"""
STRM任务控制器，用于管理STRM文件生成任务

注意：异常处理最佳实践
-------------------------------
本项目推荐使用自定义的HTTPException类而不是FastAPI的HTTPException类。

推荐用法:
```
from app.core.exceptions import HTTPException
raise HTTPException(code="4001", msg="认证失败")
```

而不是:
```
from fastapi import HTTPException
raise HTTPException(status_code=401, detail="认证失败")
```

系统已添加兼容层处理两种类型的异常，但为保持一致性，请尽量使用自定义HTTPException。
"""

import os
import shutil
import tempfile
import zipfile
import json
import asyncio
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
import re

from fastapi.responses import FileResponse
from app.core.exceptions import HTTPException

from app.models.strm import StrmTask, StrmFile, MediaServer, TaskStatus, SystemSettings, FileType, ProcessType
from app.models.strm import DownloadTask, DownloadTaskStatus
from tortoise.expressions import Q
from app.models.system import User
from app.utils.strm.processor import process_directory_tree
from app.controllers.strm.upload import get_parse_result
from app.settings import APP_SETTINGS

# 创建日志记录器
logger = logging.getLogger("strm_task_controller")


def calculate_directory_size(directory_path: str) -> int:
    """
    计算目录的总大小（字节）

    Args:
        directory_path: 目录路径

    Returns:
        目录总大小（字节），如果目录不存在或计算失败返回0
    """
    try:
        if not os.path.exists(directory_path):
            return 0

        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    # 使用 os.path.getsize 获取文件大小，处理符号链接等特殊情况
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    # 忽略无法访问的文件（如权限问题、损坏的符号链接等）
                    continue

        return total_size
    except Exception as e:
        logger.warning(f"计算目录大小失败 {directory_path}: {str(e)}")
        return 0


async def log_system_settings_to_task(task: StrmTask, settings: SystemSettings, media_server: MediaServer, download_server: MediaServer) -> None:
    """
    将系统设置信息记录到任务日志中

    Args:
        task: STRM任务对象
        settings: 系统设置对象
        media_server: 媒体服务器对象
        download_server: 下载服务器对象
    """
    try:
        # 记录任务开始信息
        await task.log("🚀 STRM任务开始执行", level="INFO")
        await task.log("=" * 60, level="INFO")

        # 记录任务基本信息
        await task.log(f"📋 任务信息:", level="INFO")
        await task.log(f"   • 任务名称: {task.name}", level="INFO")
        await task.log(f"   • 任务ID: {task.id}", level="INFO")
        await task.log(f"   • 输出目录: {task.output_dir}", level="INFO")

        # 记录任务实际使用的服务器配置
        await task.log(f"🖥️ 任务使用的服务器配置:", level="INFO")
        await task.log(f"   • 媒体服务器: {media_server.name} ({media_server.server_type})", level="INFO")
        await task.log(f"   • 媒体服务器地址: {media_server.base_url}", level="INFO")
        if download_server.id != media_server.id:
            await task.log(f"   • 下载服务器: {download_server.name} ({download_server.server_type})", level="INFO")
            await task.log(f"   • 下载服务器地址: {download_server.base_url}", level="INFO")
        else:
            await task.log(f"   • 下载服务器: 使用媒体服务器", level="INFO")

        # 记录系统设置（仅显示关键配置，避免与处理器配置重复）
        if settings:
            await task.log(f"⚙️ 系统设置 (版本 {settings.settings_version}):", level="INFO")

            # 显示系统默认服务器配置（如果有的话）
            if settings.default_media_server_id or settings.default_download_server_id:
                await task.log(f"   • 系统默认服务器配置:", level="INFO")
                if settings.default_media_server_id:
                    default_media = await MediaServer.get_or_none(id=settings.default_media_server_id)
                    if default_media:
                        await task.log(f"     - 默认媒体服务器: {default_media.name}", level="INFO")
                if settings.default_download_server_id:
                    default_download = await MediaServer.get_or_none(id=settings.default_download_server_id)
                    if default_download:
                        await task.log(f"     - 默认下载服务器: {default_download.name}", level="INFO")

            # 仅显示关键系统配置，处理器特定配置将在处理器日志中显示
            if settings.output_directory:
                await task.log(f"   • 默认输出目录: {settings.output_directory}", level="INFO")

            # 记录文件类型配置
            await task.log(f"📁 文件类型配置:", level="INFO")
            if settings.video_file_types:
                await task.log(f"   • 视频文件: {settings.video_file_types}", level="INFO")
            if settings.audio_file_types:
                await task.log(f"   • 音频文件: {settings.audio_file_types}", level="INFO")
            if settings.image_file_types:
                await task.log(f"   • 图片文件: {settings.image_file_types}", level="INFO")
            if settings.subtitle_file_types:
                await task.log(f"   • 字幕文件: {settings.subtitle_file_types}", level="INFO")
            if settings.metadata_file_types:
                await task.log(f"   • 元数据文件: {settings.metadata_file_types}", level="INFO")
        else:
            await task.log(f"⚙️ 系统设置: 使用默认配置", level="INFO")

        await task.log("=" * 60, level="INFO")
        await task.log("🔄 开始处理文件...", level="INFO")

    except Exception as e:
        logger.error(f"记录系统设置到任务日志失败: {str(e)}")
        # 即使记录失败也不应该影响任务执行，只记录错误日志
        try:
            await task.log(f"⚠️ 记录系统设置失败: {str(e)}", level="WARNING")
        except:
            pass


async def create_strm_task(
    record_id: int,
    server_id: int,
    user: User,
    output_dir: Optional[str] = None,
    custom_name: Optional[str] = None,
    download_server_id: Optional[int] = None,
    threads: int = 1,
) -> StrmTask:
    """
    创建STRM处理任务，将同时处理STRM文件生成和资源文件下载

    Args:
        record_id: 上传记录ID
        server_id: 媒体服务器ID
        user: 当前用户
        output_dir: 自定义输出目录，默认为临时目录
        custom_name: 自定义任务名称
        download_server_id: 下载服务器ID，用于下载资源文件
        threads: 下载线程数

    Returns:
        创建的任务对象
    """
    # 检查媒体服务器是否存在
    server = await MediaServer.get_or_none(id=server_id)
    if not server:
        raise HTTPException(code=404, msg=f"找不到ID为{server_id}的媒体服务器")

    # 检查下载服务器是否存在
    download_server = None
    if download_server_id:
        download_server = await MediaServer.get_or_none(id=download_server_id)
        if not download_server:
            raise HTTPException(code=404, msg=f"找不到ID为{download_server_id}的下载服务器")

    # 确定输出目录
    if not output_dir:
        # 从系统设置中获取默认输出目录
        settings = await SystemSettings.all().first()
        base_output_dir = settings.output_directory if settings and settings.output_directory else "strm_output"

        # 确保基础输出目录是Path对象
        base_output_dir = Path(base_output_dir)

        # 创建带有时间戳和用户ID的任务输出目录
        task_dir_name = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user.id}"
        output_dir = str(base_output_dir / task_dir_name)

    # 创建任务名称
    if not custom_name:
        custom_name = f"STRM任务-记录{record_id}-{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # 创建任务记录
    task = await StrmTask.create(
        name=custom_name,
        server=server,  # 媒体服务器
        download_server=download_server,  # 下载服务器
        source_file=str(record_id),  # 存储上传记录ID
        output_dir=output_dir,
        total_files=0,  # 初始化为0，后续更新
        status=TaskStatus.PENDING,
        created_by=user,
        threads=threads,
    )

    return task

