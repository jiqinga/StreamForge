"""
STRM处理器，用于生成STRM文件
"""

import os
import re
import asyncio
import threading
import queue
import time
import shutil
import zipfile
import logging
import concurrent.futures
from datetime import datetime, timedelta
from time import sleep
from typing import List, Dict, Any, Tuple, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
from tortoise.expressions import Q, F
from tortoise.functions import Sum
from tortoise.transactions import in_transaction
import traceback
from pathlib import Path
import aiofiles
from app.models.strm import MediaServer, FileType, StrmTask, StrmFile, TaskStatus, SystemSettings, ProcessType
from app.models.strm import DownloadTask, DownloadTaskStatus, DownloadLog, StrmLog
from app.utils.strm.parser import TreeParser
from app.log.log import log
from app.controllers.strm import system_settings_controller
from types import SimpleNamespace
import httpx


def get_error_message(exception: Exception) -> str:
    """简单的错误信息获取，确保不为空"""
    msg = str(exception).strip()
    return msg if msg else f"{type(exception).__name__}异常"


async def log_processor_settings_to_task(task: StrmTask, settings: SimpleNamespace, server: MediaServer, download_server: MediaServer, total_files: int) -> None:
    """
    在处理器级别记录处理配置信息到任务日志中

    Args:
        task: STRM任务对象
        settings: 系统设置对象
        server: 媒体服务器对象
        download_server: 下载服务器对象
        total_files: 总文件数
    """
    try:
        await task.log("🔧 处理器配置信息:", level="INFO")
        await task.log(f"   • 待处理文件总数: {total_files}", level="INFO")
        await task.log(f"   • 处理线程数: {settings.download_threads}", level="INFO")
        await task.log(f"   • 路径替换: {'启用' if settings.enable_path_replacement else '禁用'}", level="INFO")
        if settings.enable_path_replacement and settings.replacement_path:
            await task.log(f"   • 替换路径: {settings.replacement_path}", level="INFO")

        # 显示重试配置
        retry_count = getattr(settings, 'failure_retry_count', 2)
        retry_interval = getattr(settings, 'retry_interval_seconds', 10)
        await task.log(f"   • 失败重试次数: {retry_count}", level="INFO")
        await task.log(f"   • 重试间隔时间: {retry_interval}秒", level="INFO")

    except Exception as e:
        log.error(f"记录处理器设置到任务日志失败: {str(e)}")


