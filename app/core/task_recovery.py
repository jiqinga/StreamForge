"""
任务状态修复服务
用于处理程序异常终止或重启后的任务状态修复
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.models.strm import StrmTask, DownloadTask, TaskStatus, DownloadTaskStatus, SystemSettings
from app.log.log import log


async def get_task_recovery_config():
    """从数据库获取任务恢复配置"""
    try:
        settings = await SystemSettings.all().first()
        if settings:
            return {
                'enable_periodic_check': settings.enable_task_recovery_periodic_check,
                'check_interval': settings.task_recovery_check_interval,
                'task_timeout_hours': settings.task_timeout_hours,
                'heartbeat_timeout_minutes': settings.heartbeat_timeout_minutes,
                'activity_check_minutes': settings.activity_check_minutes,
                'recent_activity_minutes': settings.recent_activity_minutes,
            }
        else:
            # 返回默认配置
            return {
                'enable_periodic_check': True,
                'check_interval': 1800,  # 30分钟
                'task_timeout_hours': 2,
                'heartbeat_timeout_minutes': 10,
                'activity_check_minutes': 30,
                'recent_activity_minutes': 5,
            }
    except Exception as e:
        log.error(f"获取任务恢复配置失败: {str(e)}")
        # 返回默认配置
        return {
            'enable_periodic_check': True,
            'check_interval': 1800,
            'task_timeout_hours': 2,
            'heartbeat_timeout_minutes': 10,
            'activity_check_minutes': 30,
            'recent_activity_minutes': 5,
        }


class TaskRecoveryService:
    """任务状态修复服务"""

    @staticmethod
    def _normalize_datetime(dt: datetime) -> datetime:
        """
        标准化 datetime 对象，统一转换为 naive datetime

        Args:
            dt: 要标准化的 datetime 对象

        Returns:
            标准化后的 naive datetime 对象
        """
        if dt is None:
            return None

        # 如果是 timezone-aware datetime，转换为本地时间并去掉时区信息
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)

        return dt

    @staticmethod
    def _get_current_time() -> datetime:
        """获取当前时间（naive datetime）"""
        return datetime.now()
    
    @classmethod
    async def recover_orphaned_tasks(cls) -> Dict[str, Any]:
        """
        修复孤儿任务（程序重启后状态异常的任务）
        
        Returns:
            修复结果统计
        """
        log.info("🔍 开始检查和修复孤儿任务...")
        
        stats = {
            "checked_tasks": 0,
            "recovered_tasks": 0,
            "timeout_tasks": 0,
            "details": []
        }
        
        try:
            # 查找所有运行中的主任务
            running_tasks = await StrmTask.filter(status=TaskStatus.RUNNING).all()
            stats["checked_tasks"] = len(running_tasks)
            
            if len(running_tasks) == 0:
                log.info("✅ 没有发现运行中的任务")
                return stats
            
            log.info(f"🔍 发现 {len(running_tasks)} 个运行中的任务，开始检查...")
            
            for task in running_tasks:
                try:
                    recovery_result = await cls._recover_single_task(task)
                    stats["details"].append(recovery_result)
                    
                    if recovery_result["action"] == "recovered":
                        stats["recovered_tasks"] += 1
                    elif recovery_result["action"] == "timeout":
                        stats["timeout_tasks"] += 1
                        
                except Exception as e:
                    log.error(f"❌ 修复任务 {task.id} 时发生错误: {str(e)}")
                    stats["details"].append({
                        "task_id": task.id,
                        "task_name": task.name,
                        "action": "error",
                        "reason": str(e)
                    })
            
            # 修复下载任务状态
            download_stats = await cls._recover_download_tasks()
            
            log.info(f"✅ 任务修复完成: 检查了 {stats['checked_tasks']} 个任务，"
                    f"修复了 {stats['recovered_tasks']} 个主任务，"
                    f"修复了 {download_stats['recovered_count']} 个下载任务")
            
            return stats
            
        except Exception as e:
            log.error(f"❌ 任务修复过程中发生错误: {str(e)}")
            raise
    
    @classmethod
    async def _recover_single_task(cls, task: StrmTask) -> Dict[str, Any]:
        """
        修复单个任务

        Args:
            task: 要修复的任务

        Returns:
            修复结果
        """
        current_time = cls._get_current_time()

        # 检查任务是否超时
        config = await get_task_recovery_config()
        if task.start_time:
            # 标准化时间对象
            start_time = cls._normalize_datetime(task.start_time)
            if start_time:
                elapsed_time = current_time - start_time
                max_execution_time = timedelta(hours=config['task_timeout_hours'])

                if elapsed_time > max_execution_time:
                    # 任务超时，标记为失败
                    task.status = TaskStatus.FAILED
                    task.end_time = current_time
                    await task.log(f"任务因超时被自动标记为失败 (运行时间: {elapsed_time})", level="ERROR")
                    await task.save()

                    # 同时取消相关的下载任务
                    await cls._cancel_related_download_tasks(task.id)

                    log.warning(f"⏰ 任务 {task.id} ({task.name}) 因超时被标记为失败")

                    return {
                        "task_id": task.id,
                        "task_name": task.name,
                        "action": "timeout",
                        "reason": f"任务超时 (运行时间: {elapsed_time})",
                        "elapsed_time": str(elapsed_time)
                    }
        
        # 检查心跳时间（如果任务模型有 last_heartbeat 字段）
        if hasattr(task, 'last_heartbeat') and task.last_heartbeat:
            # 标准化心跳时间
            last_heartbeat = cls._normalize_datetime(task.last_heartbeat)
            if last_heartbeat:
                heartbeat_timeout = timedelta(minutes=config['heartbeat_timeout_minutes'])
                if current_time - last_heartbeat > heartbeat_timeout:
                    task.status = TaskStatus.FAILED
                    task.end_time = current_time
                    await task.log("任务因心跳超时被自动标记为失败", level="ERROR")
                    await task.save()

                    await cls._cancel_related_download_tasks(task.id)

                    log.warning(f"💔 任务 {task.id} ({task.name}) 因心跳超时被标记为失败")

                    return {
                        "task_id": task.id,
                        "task_name": task.name,
                        "action": "recovered",
                        "reason": "心跳超时"
                    }
        
        # 如果任务开始时间超过30分钟但没有心跳记录，可能是程序重启前的任务
        if task.start_time:
            # 标准化开始时间
            start_time = cls._normalize_datetime(task.start_time)
            if start_time:
                elapsed_time = current_time - start_time
                if elapsed_time > timedelta(minutes=config['activity_check_minutes']):
                    # 检查是否有任何下载任务在最近有更新
                    recent_activity = await cls._check_recent_activity(task.id)

                    if not recent_activity:
                        task.status = TaskStatus.FAILED
                        task.end_time = current_time
                        await task.log("任务因程序重启后无活动被自动标记为失败", level="ERROR")
                        await task.save()

                        await cls._cancel_related_download_tasks(task.id)

                        log.warning(f"🔄 任务 {task.id} ({task.name}) 因程序重启后无活动被标记为失败")

                        return {
                            "task_id": task.id,
                            "task_name": task.name,
                            "action": "recovered",
                            "reason": "程序重启后无活动"
                        }
        
        # 如果没有明确的异常指标，保持当前状态
        return {
            "task_id": task.id,
            "task_name": task.name,
            "action": "checked",
            "reason": "任务状态正常"
        }
    
    @classmethod
    async def _check_recent_activity(cls, task_id: int) -> bool:
        """检查任务是否有最近的活动"""
        # 检查最近几分钟内是否有下载任务状态更新
        config = await get_task_recovery_config()
        current_time = cls._get_current_time()
        recent_time = current_time - timedelta(minutes=config['recent_activity_minutes'])

        # recent_time 已经是 naive datetime

        recent_updates = await DownloadTask.filter(
            task_id=task_id,
            update_time__gte=recent_time
        ).count()

        return recent_updates > 0
    
    @classmethod
    async def _cancel_related_download_tasks(cls, task_id: int):
        """取消相关的下载任务"""
        download_tasks = await DownloadTask.filter(
            task_id=task_id,
            status__in=[DownloadTaskStatus.PENDING, DownloadTaskStatus.DOWNLOADING, DownloadTaskStatus.RETRY]
        ).all()
        
        for dt in download_tasks:
            dt.status = DownloadTaskStatus.FAILED
            await dt.save()
        
        if len(download_tasks) > 0:
            log.info(f"📋 已将任务 {task_id} 的 {len(download_tasks)} 个相关下载任务标记为失败")
    
    @classmethod
    async def _recover_download_tasks(cls) -> Dict[str, int]:
        """修复下载任务状态"""
        # 查找状态为 DOWNLOADING 但可能已经停止的下载任务
        downloading_tasks = await DownloadTask.filter(status=DownloadTaskStatus.DOWNLOADING).all()
        
        recovered_count = 0
        for dt in downloading_tasks:
            # 检查主任务状态
            main_task = await dt.task
            if main_task.status in [TaskStatus.FAILED, TaskStatus.CANCELED, TaskStatus.COMPLETED]:
                # 主任务已结束，下载任务也应该结束
                if main_task.status == TaskStatus.CANCELED:
                    dt.status = DownloadTaskStatus.CANCELED
                else:
                    dt.status = DownloadTaskStatus.FAILED
                
                await dt.save()
                recovered_count += 1
        
        if recovered_count > 0:
            log.info(f"📥 修复了 {recovered_count} 个下载任务的状态")
        
        return {"recovered_count": recovered_count}
    
    @classmethod
    async def add_heartbeat_to_task(cls, task_id: int):
        """为任务添加心跳（如果支持的话）"""
        try:
            task = await StrmTask.get_or_none(id=task_id)
            if task and hasattr(task, 'last_heartbeat'):
                # 使用 naive datetime 以匹配数据库格式
                task.last_heartbeat = datetime.now()
                await task.save(update_fields=['last_heartbeat'])
        except Exception as e:
            log.debug(f"更新任务 {task_id} 心跳失败: {str(e)}")


async def start_periodic_recovery_check():
    """启动定期任务恢复检查（后台运行）"""
    while True:
        try:
            config = await get_task_recovery_config()

            # 检查是否启用定期检查
            if not config['enable_periodic_check']:
                log.info("⏸️ 定期任务恢复检查已禁用，等待重新启用...")
                await asyncio.sleep(300)  # 5分钟后重新检查配置
                continue

            await asyncio.sleep(config['check_interval'])
            log.info("⏰ 开始定期任务恢复检查...")
            await TaskRecoveryService.recover_orphaned_tasks()
        except Exception as e:
            log.error(f"❌ 定期任务恢复检查时发生错误: {str(e)}")
            await asyncio.sleep(300)  # 出错后等待5分钟再重试


async def setup_task_recovery():
    """设置任务恢复服务，应在应用启动时调用"""
    log.info("🚀 正在设置任务恢复服务...")

    try:
        # 立即执行一次任务修复
        recovery_stats = await TaskRecoveryService.recover_orphaned_tasks()

        # 获取配置并启动定期检查（在后台运行）
        config = await get_task_recovery_config()
        asyncio.create_task(start_periodic_recovery_check())

        if config['enable_periodic_check']:
            log.info(f"✅ 任务恢复服务已设置完成（定期检查间隔: {config['check_interval']}秒）")
        else:
            log.info("✅ 任务恢复服务已设置完成（定期检查已禁用，可在系统设置中启用）")

        return recovery_stats

    except Exception as e:
        log.error(f"❌ 设置任务恢复服务时发生错误: {str(e)}")
        raise