async def start_strm_task(task_id: int, user_id: int) -> Dict[str, Any]:
    """
    启动STRM处理任务，会根据文件类型自动处理STRM文件生成和资源文件下载

    Args:
        task_id: 任务ID
        user_id: 当前用户ID

    Returns:
        任务启动结果
    """

    # 获取用户
    try:
        user = await User.get_or_none(id=user_id)
        if not user:
            logger.error(f"错误: 找不到ID为{user_id}的用户")
            return {"success": False, "message": f"找不到ID为{user_id}的用户"}

        # 获取任务
        task = await StrmTask.get_or_none(id=task_id)
        if not task:
            logger.error(f"错误: 找不到ID为{task_id}的任务")
            return {"success": False, "message": f"找不到ID为{task_id}的任务"}

        # 检查权限
        if task.created_by_id != user.id:
            logger.error(f"错误: 用户{user.id}没有权限操作任务{task_id}")
            return {"success": False, "message": "没有权限操作此任务"}

        # 检查任务状态
        if task.status == TaskStatus.RUNNING:
            return {"success": False, "message": "任务已在运行中"}

        # 获取上传记录ID和服务器
        record_id = int(task.source_file)
        media_server = await MediaServer.get_or_none(id=task.server_id)
        if not media_server:
            logger.error(f"错误: 任务 {task.id} 关联的媒体服务器 {task.server_id} 不存在")
            task.status = TaskStatus.FAILED
            await task.log(f"找不到ID为{task.server_id}的媒体服务器", level="ERROR")
            await task.save()
            return {"success": False, "message": "任务关联的媒体服务器不存在"}

        download_server = await task.download_server

        # 如果没有指定下载服务器，使用媒体服务器作为下载服务器
        if not download_server:
            download_server = media_server

        # 确保输出目录存在
        os.makedirs(task.output_dir, exist_ok=True)

        # 获取系统设置
        settings = await SystemSettings.all().first()

        # 记录系统设置信息到任务日志
        await log_system_settings_to_task(task, settings, media_server, download_server)

        # 获取解析结果
        parse_result = await get_parse_result(record_id, user, "all", 1, 10000, True)
        if not parse_result:
            # 更新任务状态为失败
            task.status = TaskStatus.FAILED
            task.log_content = f"找不到ID为{record_id}的文件解析结果"
            await task.save()
            return {"success": False, "message": f"找不到ID为{record_id}的文件解析结果"}

        all_files = parse_result.get("parsed_files", [])

        # 过滤掉目录，只处理文件
        file_list = [f for f in all_files if not f.get("is_dir", False)]

        # 更新任务总文件数
        task.total_files = len(file_list)

        # 获取系统设置中的重试次数
        settings = await SystemSettings.all().first()
        retry_count = 3  # 默认重试次数
        if settings and hasattr(settings, 'failure_retry_count'):
            retry_count = settings.failure_retry_count

        # 创建下载任务
        for file_info in file_list:
            file_path = file_info.get("path", "")
            file_type = file_info.get("file_type", FileType.OTHER)

            # 根据文件类型决定处理方式
            process_type = ProcessType.STRM_GENERATION if file_type == FileType.VIDEO else ProcessType.RESOURCE_DOWNLOAD

            # 创建下载任务
            await DownloadTask.create(
                task=task,
                source_path=file_path,
                file_type=file_type,
                process_type=process_type,
                status=DownloadTaskStatus.PENDING,
                file_size=file_info.get("size", 0),
                max_attempts=retry_count,  # 使用系统设置中的重试次数
            )

        # 更新任务状态
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        # 如果任务模型支持心跳，初始化心跳时间
        if hasattr(task, 'last_heartbeat'):
            task.last_heartbeat = datetime.now()
        await task.save()

        # 启动处理过程
        try:
            # 调用统一处理函数
            result = await process_directory_tree(
                server_id=media_server.id,
                download_server_id=download_server.id,
                files=file_list,
                output_dir=task.output_dir,
                task_id=task.id,
                threads=task.threads,
            )

            return {"success": True, "message": "任务启动成功", "task_id": task.id, "result": result}
        except Exception as e:
            # 更新任务状态为失败
            task.status = TaskStatus.FAILED
            await task.log(f"任务处理失败: {str(e)}", level="ERROR")
            await task.save()
            logger.error(f"任务{task_id}处理失败: {str(e)}")
            return {"success": False, "message": f"任务处理失败: {str(e)}"}
    except Exception as e:
        # 捕获所有异常，确保后台任务不会中断
        logger.error(f"启动任务{task_id}时发生意外错误: {str(e)}")
        # 尝试更新任务状态
        try:
            task = await StrmTask.get_or_none(id=task_id)
            if task:
                task.status = TaskStatus.FAILED
                await task.log(f"任务执行发生意外错误: {str(e)}", level="ERROR")
                await task.save()
        except Exception as inner_e:
            logger.error(f"更新任务{task_id}状态失败: {str(inner_e)}")
        return {"success": False, "message": f"启动任务时发生错误: {str(e)}"}