async def log_task_progress(task: StrmTask, processed: int, total: int, stage: str = "") -> None:
    """
    记录任务进度信息到日志中

    Args:
        task: STRM任务对象
        processed: 已处理文件数
        total: 总文件数
        stage: 当前阶段描述
    """
    try:
        # 在记录进度前检查任务是否已被取消
        if task:
            await task.refresh_from_db()
            if task.status == TaskStatus.CANCELED:
                # 任务已被取消，不记录进度
                return

        if total > 0:
            progress_percent = min(100, round((processed / total) * 100))
            progress_bar = "█" * (progress_percent // 5) + "░" * (20 - progress_percent // 5)

            stage_text = f" - {stage}" if stage else ""
            await task.log(f"📊 任务进度: {progress_percent}% [{progress_bar}] ({processed}/{total}){stage_text}", level="INFO")
        else:
            await task.log(f"📊 任务进度: 等待开始处理{' - ' + stage if stage else ''}", level="INFO")

    except Exception as e:
        log.error(f"记录任务进度失败: {str(e)}")


async def process_strm_tasks_with_retry(task_id: int, server: MediaServer, output_dir: str, task: StrmTask, settings, files: List) -> None:
    """
    处理STRM生成任务（初始处理，重试由后台服务处理）

    Args:
        task_id: 任务ID
        server: 媒体服务器
        output_dir: 输出目录
        task: STRM任务对象
        settings: 系统设置
        files: 文件列表
    """
    from tortoise.expressions import Q

    # 检查任务是否已被取消
    if task:
        await task.refresh_from_db()
        if task.status == TaskStatus.CANCELED:
            log.info(f"任务 {task_id} 已被取消，停止STRM生成处理")
            return

    # 获取需要处理的STRM生成任务（PENDING和立即可处理的RETRY任务）
    strm_tasks = await DownloadTask.filter(
        Q(task__id=task_id) &
        Q(process_type="strm_generation") &
        (Q(status=DownloadTaskStatus.PENDING) |
         Q(status=DownloadTaskStatus.RETRY, retry_after__lte=datetime.now()) |
         Q(status=DownloadTaskStatus.RETRY, retry_after__isnull=True))
    ).all()

    if strm_tasks:
        if task:
            await task.log(f"🎬 开始处理 {len(strm_tasks)} 个STRM生成任务", level="INFO")

        strm_processor = strm_downaload(
            server=server,  # STRM生成使用媒体服务器
            output_dir=output_dir,
            task=task,
            enable_path_replacement=settings.enable_path_replacement,
            replacement_path=settings.replacement_path,
            task_list=strm_tasks,
            max_threads=settings.download_threads,
            task_id=task_id,  # 传递任务ID用于心跳更新
        )
        await strm_processor.genstrm()

        # 记录STRM处理完成进度
        if task:
            strm_completed = len([dt for dt in strm_tasks if dt.status in [DownloadTaskStatus.COMPLETED, DownloadTaskStatus.FAILED]])
            await log_task_progress(task, strm_completed, len(files), "STRM文件处理完成")
    else:
        if task:
            await task.log("📝 没有需要立即处理的STRM生成任务", level="INFO")


async def process_resource_download_tasks_with_retry(task_id: int, download_server: MediaServer, output_dir: str, task: StrmTask, settings, files: List) -> None:
    """
    处理资源下载任务（初始处理，重试由后台服务处理）

    Args:
        task_id: 任务ID
        download_server: 下载服务器
        output_dir: 输出目录
        task: STRM任务对象
        settings: 系统设置
        files: 文件列表
    """
    from tortoise.expressions import Q

    # 检查任务是否已被取消
    if task:
        await task.refresh_from_db()
        if task.status == TaskStatus.CANCELED:
            log.info(f"任务 {task_id} 已被取消，停止资源下载处理")
            return

    # 获取需要处理的资源下载任务（PENDING和立即可处理的RETRY任务）
    download_tasks = await DownloadTask.filter(
        Q(task__id=task_id) &
        Q(process_type="resource_download") &
        (Q(status=DownloadTaskStatus.PENDING) |
         Q(status=DownloadTaskStatus.RETRY, retry_after__lte=datetime.now()) |
         Q(status=DownloadTaskStatus.RETRY, retry_after__isnull=True))
    ).all()

    if download_tasks:
        if task:
            await task.log(f"📦 开始处理 {len(download_tasks)} 个资源下载任务", level="INFO")

        resource_downloader = ResourceDownloader(
            server=download_server,  # 资源下载使用下载服务器
            task=task,
            output_dir=output_dir,
            task_list=download_tasks,
            threads=settings.download_threads,
            task_id=task_id,  # 传递任务ID用于心跳更新
        )
        await resource_downloader.start_download()

        # 记录资源下载完成进度
        if task:
            download_completed = len([dt for dt in download_tasks if dt.status in [DownloadTaskStatus.COMPLETED, DownloadTaskStatus.FAILED]])
            await log_task_progress(task, download_completed, len(files), "资源文件下载完成")
    else:
        if task:
            await task.log("📝 没有需要立即处理的资源下载任务", level="INFO")


class ResourceDownloader:
    """资源文件下载器"""

    def __init__(
        self,
        server: MediaServer,
        output_dir: str,
        task: StrmTask,
        task_list: Optional[List] = None,
        threads: int = 3,
        task_id: Optional[int] = None,
    ):
        self.server = server
        self.output_dir = Path(output_dir)
        self.threads = threads
        self.task_list = task_list
        self.lock = threading.Lock()
        self.task = task
        self.task_id = task_id
        self.retry_interval_seconds = 30  # 默认重试间隔，将在start_download中更新
        self.stats = {
            "total_files": 0,
            "success_files": 0,
            "failed_files": 0,
            "total_size": 0,
            "downloaded_size": 0,
            "start_time": time.time(),
            "download_time": 0,
            "average_speed": 0,
        }
    # 添加下载任务，已经不需要
    # async def add_file(self, file_info: Dict[str, Any]):
    #     await DownloadTask.create(
    #         task=self.task,
    #         source_path=file_info.get("path"),
    #         file_size=file_info.get("size", 0),
    #         file_type=file_info.get("file_type"),
    #         status=DownloadTaskStatus.PENDING,
    #         # 不传会报错，后面会更新类型
    #         process_type=ProcessType.PENDING_WAIT,
    #     )

    async def download_worker(self, task, thread_num: int = 1):
        start_time = time.time()
        file_size = None
        download_speed = None

        try:
            url = self.server.base_url + task.source_path
            # await self.log_download("开始下载文件", "INFO", task.source_path, file_type=task.file_type)

            save_path = self.output_dir / Path(task.source_path).relative_to("/")

            # 使用通用函数确保目录存在
            directory = os.path.dirname(save_path)
            if directory:
                self.ensure_dir_exists(directory)
            #模拟耗时，不要动
            await asyncio.sleep(10)
            # 执行实际下载
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()  # 检查响应状态

                # 获取文件大小
                file_size = len(response.content)

                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(response.content)

            # 计算下载时间和速度
            download_time = time.time() - start_time
            if download_time > 0 and file_size:
                download_speed = file_size / download_time

            # 记录成功日志
            # 格式化文件大小
            if file_size:
                if file_size >= 1024 * 1024 * 1024:  # GB
                    size_str = f"{file_size / (1024 * 1024 * 1024):.2f}GB"
                elif file_size >= 1024 * 1024:  # MB
                    size_str = f"{file_size / (1024 * 1024):.2f}MB"
                elif file_size >= 1024:  # KB
                    size_str = f"{file_size / 1024:.2f}KB"
                else:
                    size_str = f"{file_size}B"
            else:
                size_str = "未知大小"

            # 格式化下载速度
            if download_speed:
                if download_speed >= 1024 * 1024:  # MB/s
                    speed_str = f"{download_speed / (1024 * 1024):.2f}MB/s"
                elif download_speed >= 1024:  # KB/s
                    speed_str = f"{download_speed / 1024:.2f}KB/s"
                else:
                    speed_str = f"{download_speed:.2f}B/s"
            else:
                speed_str = "未知速度"

            await self.log_download(
                f"🧵 [线程{thread_num}] 📥 资源下载成功: {save_path} 📦 {size_str} ⚡ {speed_str} ⏱️ {download_time:.3f}s",
                "INFO",
                task.source_path,
                str(save_path),
                task.file_type,
                file_size,
                download_time,
                download_speed,
                True
            )

            return save_path

        except httpx.HTTPStatusError as e:
            download_time = time.time() - start_time
            error_msg = f"🧵 [线程{thread_num}] 🚫 HTTP错误: {e.response.status_code} - {e.response.reason_phrase} ⏱️ {download_time:.3f}s"
            await self.log_download(
                error_msg,
                "ERROR",
                task.source_path,
                file_type=task.file_type,
                download_time=download_time,
                is_success=False,
                error_message=error_msg
            )
            raise
        except httpx.RequestError as e:
            download_time = time.time() - start_time
            error_msg = f"🧵 [线程{thread_num}] 🌐 网络请求错误: {url} ⏱️ {download_time:.3f}s"
            await self.log_download(
                error_msg,
                "ERROR",
                task.source_path,
                file_type=task.file_type,
                download_time=download_time,
                is_success=False,
                error_message=error_msg
            )
            raise
        except Exception as e:
            download_time = time.time() - start_time
            error_msg = f"🧵 [线程{thread_num}] ⚠️ 未知错误: {get_error_message(e)} ⏱️ {download_time:.3f}s"
            await self.log_download(
                error_msg,
                "ERROR",
                task.source_path,
                file_type=task.file_type,
                download_time=download_time,
                is_success=False,
                error_message=get_error_message(e)
            )
            log.error(f"❌ {error_msg}")
            raise

    async def start_download(self):
        if not self.task_list:
            log.warning("没有任务需要处理")
            return ""

        # 获取系统设置中的重试间隔
        try:
            settings = await system_settings_controller.get_settings()
            self.retry_interval_seconds = settings.get('retry_interval_seconds', 30)
        except Exception as e:
            log.warning(f"获取系统设置失败，使用默认重试间隔30秒: {str(e)}")
            self.retry_interval_seconds = 30

        total_tasks = len(self.task_list)
        # 分批处理，每批次最多处理max_concurrent个任务
        for i in range(0, total_tasks, self.threads):
            # 在每批处理前检查任务是否已被取消
            if self.task:
                await self.task.refresh_from_db()
                if self.task.status == TaskStatus.CANCELED:
                    log.info(f"任务 {self.task_id} 已被取消，停止资源下载处理")
                    return ""

            batch = self.task_list[i : i + self.threads]
            # 创建批处理任务，传递线程号
            batch_tasks = [self.process_single_task(task, thread_num=(idx % self.threads) + 1)
                          for idx, task in enumerate(batch)]

            # 并发执行
            await asyncio.gather(*batch_tasks, return_exceptions=True)

            # 每批处理完成后更新心跳和进度
            if self.task_id:
                # 再次检查任务状态，避免在取消后继续记录进度
                if self.task:
                    await self.task.refresh_from_db()
                    if self.task.status == TaskStatus.CANCELED:
                        log.info(f"任务 {self.task_id} 已被取消，停止进度更新")
                        return ""

                await update_task_heartbeat(self.task_id)
                # 记录资源下载进度
                completed_count = min(i + self.threads, total_tasks)
                await log_task_progress(self.task, completed_count, total_tasks, f"资源下载进度 (批次 {i//self.threads + 1})")

    async def process_single_task(self, task, thread_num: int = 1) -> bool:
        """
        处理单个下载任务

        Args:
            task: 单个任务对象
            thread_num: 线程号（用于日志显示）

        Returns:
            bool: 处理成功返回True，失败返回False
        """
        try:
            # 检查任务是否已被取消
            await task.refresh_from_db()
            main_task = await task.task
            if main_task.status == TaskStatus.CANCELED:
                task.status = DownloadTaskStatus.CANCELED
                task.error_message = "主任务已被取消"
                await task.save()
                # log.info(f"任务已被取消，跳过下载 [path={task.source_path}]")
                return False

            # 如果是重试任务，重置重试相关字段并记录重试开始日志
            if task.status == DownloadTaskStatus.RETRY:
                task.status = DownloadTaskStatus.DOWNLOADING
                task.retry_after = None
                task.error_message = None
                await task.save()

                # 记录重试开始日志到任务日志和数据库
                # 获取文件名用于显示
                file_name = task.source_path.split('/')[-1] if task.source_path else "未知文件"
                retry_start_msg = f"🔄 [线程{thread_num}] [任务{self.task_id}] 开始重试资源下载: {file_name} (第{task.attempt_count + 1}/{task.max_attempts}次尝试)"
                # 记录到任务日志（不记录到数据库，避免重复）
                if self.task:
                    await self.task.log(retry_start_msg, level="INFO")

            rest = await self.download_worker(task, thread_num)
            task.status = DownloadTaskStatus.COMPLETED
            task.target_path = rest
            await task.save()
            return True
        except Exception as e:
            error_msg = get_error_message(e)
            task.error_message = error_msg
            task.attempt_count += 1

            # 如果未达到最大重试次数，标记为重试
            if task.attempt_count < task.max_attempts:
                task.status = DownloadTaskStatus.RETRY
                from datetime import datetime, timedelta
                task.retry_after = datetime.now() + timedelta(seconds=self.retry_interval_seconds)
                task.worker_id = None  # 释放worker
                task.download_started = None  # 重置开始时间
                task.download_completed = None  # 重置完成时间

                # 记录重试日志到任务日志（详细错误信息已在download_worker中记录）
                # 获取文件名用于显示
                file_name = task.source_path.split('/')[-1] if task.source_path else "未知文件"
                retry_msg = f"🔄 [线程{thread_num}] [任务{self.task_id}] 资源下载失败，将在{self.retry_interval_seconds}秒后重试: {file_name} (第{task.attempt_count}/{task.max_attempts}次尝试)"
                # 记录到任务日志（不重复记录到数据库）
                if self.task:
                    await self.task.log(retry_msg, level="WARNING")
            else:
                task.status = DownloadTaskStatus.FAILED
                # 记录最终失败日志到任务日志（详细错误信息已在download_worker中记录）
                # 获取文件名用于显示
                file_name = task.source_path.split('/')[-1] if task.source_path else "未知文件"
                final_fail_msg = f"❌ [线程{thread_num}] [任务{self.task_id}] 资源下载最终失败: {file_name} (已达到最大重试次数 {task.max_attempts}次)"
                # 记录到任务日志（不重复记录到数据库）
                if self.task:
                    await self.task.log(final_fail_msg, level="ERROR")

            await task.save()
            # log.error(f"❌ 处理任务失败 [path={task.source_path}]: {error_msg}")
            return False

    def ensure_dir_exists(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                # print("\n" + Fore.YELLOW + f"📁 创建目录: {directory}")

                return True
            return True
        except Exception as e:
            log.error(f"❌ 创建目录失败: {str(e)}")
            return False

    async def log_download(
        self,
        message: str,
        level: str = "INFO",
        file_path: str = "",
        target_path: str = None,
        file_type: FileType = FileType.OTHER,
        file_size: int = None,
        download_time: float = None,
        download_speed: float = None,
        is_success: bool = True,
        error_message: str = None,
    ) -> None:
        """
        记录下载日志到数据库

        Args:
            message: 日志消息
            level: 日志级别，默认为INFO
            file_path: 文件路径
            target_path: 目标路径
            file_type: 文件类型
            file_size: 文件大小
            download_time: 下载耗时
            download_speed: 下载速度
            is_success: 是否成功
            error_message: 错误信息
        """
        try:
            # 创建下载日志记录
            log_entry = DownloadLog(
                task=self.task,
                file_path=file_path or "",
                target_path=target_path,
                file_type=file_type,
                file_size=file_size,
                download_time=download_time,
                download_speed=download_speed,
                is_success=is_success,
                error_message=error_message,
                log_level=level,
                log_message=message,
            )

            # 保存到数据库
            await log_entry.save()

        except Exception as e:
            # 如果数据库记录失败，至少记录到控制台
            log.error(f"记录下载日志到数据库失败: {str(e)}")


async def process_directory_tree(
    server_id: int,
    files: List[Dict[str, Any]],
    output_dir: str,
    task_id: Optional[int] = None,
    download_server_id: Optional[int] = None,
    threads: int = 1,
    verbose_console_logging: bool = False,
) -> Dict[str, Any]:
    """
    处理文件目录树，生成STRM文件和下载资源文件

    Args:
        server_id: 媒体服务器ID
        files: 文件列表
        output_dir: 输出目录
        task_id: 任务ID
        download_server_id: 下载服务器ID
        threads: 下载线程数
        verbose_console_logging: 是否输出详细日志到控制台

    Returns:
        处理结果
    """
    try:
        # 获取媒体服务器
        server = await MediaServer.get_or_none(id=server_id)
        if not server:
            raise ValueError(f"找不到ID为{server_id}的媒体服务器")

        # 获取下载服务器（如果有）
        download_server = None
        if download_server_id:
            download_server = await MediaServer.get_or_none(id=download_server_id)
            if not download_server:
                raise ValueError(f"找不到ID为{download_server_id}的下载服务器")
        else:
            # 默认使用媒体服务器作为下载服务器
            download_server = server

        # 获取任务
        task = None
        if task_id:
            task = await StrmTask.get_or_none(id=task_id)
            if not task:
                # 添加错误日志
                log.error(f"找不到ID为{task_id}的任务")
                raise ValueError(f"找不到ID为{task_id}的任务")
            else:
                # 添加详细的调试日志
                print(f"[DEBUG] 获取到任务对象: ID={task.id}, 名称={task.name}, 类型={type(task)}")
                print(f"[DEBUG] 任务详情: 状态={task.status}, 总文件数={task.total_files}, 输出目录={task.output_dir}")

        # 获取系统设置
        settings = await system_settings_controller.get_settings()
        settings = SimpleNamespace(**settings)
        settings_dict = {
            "settings_version": settings.settings_version,
            "video_file_types": settings.video_file_types,
            "audio_file_types": settings.audio_file_types,
            "image_file_types": settings.image_file_types,
            "subtitle_file_types": settings.subtitle_file_types,
            "metadata_file_types": settings.metadata_file_types,
            "enable_path_replacement": settings.enable_path_replacement,
            "replacement_path": settings.replacement_path,
            "download_threads": settings.download_threads,
        }

        # 如果有任务对象，记录处理器级别的系统设置信息
        if task:
            await log_processor_settings_to_task(task, settings, server, download_server, len(files))
            # 记录初始进度信息
            await log_task_progress(task, 0, len(files), "开始处理")

        # 记录开始时间
        start_time = datetime.now()

        # 统计数据
        stats = {
            "total": len(files),
            "processed": 0,
            "success_strm": 0,
            "failed_strm": 0,
            "success_download": 0,
            "failed_download": 0,
            "time": 0,
        }
        # 从数据库获取strm任务项
        if task_id:
            # 检查任务是否已被取消
            await task.refresh_from_db()
            if task.status == TaskStatus.CANCELED:
                log.info(f"任务 {task_id} 已被取消，停止处理")
                return stats

            # 更新任务心跳
            await update_task_heartbeat(task_id)

            # 处理STRM生成任务（包含重试逻辑）
            await process_strm_tasks_with_retry(task_id, server, output_dir, task, settings, files)

            # 再次检查任务是否已被取消
            await task.refresh_from_db()
            if task.status == TaskStatus.CANCELED:
                log.info(f"任务 {task_id} 已被取消，停止处理")
                return stats

            # 更新任务心跳
            await update_task_heartbeat(task_id)

            # 处理资源下载任务（包含重试逻辑）
            await process_resource_download_tasks_with_retry(task_id, download_server, output_dir, task, settings, files)

        #添加下载任务已在start_strm_task中处理，此处不再需要
        # files_added = 0
        # for file_info in files:
        #     if file_info.get("is_dir", False):
        #         continue
        #
        #     file_type_parser = TreeParser(settings_dict)
        #     file_type = (
        #         file_type_parser.get_file_type(file_info.get("path", ""))
        #         if hasattr(file_type_parser, "get_file_type")
        #         else FileType.OTHER
        #     )
        #     file_info["file_type"] = file_type
        #     if file_type in [FileType.VIDEO, FileType.AUDIO, FileType.IMAGE, FileType.SUBTITLE, FileType.METADATA]:
        #         await strm_processor.add_file(file_info=file_info)
        #         files_added += 1
        #         if files_added % 100 == 0:
        #             log.info(f"已添加 {files_added} 个文件到下载队列")
        #
        # log.info(f"总计添加了 {files_added} 个文件到下载队列")
        # 计算处理时间
        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()
        stats["time"] = elapsed_time

        # 更新任务状态
        if task:
            # 在更新状态前检查任务是否已被取消
            await task.refresh_from_db()
            if task.status == TaskStatus.CANCELED:
                log.info(f"任务 {task_id} 已被取消，保持取消状态不变")
                # 即使任务被取消，也要更新统计信息和结束时间
                task.end_time = end_time
                task.download_duration = elapsed_time
                await task.log("任务已被取消，处理停止", level="INFO")
            else:
                # 任务未被取消，从数据库获取实际的统计数据
                # 获取所有相关的下载任务
                all_download_tasks = await DownloadTask.filter(task_id=task.id).all()

                # 分类统计
                strm_tasks = [dt for dt in all_download_tasks if dt.process_type == "strm_generation"]
                resource_tasks = [dt for dt in all_download_tasks if dt.process_type == "resource_download"]

                # 统计STRM文件
                strm_success = sum(1 for dt in strm_tasks if dt.status == DownloadTaskStatus.COMPLETED)
                strm_failed = sum(1 for dt in strm_tasks if dt.status == DownloadTaskStatus.FAILED)

                # 统计资源文件
                resource_success = sum(1 for dt in resource_tasks if dt.status == DownloadTaskStatus.COMPLETED)
                resource_failed = sum(1 for dt in resource_tasks if dt.status == DownloadTaskStatus.FAILED)

                # 更新任务统计信息
                task.end_time = end_time
                task.processed_files = strm_success + strm_failed + resource_success + resource_failed
                task.success_files = strm_success + resource_success
                task.failed_files = strm_failed + resource_failed
                task.download_duration = elapsed_time

                # 根据所有文件处理结果决定任务状态
                if strm_failed > 0 or resource_failed > 0:
                    # 如果有任何文件处理失败，设置为失败状态
                    task.status = TaskStatus.FAILED
                    if strm_failed > 0 and resource_failed > 0:
                        await task.log(f"任务失败：有 {strm_failed} 个STRM文件生成失败，{resource_failed} 个资源文件下载失败", level="ERROR")
                    elif strm_failed > 0:
                        await task.log(f"任务失败：有 {strm_failed} 个STRM文件生成失败", level="ERROR")
                    else:
                        await task.log(f"任务失败：有 {resource_failed} 个资源文件下载失败", level="ERROR")
                else:
                    # 只有全部成功，才设置为完成状态
                    task.status = TaskStatus.COMPLETED
                    await task.log("任务完全成功：所有文件处理成功", level="INFO")

                # 记录最终进度和统计信息
                total_processed = strm_success + strm_failed + resource_success + resource_failed
                await log_task_progress(task, total_processed, len(all_download_tasks), "任务完成")

                # 生成详细的处理总结
                await task.log("=" * 60, level="INFO")
                await task.log("🎯 任务完成统计", level="INFO")
                await task.log(f"⏱️ 总耗时: {elapsed_time:.2f} 秒", level="INFO")
                await task.log(f"📁 总文件数: {len(all_download_tasks)}", level="INFO")
                await task.log(f"✅ 成功处理: {strm_success + resource_success} 个文件", level="INFO")
                await task.log(f"❌ 处理失败: {strm_failed + resource_failed} 个文件", level="INFO")
                if strm_tasks:
                    await task.log(f"🎬 STRM文件: 成功 {strm_success} 个，失败 {strm_failed} 个", level="INFO")
                if resource_tasks:
                    await task.log(f"📦 资源文件: 成功 {resource_success} 个，失败 {resource_failed} 个", level="INFO")

                # 计算成功率
                if len(all_download_tasks) > 0:
                    success_rate = round((strm_success + resource_success) / len(all_download_tasks) * 100, 1)
                    await task.log(f"📊 成功率: {success_rate}%", level="INFO")

                await task.log("=" * 60, level="INFO")

            await task.save()

        return stats
    except Exception as e:
        error_msg = get_error_message(e)
        log.error(f"处理文件目录树时发生错误: {error_msg}")

        # 更新任务状态为失败
        if task_id:
            task = await StrmTask.get_or_none(id=task_id)
            if task:
                task.status = TaskStatus.FAILED
                await task.log(f"处理文件目录树时发生错误: {error_msg}", level="ERROR")
                await task.save()

        # 重新抛出异常，让上层处理
        raise


def is_summary_log(message: str) -> bool:
    """
    判断是否为汇总日志

    Args:
        message: 日志消息

    Returns:
        是否为汇总日志
    """
    summary_keywords = [
        "总耗时",
        "下载完成",
        "任务统计",
        "总文件数",
        "成功文件数",
        "失败文件数",
        "平均速度",
        "汇总",
        "总计",
        "summary",
        "开始多线程下载",
        "队列中文件数",
    ]

    return any(keyword in message for keyword in summary_keywords)


class strm_downaload:
    def __init__(
        self,
        server: MediaServer,
        output_dir: str,
        max_threads: int,
        task: StrmTask,
        enable_path_replacement: bool = False,
        replacement_path: str = "/nas",
        task_list: Optional[List] = None,
        task_id: Optional[int] = None,
    ):
        self.server = server
        self.output_dir = output_dir
        self.base_url = server.base_url
        self.enable_path_replacement = enable_path_replacement
        self.replacement_path = replacement_path
        self.max_threads = max_threads
        self.task = task
        # 下载列表
        self.task_list = task_list
        self.task_id = task_id
        self.retry_interval_seconds = 30  # 默认重试间隔，将在genstrm中更新

    async def genstrm(self):
        """
        并发处理STRM任务

        Args:
            max_concurrent: 最大并发数，默认20
        """
        if not self.task_list:
            log.warning("没有任务需要处理")
            return

        # 获取系统设置中的重试间隔
        try:
            settings = await system_settings_controller.get_settings()
            self.retry_interval_seconds = settings.get('retry_interval_seconds', 30)
        except Exception as e:
            log.warning(f"获取系统设置失败，使用默认重试间隔30秒: {str(e)}")
            self.retry_interval_seconds = 30

        total_tasks = len(self.task_list)

        # 分批处理，每批次最多处理max_concurrent个任务
        for i in range(0, total_tasks, self.max_threads):
            # 在每批处理前检查任务是否已被取消
            if self.task:
                await self.task.refresh_from_db()
                if self.task.status == TaskStatus.CANCELED:
                    log.info(f"任务 {self.task_id} 已被取消，停止STRM生成处理")
                    return

            batch = self.task_list[i : i + self.max_threads]
            # 创建批处理任务，传递线程号
            batch_tasks = [self.process_single_task(task, thread_num=(idx % self.max_threads) + 1)
                          for idx, task in enumerate(batch)]

            # 并发执行
            await asyncio.gather(*batch_tasks, return_exceptions=True)

            # 每批处理完成后更新心跳和进度
            if self.task_id:
                # 再次检查任务状态，避免在取消后继续记录进度
                if self.task:
                    await self.task.refresh_from_db()
                    if self.task.status == TaskStatus.CANCELED:
                        log.info(f"任务 {self.task_id} 已被取消，停止进度更新")
                        return

                await update_task_heartbeat(self.task_id)
                # 记录STRM生成进度
                completed_count = min(i + self.max_threads, total_tasks)
                await log_task_progress(self.task, completed_count, total_tasks, f"STRM生成进度 (批次 {i//self.max_threads + 1})")

    async def process_single_task(self, task, thread_num: int = 1) -> bool:
        """
        处理单个STRM任务

        Args:
            task: 单个任务对象
            thread_num: 线程号（用于日志显示）

        Returns:
            bool: 处理成功返回True，失败返回False
        """
        try:
            # 检查任务是否已被取消
            await task.refresh_from_db()
            main_task = await task.task
            if main_task.status == TaskStatus.CANCELED:
                task.status = DownloadTaskStatus.CANCELED
                task.error_message = "主任务已被取消"
                await task.save()
                log.info(f"任务已被取消，跳过处理 [path={task.source_path}]")
                return False

            # 如果是重试任务，重置重试相关字段并记录重试开始日志
            if task.status == DownloadTaskStatus.RETRY:
                task.status = DownloadTaskStatus.DOWNLOADING
                task.retry_after = None
                task.error_message = None
                await task.save()

                # 记录重试开始日志到任务日志
                # 获取文件名用于显示
                file_name = task.source_path.split('/')[-1] if task.source_path else "未知文件"
                retry_start_msg = f"🔄 [线程{thread_num}] [任务{self.task_id}] 开始重试STRM生成: {file_name} (第{task.attempt_count + 1}/{task.max_attempts}次尝试)"
                # 记录到任务日志（不记录到数据库，避免重复）
                if self.task:
                    await self.task.log(retry_start_msg, level="INFO")

            rest = await self.createstrm(task.source_path, self.server.base_url, self.output_dir, thread_num)
            task.status = DownloadTaskStatus.COMPLETED
            task.target_path = rest
            await task.save()
            return True
        except Exception as e:
            error_msg = get_error_message(e)
            task.error_message = error_msg
            task.attempt_count += 1

            # 如果未达到最大重试次数，标记为重试
            if task.attempt_count < task.max_attempts:
                task.status = DownloadTaskStatus.RETRY
                from datetime import datetime, timedelta
                task.retry_after = datetime.now() + timedelta(seconds=self.retry_interval_seconds)
                task.worker_id = None  # 释放worker
                task.download_started = None  # 重置开始时间
                task.download_completed = None  # 重置完成时间

                # 记录重试日志到任务日志（详细错误信息已在createstrm中记录）
                # 获取文件名用于显示
                file_name = task.source_path.split('/')[-1] if task.source_path else "未知文件"
                retry_msg = f"🔄 [线程{thread_num}] [任务{self.task_id}] STRM生成失败，将在{self.retry_interval_seconds}秒后重试: {file_name} (第{task.attempt_count}/{task.max_attempts}次尝试)"
                # 记录到任务日志（不重复记录到数据库）
                if self.task:
                    await self.task.log(retry_msg, level="WARNING")
            else:
                task.status = DownloadTaskStatus.FAILED
                # 记录最终失败日志到任务日志（详细错误信息已在createstrm中记录）
                # 获取文件名用于显示
                file_name = task.source_path.split('/')[-1] if task.source_path else "未知文件"
                final_fail_msg = f"❌ [线程{thread_num}] [任务{self.task_id}] STRM生成最终失败: {file_name} (已达到最大重试次数 {task.max_attempts}次)"
                # 记录到任务日志（不重复记录到数据库）
                if self.task:
                    await self.task.log(final_fail_msg, level="ERROR")

            await task.save()
            log.error(f"❌ 处理任务失败 [path={task.source_path}]: {error_msg}")
            return False

    async def createstrm(self, filepath, hosts, save_path, thread_num: int = 1):
        start_time = time.time()
        target_path = None

        try:

            # 路径替换功能
            if self.enable_path_replacement:
                url = hosts + quote(self.replace_base_path(filepath, self.replacement_path))
            else:
                url = hosts + quote(filepath)
            root, ext = os.path.splitext(filepath)
            # 新后缀名（例如改为 .mp4）
            new_extension = ".strm"
            from pathlib import Path

            # 拼接新路径
            new_path = root + new_extension
            # 拼接保存路径
            target_path = save_path / Path(new_path).relative_to("/")
            # 使用通用函数确保目录存在
            directory = os.path.dirname(target_path)
            if directory:
                self.ensure_dir_exists(directory)
            async with aiofiles.open(target_path, "w") as f:
                await f.write(url)

            # 计算生成时间
            generation_time = time.time() - start_time

            # 记录成功日志
            await self.log_strm(
                f"🧵 [线程{thread_num}] 🎬 STRM文件生成成功: {target_path} ⏱️ {generation_time:.3f}s",
                "INFO",
                filepath,
                str(target_path),
                True,
                generation_time=generation_time
            )

            return target_path
        except Exception as e:
            error_msg = get_error_message(e)
            generation_time = time.time() - start_time

            # 记录失败日志
            await self.log_strm(
                f"🧵 [线程{thread_num}] 💥 STRM文件生成失败: {error_msg} ⏱️ {generation_time:.3f}s",
                "ERROR",
                filepath,
                str(target_path) if target_path else None,
                False,
                error_message=error_msg,
                generation_time=generation_time
            )

            log.error(f"STRM文件生成错误: {error_msg}")
            log.error(f"❌ 📄{target_path}生成失败")
            raise  # 重新抛出异常给上层

    def replace_base_path(self, original_path, new_base_path):
        """
        替换路径中的主路径部分

        Args:
            original_path (str): 原始路径，如"/nas/动漫/一拳超人/S01E01.mkv"
            new_base_path (str): 新的主路径，nas2 "/nas2/动漫/一拳超人/S01E01.mkv"

        Returns:
            str: 替换主路径后的新路径
        """
        try:
            # 如果new_base_path头尾有/，则去掉
            if new_base_path.startswith("/"):
                new_base_path = new_base_path[1:]
            if new_base_path.endswith("/"):
                new_base_path = new_base_path[:-1]
            # 使用根对路径分割
            pathlist = original_path.split("/")
            # 替换第一层主路径
            pathlist[1] = new_base_path
            # 合并路径
            new_path = "/".join(pathlist)
            return new_path

        except Exception as e:
            log.error(f"❌ 替换路径错误: {str(e)}")
            return original_path

    def ensure_dir_exists(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                # print("\n" + Fore.YELLOW + f"📁 创建目录: {directory}")

                return True
            return True
        except Exception as e:
            log.error(f"❌ 创建目录失败: {str(e)}")
            return False

    async def log_download(
        self,
        message: str,
        level: str = "INFO",
        file_path: str = "",
        target_path: str = None,
        file_type: FileType = FileType.OTHER,
        file_size: int = None,
        download_time: float = None,
        download_speed: float = None,
        is_success: bool = True,
        error_message: str = None,
    ) -> None:
        """
        记录下载日志到数据库

        Args:
            message: 日志消息
            level: 日志级别，默认为INFO
            file_path: 文件路径
            target_path: 目标路径
            file_type: 文件类型
            file_size: 文件大小
            download_time: 下载耗时
            download_speed: 下载速度
            is_success: 是否成功
            error_message: 错误信息
        """
        try:
            # 创建下载日志记录
            log_entry = DownloadLog(
                task=self.task,
                file_path=file_path or "",
                target_path=target_path,
                file_type=file_type,
                file_size=file_size,
                download_time=download_time,
                download_speed=download_speed,
                is_success=is_success,
                error_message=error_message,
                log_level=level,
                log_message=message,
            )

            # 保存到数据库
            await log_entry.save()

        except Exception as e:
            # 如果数据库记录失败，至少记录到控制台
            log.error(f"记录下载日志到数据库失败: {str(e)}")

    async def log_strm(
        self,
        message: str,
        level: str = "INFO",
        source_path: str = "",
        target_path: str = None,
        is_success: bool = True,
        error_message: str = None,
        generation_time: float = None,
        file_type: FileType = FileType.VIDEO,
    ) -> None:
        """
        记录STRM生成日志到数据库

        Args:
            message: 日志消息
            level: 日志级别，默认为INFO
            source_path: 源文件路径
            target_path: 目标STRM文件路径
            is_success: 是否成功
            error_message: 错误信息
            generation_time: 生成耗时
            file_type: 文件类型
        """
        try:
            # 创建STRM生成日志记录
            log_entry = StrmLog(
                task=self.task,
                source_path=source_path or "",
                target_path=target_path,
                file_type=file_type,
                is_success=is_success,
                error_message=error_message,
                log_level=level,
                log_message=message,
                generation_time=generation_time,
            )

            # 保存到数据库
            await log_entry.save()

        except Exception as e:
            # 如果数据库记录失败，至少记录到控制台
            log.error(f"记录STRM生成日志到数据库失败: {str(e)}")


async def update_task_heartbeat(task_id: int):
    """更新任务心跳时间"""
    try:
        from app.core.task_recovery import TaskRecoveryService
        await TaskRecoveryService.add_heartbeat_to_task(task_id)
    except Exception as e:
        log.debug(f"更新任务 {task_id} 心跳失败: {str(e)}")
