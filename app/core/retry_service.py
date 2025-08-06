"""
重试服务 - 处理失败任务的重试逻辑
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from tortoise.expressions import Q

from app.models.strm import DownloadTask, DownloadTaskStatus, StrmTask, TaskStatus, MediaServer, SystemSettings
from app.utils.strm.processor import ResourceDownloader, strm_downaload, update_task_heartbeat
from app.controllers.strm import system_settings_controller
from types import SimpleNamespace

log = logging.getLogger(__name__)


class RetryService:
    """重试服务类"""
    
    _instance = None
    _running = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def start_retry_service(cls):
        """启动重试服务"""
        if cls._running:
            log.info("重试服务已在运行中")
            return
        
        cls._running = True
        log.info("🔄 启动重试服务...")
        
        # 创建后台任务
        asyncio.create_task(cls._retry_loop())
    
    @classmethod
    async def stop_retry_service(cls):
        """停止重试服务"""
        cls._running = False
        log.info("🛑 重试服务已停止")
    
    @classmethod
    async def _retry_loop(cls):
        """重试服务主循环"""
        while cls._running:
            try:
                await cls._process_retry_tasks()
                await asyncio.sleep(10)  # 每10秒检查一次
            except Exception as e:
                log.error(f"❌ 重试服务处理时发生错误: {str(e)}")
                await asyncio.sleep(30)  # 出错后等待30秒再重试
    
    @classmethod
    async def _process_retry_tasks(cls):
        """处理重试任务"""
        try:
            # 获取所有到期的重试任务
            retry_tasks = await DownloadTask.filter(
                Q(status=DownloadTaskStatus.RETRY) &
                (Q(retry_after__lte=datetime.now()) | Q(retry_after__isnull=True))
            ).prefetch_related('task').all()
            
            if not retry_tasks:
                return
            
            log.info(f"🔄 发现 {len(retry_tasks)} 个到期的重试任务")
            
            # 按任务ID分组
            tasks_by_task_id = {}
            for retry_task in retry_tasks:
                task_id = retry_task.task.id
                if task_id not in tasks_by_task_id:
                    tasks_by_task_id[task_id] = []
                tasks_by_task_id[task_id].append(retry_task)
            
            # 处理每个任务的重试
            for task_id, task_retry_list in tasks_by_task_id.items():
                await cls._process_task_retries(task_id, task_retry_list)
                
        except Exception as e:
            log.error(f"❌ 处理重试任务时发生错误: {str(e)}")
    
    @classmethod
    async def _process_task_retries(cls, task_id: int, retry_tasks: List[DownloadTask]):
        """处理单个任务的重试"""
        try:
            # 获取主任务
            main_task = await StrmTask.get_or_none(id=task_id)
            if not main_task:
                log.warning(f"找不到任务 {task_id}，跳过重试处理")
                return
            
            # 检查任务状态
            if main_task.status in [TaskStatus.CANCELED, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                log.info(f"任务 {task_id} 状态为 {main_task.status}，跳过重试处理")
                return
            
            # 获取系统设置
            settings = await system_settings_controller.get_settings()
            settings = SimpleNamespace(**settings)
            
            # 分类重试任务
            strm_retries = [t for t in retry_tasks if t.process_type == "strm_generation"]
            download_retries = [t for t in retry_tasks if t.process_type == "resource_download"]
            
            # 处理STRM重试
            if strm_retries:
                await cls._process_strm_retries(main_task, strm_retries, settings)
            
            # 处理资源下载重试
            if download_retries:
                await cls._process_download_retries(main_task, download_retries, settings)
                
            # 更新任务心跳
            await update_task_heartbeat(task_id)
            
        except Exception as e:
            log.error(f"❌ 处理任务 {task_id} 重试时发生错误: {str(e)}")
    
    @classmethod
    async def _process_strm_retries(cls, main_task: StrmTask, strm_retries: List[DownloadTask], settings):
        """处理STRM生成重试"""
        try:
            # 获取媒体服务器
            server = await MediaServer.get_or_none(id=main_task.server_id)
            if not server:
                log.error(f"找不到媒体服务器 {main_task.server_id}")
                return
            
            await main_task.log(f"🔄 [重试服务] [任务{main_task.id}] 开始处理 {len(strm_retries)} 个STRM生成重试任务", level="INFO")
            
            # 创建STRM处理器
            strm_processor = strm_downaload(
                server=server,
                output_dir=main_task.output_dir,
                task=main_task,
                enable_path_replacement=settings.enable_path_replacement,
                replacement_path=settings.replacement_path,
                task_list=strm_retries,
                max_threads=settings.download_threads,
                task_id=main_task.id,
            )
            
            # 处理重试任务
            await strm_processor.genstrm()
            
        except Exception as e:
            log.error(f"❌ 处理STRM重试时发生错误: {str(e)}")
    
    @classmethod
    async def _process_download_retries(cls, main_task: StrmTask, download_retries: List[DownloadTask], settings):
        """处理资源下载重试"""
        try:
            # 获取下载服务器
            download_server_id = main_task.download_server_id or main_task.server_id
            download_server = await MediaServer.get_or_none(id=download_server_id)
            if not download_server:
                log.error(f"找不到下载服务器 {download_server_id}")
                return
            
            await main_task.log(f"🔄 [重试服务] [任务{main_task.id}] 开始处理 {len(download_retries)} 个资源下载重试任务", level="INFO")
            
            # 创建资源下载器
            resource_downloader = ResourceDownloader(
                server=download_server,
                task=main_task,
                output_dir=main_task.output_dir,
                task_list=download_retries,
                threads=settings.download_threads,
                task_id=main_task.id,
            )
            
            # 处理重试任务
            await resource_downloader.start_download()
            
        except Exception as e:
            log.error(f"❌ 处理资源下载重试时发生错误: {str(e)}")


async def setup_retry_service():
    """设置重试服务，应在应用启动时调用"""
    log.info("🚀 正在设置重试服务...")
    
    try:
        await RetryService.start_retry_service()
        log.info("✅ 重试服务已设置完成")
        
    except Exception as e:
        log.error(f"❌ 设置重试服务时发生错误: {str(e)}")
        raise


async def shutdown_retry_service():
    """关闭重试服务，应在应用关闭时调用"""
    log.info("🛑 正在关闭重试服务...")
    
    try:
        await RetryService.stop_retry_service()
        log.info("✅ 重试服务已关闭")
        
    except Exception as e:
        log.error(f"❌ 关闭重试服务时发生错误: {str(e)}")