async def get_task_status(task_id: int, user: User) -> Dict[str, Any]:
    """
    获取任务状态

    Args:
        task_id: 任务ID
        user: 当前用户

    Returns:
        包含任务状态信息的字典
    """
    # 验证任务存在并属于当前用户，并预加载服务器信息
    task = await StrmTask.get_or_none(id=task_id, created_by=user).prefetch_related("server", "download_server")
    if not task:
        raise HTTPException(code=404, msg=f"找不到ID为{task_id}的任务或无权访问")

    from app.log.log import log
    from app.models.strm import DownloadTask, DownloadTaskStatus

    try:
        # --- 改进的统计逻辑 ---
        # 1. 获取所有与该任务相关的下载任务记录
        all_download_tasks = await DownloadTask.filter(task_id=task.id).all()

        # 2. 分类统计
        strm_tasks = [dt for dt in all_download_tasks if dt.process_type == "strm_generation"]
        resource_tasks = [dt for dt in all_download_tasks if dt.process_type == "resource_download"]

        # 统计STRM文件
        strm_files_count = len(strm_tasks)
        strm_success = sum(1 for dt in strm_tasks if dt.status == DownloadTaskStatus.COMPLETED)
        strm_failed = sum(1 for dt in strm_tasks if dt.status == DownloadTaskStatus.FAILED)
        strm_pending = sum(1 for dt in strm_tasks if dt.status in [DownloadTaskStatus.PENDING])

        # 统计资源文件
        resource_files_count = len(resource_tasks)
        resource_success = sum(1 for dt in resource_tasks if dt.status == DownloadTaskStatus.COMPLETED)
        resource_failed = sum(1 for dt in resource_tasks if dt.status == DownloadTaskStatus.FAILED)
        resource_pending = sum(1 for dt in resource_tasks if dt.status in [DownloadTaskStatus.PENDING])

        # 3. 记录详细统计信息
        file_stats = {
            "strm_files_count": strm_files_count,
            "strm_success": strm_success,
            "strm_failed": strm_failed,
            "strm_pending": strm_pending,
            "resource_files_count": resource_files_count,
            "resource_success": resource_success,
            "resource_failed": resource_failed,
            "resource_pending": resource_pending,
        }

        # 4. 计算总数和进度
        total_files = strm_files_count + resource_files_count
        # 统计所有已处理的文件（成功+失败）
        processed_files = strm_success + strm_failed + resource_success + resource_failed

        try:
            # 进度基于已处理文件数计算（包括成功和失败）
            progress = min(100, round((processed_files / total_files) * 100))
        except ZeroDivisionError:
            progress = 0

        # 5. 计算资源大小 - 直接计算输出目录的实际大小
        total_size = calculate_directory_size(task.output_dir)

        # 如果目录大小为0（可能目录不存在或为空），回退到数据库记录的大小
        if total_size == 0:
            total_size = sum(dt.file_size or 0 for dt in all_download_tasks)

        # 6. 获取服务器信息
        media_server = await task.server
        download_server = await task.download_server if task.download_server else media_server

        elapsed_time = None
        if task.start_time:
            end_time = task.end_time or datetime.now().astimezone()
            elapsed_seconds = int((end_time - task.start_time).total_seconds())
            minutes, seconds = divmod(elapsed_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            elapsed_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # 7. 构建完整的任务状态信息
        result = {
            "id": task.id,
            "name": task.name,
            "status": task.status,
            "total_files": total_files,
            "processed_files": processed_files,  # 已处理文件数（只统计成功的）
            "success_files": strm_success + resource_success,  # 成功文件数
            "failed_files": strm_failed + resource_failed,  # 失败文件数
            # 进度百分比
            "progress": progress,
            "create_time": task.create_time.strftime("%Y-%m-%d %H:%M:%S") if task.create_time else None,
            "start_time": task.start_time.strftime("%Y-%m-%d %H:%M:%S") if task.start_time else None,
            "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S") if task.end_time else None,
            "elapsed_time": elapsed_time,
            "output_dir": task.output_dir,
            "threads": task.threads,  # 线程数字段
            "total_size": total_size,  # 资源总大小
            "server_name": media_server.name if media_server else "未知服务器",  # 媒体服务器名称
            "server_url": media_server.base_url if media_server else "未知服务器",  # 媒体服务器URL
            "download_server_name": download_server.name if download_server and download_server.id != media_server.id else None,  # 下载服务器名称
            "download_server_url": download_server.base_url if download_server and download_server.id != media_server.id else None,  # 下载服务器URL
            "download_server_id": download_server.id if download_server else None,  # 下载服务器ID
            "media_server_id": media_server.id if media_server else None,  # 媒体服务器ID
            "has_separate_download_server": download_server and download_server.id != media_server.id,  # 是否有独立下载服务器
            **file_stats,
        }

        return result

    except Exception as e:
        # 确保即使出现异常也能返回任务基本状态
        log.error(f"[任务状态] 获取任务 {task_id} 状态时发生异常: {str(e)}")
        # 记录详细错误信息和堆栈跟踪
        log.error(f"[任务状态] 异常堆栈: {traceback.format_exc()}")

        # 返回基本信息
        return {
            "id": task.id,
            "name": task.name,
            "status": task.status,
            "total_files": task.total_files,
            "processed_files": task.processed_files,
            "success_files": task.success_files,
            "failed_files": task.failed_files,
            "progress": 0
            if task.total_files == 0
            else min(100, round((task.processed_files / task.total_files) * 100)),
            "create_time": task.create_time.strftime("%Y-%m-%d %H:%M:%S") if task.create_time else None,
            "start_time": task.start_time.strftime("%Y-%m-%d %H:%M:%S") if task.start_time else None,
            "end_time": task.end_time.strftime("%Y-%m-%d %H:%M:%S") if task.end_time else None,
            "output_dir": task.output_dir,
            "threads": task.threads,  # 线程数字段
            "total_size": calculate_directory_size(task.output_dir),  # 计算输出目录实际大小
            "server_name": "未知服务器",  # 媒体服务器名称默认值
            "server_url": "未知服务器",  # 媒体服务器URL默认值
            "download_server_name": None,  # 下载服务器名称默认值
            "download_server_url": None,  # 下载服务器URL默认值
            "error": f"获取详细状态时发生错误: {str(e)}",
            "strm_files_count": 0,
            "strm_success": 0,
            "strm_failed": 0,
            "resource_files_count": 0,
            "resource_success": 0,
            "resource_failed": 0,
        }


async def get_task_files(
    task_id: int,
    user: User,
    page: int = 1,
    page_size: int = 10,
    file_type: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取任务的文件列表

    Args:
        task_id: 任务ID
        user: 当前用户
        page: 页码
        page_size: 每页数量
        file_type: 文件类型过滤 (video, audio, image, subtitle, metadata)
        search: 搜索关键词
        status: 处理状态过滤

    Returns:
        包含文件列表的字典
    """
    # 验证任务存在并属于当前用户
    task = await StrmTask.get_or_none(id=task_id, created_by=user)
    if not task:
        raise HTTPException(code=404, msg=f"找不到ID为{task_id}的任务或无权访问")

    from app.log.log import log

    try:
        # 获取系统设置以便进行文件类型分类
        from app.controllers.strm.system_controller import system_settings_controller
        settings = await system_settings_controller.get_settings()

        # 构建查询条件
        query_filters = {"task_id": task.id}

        # 状态过滤
        if status:
            # 根据传入的状态字符串进行过滤
            if status == "completed":
                query_filters["status"] = DownloadTaskStatus.COMPLETED
            elif status == "failed":
                query_filters["status"] = DownloadTaskStatus.FAILED
            elif status == "canceled":
                query_filters["status"] = DownloadTaskStatus.CANCELED
            elif status == "downloading":
                query_filters["status"] = DownloadTaskStatus.DOWNLOADING
            elif status == "pending":
                query_filters["status"] = DownloadTaskStatus.PENDING

        # 构建基础查询
        base_query = DownloadTask.filter(**query_filters)

        # 如果有搜索关键词，添加搜索条件
        if search:
            search_lower = search.lower()
            base_query = base_query.filter(
                Q(source_path__icontains=search_lower) | Q(target_path__icontains=search_lower)
            )

        # 获取所有符合条件的记录（用于文件类型过滤）
        all_matching_tasks = await base_query.all()

        # 如果有文件类型过滤，需要在Python中进行过滤
        if file_type and settings:
            filtered_tasks = []
            for dt in all_matching_tasks:
                if _get_file_type_category(dt.source_path, settings) == file_type:
                    filtered_tasks.append(dt)
            all_matching_tasks = filtered_tasks

        # 计算总数
        total_count = len(all_matching_tasks)

        # 手动分页
        offset = (page - 1) * page_size
        download_tasks = all_matching_tasks[offset:offset + page_size]

        # 构建文件列表
        files = []
        for dt in download_tasks:
            file_info = {
                "id": dt.id,
                "source_path": dt.source_path,
                "target_path": dt.target_path,
                "file_size": dt.file_size,
                "is_success": dt.status == DownloadTaskStatus.COMPLETED,
                "status": dt.status.value if dt.status else "unknown",
                "process_type": dt.process_type,
                "error_message": dt.error_message,
                "created_at": dt.create_time.strftime("%Y-%m-%d %H:%M:%S") if dt.create_time else None,
                "updated_at": dt.update_time.strftime("%Y-%m-%d %H:%M:%S") if dt.update_time else None,
                "process_time": dt.download_duration,
                "download_speed": dt.download_speed,
                "file_type": "strm" if dt.process_type == "strm_generation" else "resource"
            }
            files.append(file_info)

        # 统计信息
        stats = {
            "total": total_count,
            "success": await DownloadTask.filter(task_id=task.id, status=DownloadTaskStatus.COMPLETED).count(),
            "failed": await DownloadTask.filter(task_id=task.id, status=DownloadTaskStatus.FAILED).count(),
            "canceled": await DownloadTask.filter(task_id=task.id, status=DownloadTaskStatus.CANCELED).count(),
            "pending": await DownloadTask.filter(task_id=task.id, status=DownloadTaskStatus.PENDING).count(),
            "processing": await DownloadTask.filter(task_id=task.id, status=DownloadTaskStatus.DOWNLOADING).count(),
        }

        # log.info(f"[文件列表] 任务 {task_id} 文件列表获取成功，总数: {total_count}, 当前页: {page}, 每页: {page_size}")

        return {
            "files": files,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            },
            "stats": stats
        }

    except Exception as e:
        log.error(f"[文件列表] 获取任务 {task_id} 文件列表失败: {str(e)}")
        log.error(f"[文件列表] 异常堆栈: {traceback.format_exc()}")
        raise HTTPException(code=500, msg=f"获取任务文件列表失败: {str(e)}")


async def get_task_directory_content(task_id: int, user: User, directory_path: str = "/") -> Dict[str, Any]:
    """
    获取任务指定目录的内容（用于树形视图懒加载）

    Args:
        task_id: 任务ID
        user: 当前用户
        directory_path: 目录路径

    Returns:
        包含目录内容的字典
    """
    # 验证任务存在并属于当前用户
    task = await StrmTask.get_or_none(id=task_id, created_by=user)
    if not task:
        raise HTTPException(code=404, msg=f"找不到ID为{task_id}的任务或无权访问")

    from app.log.log import log

    try:
        # 标准化目录路径
        directory_path = directory_path.strip()
        if not directory_path.startswith('/'):
            directory_path = '/' + directory_path
        directory_path = directory_path.rstrip('/')
        if not directory_path:
            directory_path = '/'

        # log.info(f"[目录内容] 获取任务 {task_id} 目录 '{directory_path}' 的内容")

        # 获取该目录下的所有文件
        if directory_path == '/':
            # 根目录：获取所有文件并分析根级别内容
            all_files = await DownloadTask.filter(task_id=task.id).all()

            directories = set()
            files = []

            for file_task in all_files:
                source_path = file_task.source_path or ''
                if not source_path:
                    continue

                # 移除开头的斜杠并分割路径
                path_parts = source_path.lstrip('/').split('/')

                if len(path_parts) == 1:
                    # 根文件
                    files.append({
                        'file_name': path_parts[0],
                        'is_directory': False,
                        'file_size': file_task.file_size,
                        'is_success': file_task.status == DownloadTaskStatus.COMPLETED,
                        'file_type': file_task.file_type.value if file_task.file_type else 'other'
                    })
                elif len(path_parts) > 1:
                    # 子目录
                    directories.add(path_parts[0])

            # 添加目录项
            items = []
            for dir_name in sorted(directories):
                items.append({
                    'file_name': dir_name,
                    'is_directory': True
                })

            # 添加文件项
            items.extend(sorted(files, key=lambda x: x['file_name']))

        else:
            # 子目录：获取该目录下的内容
            target_prefix = directory_path.lstrip('/') + '/'
            all_files = await DownloadTask.filter(task_id=task.id).all()

            directories = set()
            files = []

            for file_task in all_files:
                source_path = file_task.source_path or ''
                if not source_path:
                    continue

                # 移除开头的斜杠
                normalized_path = source_path.lstrip('/')

                # 检查是否在目标目录下
                if normalized_path.startswith(target_prefix):
                    # 获取相对路径
                    relative_path = normalized_path[len(target_prefix):]
                    if not relative_path:
                        continue

                    path_parts = relative_path.split('/')

                    if len(path_parts) == 1:
                        # 直接文件
                        files.append({
                            'file_name': path_parts[0],
                            'is_directory': False,
                            'file_size': file_task.file_size,
                            'is_success': file_task.status == DownloadTaskStatus.COMPLETED,
                            'file_type': file_task.file_type.value if file_task.file_type else 'other'
                        })
                    elif len(path_parts) > 1:
                        # 子目录
                        directories.add(path_parts[0])

            # 添加目录项
            items = []
            for dir_name in sorted(directories):
                items.append({
                    'file_name': dir_name,
                    'is_directory': True
                })

            # 添加文件项
            items.extend(sorted(files, key=lambda x: x['file_name']))

        # 统计信息
        file_count = len([item for item in items if not item['is_directory']])
        directory_count = len([item for item in items if item['is_directory']])

        # log.info(f"[目录内容] 任务 {task_id} 目录 '{directory_path}' 内容获取成功，文件: {file_count}, 目录: {directory_count}")

        return {
            "directory_path": directory_path,
            "items": items,
            "stats": {
                "file_count": file_count,
                "directory_count": directory_count
            }
        }

    except Exception as e:
        log.error(f"[目录内容] 获取任务 {task_id} 目录 '{directory_path}' 内容失败: {str(e)}")
        log.error(f"[目录内容] 异常堆栈: {traceback.format_exc()}")
        raise HTTPException(code=500, msg=f"获取目录内容失败: {str(e)}")


async def get_user_tasks(
    user: User,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取用户的任务列表，支持搜索和过滤

    Args:
        user: 当前用户
        page: 页码
        page_size: 每页数量
        search: 按名称搜索
        status: 按状态过滤
        start_date: 开始日期过滤
        end_date: 结束日期过滤

    Returns:
        任务列表
    """
    from app.log.log import log

    # 计算偏移量
    offset = (page - 1) * page_size

    # 构建基本查询
    query = StrmTask.filter(created_by=user)

    # 添加搜索条件
    if search:
        query = query.filter(name__icontains=search)

    # 添加状态过滤
    if status:
        # 状态值映射，处理前端传入的状态值
        status_mapping = {
            "SUCCESS": "completed",  # 前端使用SUCCESS，后端是completed
            "CANCELED": "canceled",  # 前端是大写，后端是小写
            "FAILED": "failed",  # 前端是大写，后端是小写
            "PENDING": "pending",  # 前端是大写，后端是小写
            "RUNNING": "running",  # 前端是大写，后端是小写
        }
        # 将前端状态值转换为后端状态值
        backend_status = status_mapping.get(status, status.lower())
        query = query.filter(status=backend_status)

    # 添加日期范围过滤
    if start_date:
        # 将日期字符串转换为datetime对象
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(create_time__gte=start_datetime)

    if end_date:
        # 将日期字符串转换为datetime对象，并设置为当天的结束时间
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
        end_datetime = end_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.filter(create_time__lte=end_datetime)

    # 查询任务并计算总数
    tasks = await query.offset(offset).limit(page_size).order_by("-create_time")
    total = await query.count()

    if not tasks:
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "tasks": [],
        }

    # 获取所有任务ID
    task_ids = [t.id for t in tasks]

    # 批量查询所有任务的下载任务统计信息，使用原生SQL优化性能
    from tortoise import Tortoise
    conn = Tortoise.get_connection("conn_system")

    # 使用单个SQL查询获取所有任务的统计信息
    stats_sql = """
    SELECT
        task_id,
        process_type,
        status,
        COUNT(*) as count
    FROM strm_download_tasks
    WHERE task_id IN ({})
    GROUP BY task_id, process_type, status
    """.format(','.join('?' * len(task_ids)))

    stats_result = await conn.execute_query(stats_sql, task_ids)

    # 构建统计信息字典
    task_stats = {}
    for row in stats_result[1]:
        task_id, process_type, status, count = row
        if task_id not in task_stats:
            task_stats[task_id] = {
                'strm_completed': 0,
                'strm_failed': 0,
                'resource_completed': 0,
                'resource_failed': 0,
                'total': 0
            }

        task_stats[task_id]['total'] += count

        if process_type == 'strm_generation':
            if status == 'completed':
                task_stats[task_id]['strm_completed'] = count
            elif status == 'failed':
                task_stats[task_id]['strm_failed'] = count
        elif process_type == 'resource_download':
            if status == 'completed':
                task_stats[task_id]['resource_completed'] = count
            elif status == 'failed':
                task_stats[task_id]['resource_failed'] = count

    # 构建任务列表
    task_list = []
    for t in tasks:
        stats = task_stats.get(t.id, {
            'strm_completed': 0,
            'strm_failed': 0,
            'resource_completed': 0,
            'resource_failed': 0,
            'total': 0
        })

        total_files = stats['total']
        success_files = stats['strm_completed'] + stats['resource_completed']
        failed_files = stats['strm_failed'] + stats['resource_failed']
        processed_files = success_files + failed_files
        progress = min(100, round((processed_files / total_files) * 100)) if total_files > 0 else 0

        task_list.append({
            "id": t.id,
            "name": t.name,
            "status": t.status,
            "total_files": total_files,
            "processed_files": processed_files,
            "success_files": success_files,
            "failed_files": failed_files,
            "progress": progress,
            "start_time": t.start_time.isoformat() if t.start_time else None,
            "end_time": t.end_time.isoformat() if t.end_time else None,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "tasks": task_list,
    }


async def cancel_task(task_id: int, user: User) -> Dict[str, Any]:
    """
    取消任务

    Args:
        task_id: 任务ID
        user: 当前用户

    Returns:
        取消结果
    """
    # 获取任务
    task = await StrmTask.get_or_none(id=task_id)
    if not task:
        raise HTTPException(code=404, msg=f"找不到ID为{task_id}的任务")

    # 检查权限
    if task.created_by_id != user.id:
        raise HTTPException(code=403, msg="没有权限取消此任务")

    # 检查任务状态，只有运行中或等待中的任务可以取消
    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(code=400, msg=f"任务状态为{task.status}，无法取消")

    try:
        # 更新主任务状态为已取消
        task.status = TaskStatus.CANCELED
        task.end_time = datetime.now()
        await task.log("任务已被用户取消", level="INFO")
        await task.save()

        # 取消所有相关的下载任务
        pending_downloads = await DownloadTask.filter(
            task_id=task.id,
            status__in=[DownloadTaskStatus.PENDING, DownloadTaskStatus.DOWNLOADING, DownloadTaskStatus.RETRY],
        )

        canceled_count = 0
        for dl_task in pending_downloads:
            dl_task.status = DownloadTaskStatus.CANCELED
            dl_task.error_message = "任务被用户取消"
            await dl_task.save()
            canceled_count += 1

        logger.info(f"任务 {task_id} 已取消，同时取消了 {canceled_count} 个下载任务")

        return {
            "success": True,
            "message": f"任务取消成功，已取消 {canceled_count} 个相关下载任务",
            "task_id": task_id,
            "canceled_downloads": canceled_count
        }

    except Exception as e:
        logger.error(f"取消任务 {task_id} 时发生错误: {str(e)}")
        raise HTTPException(code=500, msg=f"取消任务时发生错误: {str(e)}")


async def continue_task(task_id: int, user: User) -> Dict[str, Any]:
    """
    继续已取消的任务

    Args:
        task_id: 任务ID
        user: 当前用户

    Returns:
        继续结果
    """
    # 获取任务
    task = await StrmTask.get_or_none(id=task_id)
    if not task:
        raise HTTPException(code=404, msg=f"找不到ID为{task_id}的任务")

    # 检查权限
    if task.created_by_id != user.id:
        raise HTTPException(code=403, msg="没有权限操作此任务")

    # 检查任务状态，只有已取消的任务可以继续
    if task.status != TaskStatus.CANCELED:
        raise HTTPException(code=400, msg=f"任务状态为{task.status}，只有已取消的任务可以继续")

    try:
        # 获取媒体服务器和下载服务器
        media_server = await MediaServer.get_or_none(id=task.server_id)
        if not media_server:
            raise HTTPException(code=404, msg=f"找不到ID为{task.server_id}的媒体服务器")

        download_server = await task.download_server
        if not download_server:
            download_server = media_server

        # 重置任务状态
        task.status = TaskStatus.RUNNING  # 直接设置为运行中
        task.start_time = datetime.now()
        task.end_time = None
        await task.log(f"任务由用户 {user.user_name} 继续执行", level="INFO")
        await task.save()

        # 智能处理下载任务状态
        # 获取所有相关的下载任务
        all_downloads = await DownloadTask.filter(task_id=task.id)

        reset_count = 0
        skipped_count = 0
        completed_count = 0

        for dl_task in all_downloads:
            if dl_task.status == DownloadTaskStatus.COMPLETED:
                # 已完成的任务，检查文件是否仍然存在
                if dl_task.target_path and os.path.exists(dl_task.target_path):
                    # 文件存在，保持完成状态
                    completed_count += 1
                    continue
                else:
                    # 文件不存在，重置为待处理
                    dl_task.status = DownloadTaskStatus.PENDING
                    dl_task.error_message = "文件丢失，需要重新处理"
                    await dl_task.save()
                    reset_count += 1
            elif dl_task.status == DownloadTaskStatus.CANCELED:
                # 已取消的任务，检查是否已有完整文件
                if dl_task.target_path and os.path.exists(dl_task.target_path):
                    # 检查文件完整性
                    file_is_complete = False
                    if dl_task.process_type == ProcessType.RESOURCE_DOWNLOAD and dl_task.file_size:
                        try:
                            actual_size = os.path.getsize(dl_task.target_path)
                            file_is_complete = (actual_size == dl_task.file_size)
                        except OSError:
                            file_is_complete = False
                    elif dl_task.process_type == ProcessType.STRM_GENERATION:
                        # STRM文件存在即认为完整
                        file_is_complete = True

                    if file_is_complete:
                        # 文件完整，标记为已完成
                        dl_task.status = DownloadTaskStatus.COMPLETED
                        dl_task.error_message = None
                        await dl_task.save()
                        skipped_count += 1
                    else:
                        # 文件不完整，重置为待处理
                        dl_task.status = DownloadTaskStatus.PENDING
                        dl_task.error_message = None
                        await dl_task.save()
                        reset_count += 1
                else:
                    # 文件不存在，重置为待处理
                    dl_task.status = DownloadTaskStatus.PENDING
                    dl_task.error_message = None
                    await dl_task.save()
                    reset_count += 1
            elif dl_task.status in [DownloadTaskStatus.FAILED, DownloadTaskStatus.RETRY]:
                # 失败或重试的任务，重置为待处理
                dl_task.status = DownloadTaskStatus.PENDING
                dl_task.error_message = None
                dl_task.attempt_count = 0  # 重置重试次数
                await dl_task.save()
                reset_count += 1

        # 直接调用处理函数，不重新创建下载任务
        from app.utils.strm.processor import process_directory_tree

        # 获取文件列表（用于统计，不用于创建新任务）
        record_id = int(task.source_file)
        parse_result = await get_parse_result(record_id, user, "all", 1, 10000, True)
        file_list = parse_result.get("parsed_files", []) if parse_result else []
        file_list = [f for f in file_list if not f.get("is_dir", False)]

        # 启动处理过程（只处理现有的待处理任务）
        result = await process_directory_tree(
            server_id=media_server.id,
            download_server_id=download_server.id,
            files=file_list,  # 用于统计和日志
            output_dir=task.output_dir,
            task_id=task.id,
            threads=task.threads,
        )

        logger.info(f"任务 {task_id} 已继续，重置了 {reset_count} 个任务，跳过了 {skipped_count} 个已完成的文件，保持了 {completed_count} 个已完成的任务")

        # 构建详细的消息
        message_parts = ["任务继续成功"]
        if completed_count > 0:
            message_parts.append(f"保持了 {completed_count} 个已完成的文件")
        if skipped_count > 0:
            message_parts.append(f"跳过了 {skipped_count} 个已存在的文件")
        if reset_count > 0:
            message_parts.append(f"重新处理 {reset_count} 个未完成的任务")

        return {
            "success": True,
            "message": "，".join(message_parts),
            "task_id": task_id,
            "reset_downloads": reset_count,
            "skipped_downloads": skipped_count,
            "completed_downloads": completed_count,
            "process_result": result
        }

    except Exception as e:
        logger.error(f"继续任务 {task_id} 时发生错误: {str(e)}")
        # 如果出错，将任务状态重置为取消
        try:
            task = await StrmTask.get_or_none(id=task_id)
            if task:
                task.status = TaskStatus.CANCELED
                await task.log(f"继续任务时发生错误: {str(e)}", level="ERROR")
                await task.save()
        except:
            pass
        raise HTTPException(code=500, msg=f"继续任务时发生错误: {str(e)}")


async def delete_task(task_id: int, user: User) -> Dict[str, Any]:
    """
    删除任务及相关文件

    Args:
        task_id: 任务ID
        user: 当前用户

    Returns:
        删除结果
    """
    # 获取任务
    task = await StrmTask.get_or_none(id=task_id)
    if not task:
        raise HTTPException(code=404, msg=f"找不到ID为{task_id}的任务")

    # 检查权限
    if task.created_by_id != user.id:
        raise HTTPException(code=403, msg="没有权限删除此任务")

    # 删除输出目录
    output_dir = Path(task.output_dir)
    directory_deleted = False
    if output_dir.exists():
        try:
            shutil.rmtree(output_dir)
            directory_deleted = True
            logger.info(f"成功删除任务 {task_id} 的输出目录: {output_dir}")
        except Exception as e:
            # 记录错误但继续删除任务记录
            logger.error(f"删除任务 {task_id} 输出目录失败: {str(e)}")

    # 删除相关的下载任务记录
    await DownloadTask.filter(task_id=task_id).delete()

    # 删除相关文件记录
    await StrmFile.filter(task_id=task_id).delete()

    # 删除任务记录
    await task.delete()

    # 构建返回消息
    message = "任务删除成功"
    if directory_deleted:
        message += "，本地资源目录已清除"
    elif output_dir.exists():
        message += "，但本地资源目录清除失败"

    return {"success": True, "message": message, "task_id": task_id}


async def get_task_logs(
    task_id: int,
    user: User,
    page: int = 1,
    page_size: int = 50,
    level: Optional[str] = None,
    search: Optional[str] = None,
    log_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取任务日志

    Args:
        task_id: 任务ID
        user: 当前用户
        page: 页码
        page_size: 每页数量
        level: 日志级别过滤
        search: 日志内容搜索
        log_type: 日志类型过滤 (task/download/strm)

    Returns:
        任务日志列表
    """
    from app.models.strm import DownloadLog, StrmLog
    from datetime import datetime

    # 获取任务
    task = await StrmTask.get_or_none(id=task_id)
    if not task:
        raise HTTPException(code=404, msg=f"找不到ID为{task_id}的任务")

    # 检查权限
    if task.created_by_id != user.id:
        raise HTTPException(code=403, msg="没有权限查看此任务日志")

    all_logs = []

    # 根据日志类型获取不同的日志
    if not log_type or log_type == "task":
        # 获取任务基本日志
        if task.log_content:
            task_log_lines = task.log_content.split('\n')
            for line in task_log_lines:
                line = line.strip()
                if line:
                    # 解析时间戳和级别
                    parsed_timestamp = None
                    parsed_level = None

                    # 尝试解析格式：[2025-07-10T16:45:58.705] [INFO] 消息内容
                    match = re.match(r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})\] \[(\w+)\] (.+)', line)
                    if match:
                        timestamp_str, level_str, message = match.groups()
                        try:
                            # 解析时间戳
                            parsed_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
                        except ValueError:
                            # 如果解析失败，保持为None
                            pass
                        parsed_level = level_str

                    all_logs.append({
                        "type": "task",
                        "content": line,
                        "timestamp": parsed_timestamp,
                        "level": parsed_level,
                    })

    if not log_type or log_type == "download":
        # 获取下载日志
        download_query = DownloadLog.filter(task_id=task_id)
        if level:
            download_query = download_query.filter(log_level=level.upper())
        if search:
            download_query = download_query.filter(log_message__icontains=search)

        download_logs = await download_query.order_by("create_time").all()
        for log_entry in download_logs:
            all_logs.append({
                "type": "download",
                "content": f"[{log_entry.create_time.strftime('%Y-%m-%d %H:%M:%S')}] [{log_entry.log_level}] [下载] {log_entry.log_message}",
                "timestamp": log_entry.create_time,
                "level": log_entry.log_level,
                "file_path": log_entry.file_path,
                "target_path": log_entry.target_path,
                "is_success": log_entry.is_success,
                "error_message": log_entry.error_message,
                "file_size": log_entry.file_size,
                "download_time": log_entry.download_time,
                "download_speed": log_entry.download_speed,
            })

    if not log_type or log_type == "strm":
        # 获取STRM生成日志
        strm_query = StrmLog.filter(task_id=task_id)
        if level:
            strm_query = strm_query.filter(log_level=level.upper())
        if search:
            strm_query = strm_query.filter(log_message__icontains=search)

        strm_logs = await strm_query.order_by("create_time").all()
        for log_entry in strm_logs:
            all_logs.append({
                "type": "strm",
                "content": f"[{log_entry.create_time.strftime('%Y-%m-%d %H:%M:%S')}] [{log_entry.log_level}] [STRM] {log_entry.log_message}",
                "timestamp": log_entry.create_time,
                "level": log_entry.log_level,
                "source_path": log_entry.source_path,
                "target_path": log_entry.target_path,
                "is_success": log_entry.is_success,
                "error_message": log_entry.error_message,
                "generation_time": log_entry.generation_time,
            })

    # 按时间戳排序（最早的在前）
    # 使用一个安全的默认时间戳，确保时区一致性
    def get_sort_timestamp(log_entry):
        timestamp = log_entry.get("timestamp")
        if timestamp is None:
            # 对于没有时间戳的日志，使用一个很早的时间作为默认值
            # 确保与数据库时间戳的时区处理一致
            return datetime.min.replace(tzinfo=None)
        # 如果时间戳有时区信息，移除时区信息以保持一致性
        if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
            return timestamp.replace(tzinfo=None)
        return timestamp

    all_logs.sort(key=get_sort_timestamp, reverse=False)

    # 应用搜索过滤（如果还没有应用）
    if search and (not log_type or log_type == "task"):
        all_logs = [log for log in all_logs if search.lower() in log["content"].lower()]

    # 计算分页
    total = len(all_logs)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_logs = all_logs[start_idx:end_idx]

    # 构建原始内容（用于导出）
    raw_content_lines = [log["content"] for log in all_logs]
    raw_content = "\n".join(raw_content_lines)

    return {
        "logs": [log["content"] for log in page_logs],
        "detailed_logs": page_logs,  # 包含详细信息的日志
        "total": total,
        "page": page,
        "page_size": page_size,
        "raw_content": raw_content
    }


# async def process_strm_task(task_id: int):
#     """
#     处理STRM任务，创建下载任务记录并启动处理
#
#     Args:
#         task_id: STRM任务ID
#     """
#     from app.log.log import log
#
#     try:
#         # 获取任务信息
#         task = await StrmTask.get_or_none(id=task_id)
#         if not task:
#             log.error(f"找不到ID为{task_id}的任务")
#             return
#
#         # 获取解析结果
#         record_id = int(task.source_file)
#         parse_result = await get_parse_result(record_id, task.created_by, all_files=True)
#         if not parse_result or not parse_result.get("files"):
#             log.error(f"任务 {task_id} 无法获取解析结果或文件列表为空")
#             task.status = TaskStatus.FAILED
#             task.log_content = "无法获取解析结果或文件列表为空"
#             await task.save()
#             return
#
#         # 更新任务状态为运行中
#         task.status = TaskStatus.RUNNING
#         task.start_time = datetime.now()
#         await task.save()
#
#         # 处理文件，创建下载任务
#         files = parse_result.get("files", [])
#         created_task_count = 0
#
#         for file in files:
#             # 确定处理类型
#             file_type_str = file.get("file_type", "other")
#             try:
#                 file_type = FileType(file_type_str)
#             except ValueError:
#                 file_type = FileType.OTHER
#
#             # 确定是生成STRM还是下载资源
#             process_type = ProcessType.STRM_GENERATION if file_type == FileType.VIDEO else ProcessType.RESOURCE_DOWNLOAD
#
#             # 创建下载任务记录
#             await DownloadTask.create(
#                 task=task,
#                 source_path=file.get("path", ""),
#                 file_type=file_type,
#                 process_type=process_type,
#                 status=DownloadTaskStatus.PENDING,
#                 file_size=file.get("size", 0),
#             )
#             created_task_count += 1
#
#         # 更新任务总文件数
#         task.total_files = created_task_count
#         await task.save()
#
#         log.info(f"任务 {task_id} 已创建 {created_task_count} 个下载任务")
#
#         # 调用处理函数开始实际处理
#         await process_directory_tree(
#             server_id=task.server_id,
#             files=files,
#             output_dir=task.output_dir,
#             task_id=task.id,
#             download_server_id=task.download_server_id if task.download_server else None,
#             threads=task.threads,
#         )
#
#     except Exception as e:
#         log.error(f"处理STRM任务 {task_id} 时发生错误: {str(e)}")
#         log.error(traceback.format_exc())
#
#         # 更新任务状态为失败
#         try:
#             if task:
#                 task.status = TaskStatus.FAILED
#                 task.log_content = f"处理任务时发生错误: {str(e)}"
#                 await task.save()
#         except Exception as save_error:
#             log.error(f"更新任务状态失败: {str(save_error)}")


async def get_file_preview(task_id: int, file_path: str, user: User) -> Dict[str, Any]:
    """
    获取任务文件预览内容

    Args:
        task_id: 任务ID
        file_path: 源文件路径，用于查找对应的下载任务记录
        user: 当前用户

    Returns:
        包含文件预览信息的字典
    """
    # 验证任务权限
    task = await StrmTask.filter(id=task_id, created_by=user).first()
    if not task:
        raise HTTPException(code=404, msg="任务不存在或无权限访问")

    # 查找文件记录（使用源文件路径查找）
    download_task = await DownloadTask.filter(
        task=task,
        source_path=file_path
    ).first()

    if not download_task:
        raise HTTPException(code=404, msg="文件不存在")

    # 检查文件是否处理成功
    if download_task.status != DownloadTaskStatus.COMPLETED:
        return {
            "file_path": file_path,
            "file_type": download_task.file_type.value if download_task.file_type else "unknown",
            "file_extension": Path(file_path).suffix.lower(),
            "file_size": download_task.file_size,
            "status": download_task.status.value if download_task.status else "unknown",
            "target_path": download_task.target_path,
            "preview_type": "error",
            "content": None,
            "error": download_task.error_message or "文件处理未完成或失败"
        }

    # 检查目标文件路径是否存在
    if not download_task.target_path:
        return {
            "file_path": file_path,
            "file_type": download_task.file_type.value if download_task.file_type else "unknown",
            "file_extension": Path(file_path).suffix.lower(),
            "file_size": download_task.file_size,
            "status": download_task.status.value,
            "target_path": None,
            "preview_type": "error",
            "content": None,
            "error": "目标文件路径不存在"
        }

    # 获取目标文件的扩展名（这才是实际要预览的文件类型）
    target_file_extension = Path(download_task.target_path).suffix.lower()

    # 构建预览结果
    preview_result = {
        "file_path": file_path,
        "target_path": download_task.target_path,
        "file_type": download_task.file_type.value if download_task.file_type else "unknown",
        "file_extension": target_file_extension,
        "file_size": download_task.file_size,
        "status": download_task.status.value,
        "preview_type": "info",  # 默认为基本信息
        "content": None,
        "error": None
    }

    try:
        # 根据目标文件类型决定预览方式
        if target_file_extension == ".strm":
            # STRM文件预览 - 读取STRM文件中的视频链接
            preview_result.update(await _preview_strm_file(download_task.target_path))
        elif target_file_extension in [".txt", ".nfo", ".xml", ".json", ".srt", ".ass", ".ssa", ".vtt", ".sub"]:
            # 文本文件预览
            preview_result.update(await _preview_text_file(download_task.target_path))
        elif target_file_extension in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            # 图片文件预览
            preview_result.update(await _preview_image_file(download_task.target_path))
        else:
            # 其他文件类型，只显示基本信息
            preview_result["preview_type"] = "info"

    except Exception as e:
        logger.error(f"预览文件 {download_task.target_path} 时发生错误: {str(e)}")
        preview_result["error"] = f"预览失败: {str(e)}"
        preview_result["preview_type"] = "error"

    return preview_result


async def _preview_strm_file(target_path: str) -> Dict[str, Any]:
    """预览STRM文件内容"""
    try:
        if not os.path.exists(target_path):
            return {
                "preview_type": "error",
                "error": "STRM文件不存在"
            }

        # 读取STRM文件内容（通常是一个URL）
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        # URL解码
        decoded_content = None
        try:
            from urllib.parse import unquote
            decoded_content = unquote(content, encoding='utf-8')
        except Exception as decode_error:
            logger.warning(f"URL解码失败: {str(decode_error)}")
            decoded_content = content  # 解码失败时使用原始内容

        return {
            "preview_type": "strm",
            "content": content,  # 原始编码的URL
            "decoded_content": decoded_content,  # 解码后的URL
            "content_type": "url"
        }
    except Exception as e:
        return {
            "preview_type": "error",
            "error": f"读取STRM文件失败: {str(e)}"
        }


async def _preview_text_file(target_path: str) -> Dict[str, Any]:
    """预览文本文件内容"""
    try:
        if not os.path.exists(target_path):
            return {
                "preview_type": "error",
                "error": "文件不存在"
            }

        # 检查文件大小，避免读取过大的文件
        file_size = os.path.getsize(target_path)
        if file_size > 1024 * 1024:  # 1MB
            return {
                "preview_type": "info",
                "error": "文件过大，无法预览（超过1MB）"
            }

        # 尝试以UTF-8编码读取文件
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试其他编码
            try:
                with open(target_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(target_path, 'r', encoding='latin-1') as f:
                    content = f.read()

        # 限制显示的内容长度
        if len(content) > 10000:  # 10000字符
            content = content[:10000] + "\n\n... (内容已截断)"

        return {
            "preview_type": "text",
            "content": content,
            "content_type": "text"
        }
    except Exception as e:
        return {
            "preview_type": "error",
            "error": f"读取文本文件失败: {str(e)}"
        }


async def _preview_image_file(target_path: str) -> Dict[str, Any]:
    """预览图片文件"""
    try:
        if not os.path.exists(target_path):
            return {
                "preview_type": "error",
                "error": "图片文件不存在"
            }

        # 获取图片文件信息
        file_size = os.path.getsize(target_path)

        return {
            "preview_type": "image",
            "content": target_path,  # 返回文件路径，前端可以通过API获取图片
            "content_type": "image",
            "file_size": file_size
        }
    except Exception as e:
        return {
            "preview_type": "error",
            "error": f"获取图片信息失败: {str(e)}"
        }


def _get_file_type_category(file_path: str, settings: dict) -> str:
    """
    根据系统设置判断文件类型分类

    Args:
        file_path: 文件路径
        settings: 系统设置字典

    Returns:
        文件类型分类: video, audio, image, subtitle, metadata 或空字符串
    """
    if not file_path or not settings:
        return ""

    # 获取文件扩展名
    file_name = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
    if '.' not in file_name:
        return ""

    ext = file_name.split('.')[-1].lower()

    try:
        # 获取系统设置中的文件类型配置
        video_types = (settings.get('video_file_types', '') or '').split(',')
        video_types = [t.strip().lower() for t in video_types if t.strip()]

        audio_types = (settings.get('audio_file_types', '') or '').split(',')
        audio_types = [t.strip().lower() for t in audio_types if t.strip()]

        image_types = (settings.get('image_file_types', '') or '').split(',')
        image_types = [t.strip().lower() for t in image_types if t.strip()]

        subtitle_types = (settings.get('subtitle_file_types', '') or '').split(',')
        subtitle_types = [t.strip().lower() for t in subtitle_types if t.strip()]

        metadata_types = (settings.get('metadata_file_types', '') or '').split(',')
        metadata_types = [t.strip().lower() for t in metadata_types if t.strip()]

        if ext in video_types:
            return 'video'
        elif ext in audio_types:
            return 'audio'
        elif ext in image_types:
            return 'image'
        elif ext in subtitle_types:
            return 'subtitle'
        elif ext in metadata_types:
            return 'metadata'

        return ""
    except Exception:
        return ""
