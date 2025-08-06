"""
系统设置控制器，用于管理系统范围的设置
"""

from typing import Dict, Any, Optional, List, Set, Tuple
from collections import defaultdict
import os
from pathlib import Path

from app.models.strm import SystemSettings, MediaServer, FileType
from app.settings import APP_SETTINGS
from app.core.crud import CRUDBase
from app.core.ctx import CTX_USER_ID
from app.core.exceptions import HTTPException
from app.log.log import (
    set_sql_logging_enabled,
    set_log_level,
    reconfigure_global_logger,
    reconfigure_global_logger_async,
    logger
)


class SystemSettingsController(CRUDBase):
    """系统设置控制器"""

    def _validate_logs_directory(self, logs_directory: str) -> None:
        """验证日志目录路径的有效性"""
        if not logs_directory or not logs_directory.strip():
            return  # 空值是允许的，会使用默认配置

        logs_dir = Path(logs_directory.strip())

        # 如果是相对路径，相对于项目根目录
        if not logs_dir.is_absolute():
            logs_dir = APP_SETTINGS.BASE_DIR / logs_dir

        try:
            # 尝试创建目录
            logs_dir.mkdir(parents=True, exist_ok=True)

            # 检查是否有写入权限
            test_file = logs_dir / "test_write_permission.tmp"
            test_file.write_text("test")
            test_file.unlink()  # 删除测试文件

        except PermissionError:
            raise HTTPException(status_code=400, detail=f"没有权限在目录 '{logs_dir}' 中创建或写入文件")
        except OSError as e:
            raise HTTPException(status_code=400, detail=f"无效的日志目录路径 '{logs_directory}': {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"日志目录验证失败: {str(e)}")

    async def init_sql_logging(self):
        """初始化SQL日志设置（保持向后兼容）"""
        await self.init_all_logging_settings()

    async def init_all_logging_settings(self):
        """初始化所有日志设置"""
        try:
            settings = await SystemSettings.all().first()
            if settings:
                # 初始化SQL日志设置
                if hasattr(settings, 'enable_sql_logging'):
                    set_sql_logging_enabled(settings.enable_sql_logging)
                else:
                    set_sql_logging_enabled(False)

                # 初始化日志级别设置
                if hasattr(settings, 'log_level'):
                    set_log_level(settings.log_level)
                else:
                    set_log_level("INFO")  # 默认INFO级别

                # 重新配置日志记录器以应用新设置
                reconfigure_global_logger()

            else:
                # 如果没有设置记录，使用默认值
                set_sql_logging_enabled(False)
                set_log_level("INFO")
                reconfigure_global_logger()

        except Exception as e:
            # 如果出现任何错误，使用默认设置
            set_sql_logging_enabled(False)
            set_log_level("INFO")
            reconfigure_global_logger()
            print(f"初始化日志设置时出错: {e}")

    async def get_settings(self) -> Optional[Dict[str, Any]]:
        """
        获取系统设置

        如果不存在设置记录，返回None

        Returns:
            系统设置字典或None
        """
        # 获取第一条系统设置记录，通常只会有一条
        settings = await SystemSettings.all().first()
        if not settings:
            return None

        # 获取默认下载服务器信息
        default_download_server = None
        if settings.default_download_server_id:
            server = await MediaServer.filter(id=settings.default_download_server_id).first()
            if server:
                default_download_server = {
                    "id": server.id,
                    "name": server.name,
                    "server_type": server.server_type,
                    "base_url": server.base_url,
                    "description": server.description,
                }

        # 获取默认媒体服务器信息
        default_media_server = None
        if settings.default_media_server_id:
            server = await MediaServer.filter(id=settings.default_media_server_id).first()
            if server:
                default_media_server = {
                    "id": server.id,
                    "name": server.name,
                    "server_type": server.server_type,
                    "base_url": server.base_url,
                    "description": server.description,
                }

        return {
            "id": settings.id,
            "default_download_server_id": settings.default_download_server_id,
            "default_download_server": default_download_server,
            "default_media_server_id": settings.default_media_server_id,
            "default_media_server": default_media_server,
            "enable_path_replacement": settings.enable_path_replacement,
            "replacement_path": settings.replacement_path,
            "download_threads": settings.download_threads,
            "output_directory": settings.output_directory,
            "video_file_types": settings.video_file_types,
            "audio_file_types": settings.audio_file_types,
            "image_file_types": settings.image_file_types,
            "subtitle_file_types": settings.subtitle_file_types,
            "metadata_file_types": settings.metadata_file_types,
            # 任务恢复配置
            "enable_task_recovery_periodic_check": settings.enable_task_recovery_periodic_check,
            "task_recovery_check_interval": settings.task_recovery_check_interval,
            "task_timeout_hours": settings.task_timeout_hours,
            "heartbeat_timeout_minutes": settings.heartbeat_timeout_minutes,
            "activity_check_minutes": settings.activity_check_minutes,
            "recent_activity_minutes": settings.recent_activity_minutes,
            # 重试配置
            "failure_retry_count": settings.failure_retry_count,
            "retry_interval_seconds": settings.retry_interval_seconds,
            # 日志配置
            "enable_sql_logging": settings.enable_sql_logging,
            "log_level": settings.log_level,
            "logs_directory": settings.logs_directory,
            "log_retention_days": getattr(settings, 'log_retention_days', 30),
            "update_time": settings.update_time,
            "settings_version": settings.settings_version,
        }

    def _validate_file_extensions(self, data: Dict[str, Any]) -> None:
        """
        验证文件扩展名是否有重复

        检查所有文件类型中的扩展名，确保每个扩展名只在一种文件类型中出现
        以及确保同一类型内没有重复的扩展名

        Args:
            data: 包含文件类型字段的系统设置数据

        Raises:
            HTTPException: 当发现不同文件类型中有重复扩展名或同一类型内有重复扩展名时抛出异常
        """
        # 定义文件类型字段映射关系
        file_type_fields = {
            FileType.VIDEO: "video_file_types",
            FileType.AUDIO: "audio_file_types",
            FileType.IMAGE: "image_file_types",
            FileType.SUBTITLE: "subtitle_file_types",
            FileType.METADATA: "metadata_file_types",
        }

        # 映射用于显示中文名称
        file_type_names = {
            FileType.VIDEO: "视频",
            FileType.AUDIO: "音频",
            FileType.IMAGE: "图片",
            FileType.SUBTITLE: "字幕",
            FileType.METADATA: "元数据",
        }

        # 记录每个类型内部的扩展名，用于检查同一类型内的重复
        type_extensions: Dict[str, Set[str]] = {}
        # 记录同一类型内的重复扩展名
        internal_duplicates: List[Tuple[str, str]] = []

        # 存储所有扩展名及其所属类型，用于检查跨类型的重复
        extension_to_type: Dict[str, str] = {}
        # 记录跨类型重复的扩展名
        cross_type_duplicates: List[Tuple[str, str, str]] = []

        # 遍历所有文件类型字段
        for file_type, field_name in file_type_fields.items():
            if field_name not in data or not data[field_name]:
                continue

            # 为该类型初始化扩展名集合
            if file_type not in type_extensions:
                type_extensions[file_type] = set()

            # 解析扩展名，使用逗号分隔
            extensions = [ext.strip() for ext in data[field_name].split(",") if ext.strip()]

            for ext in extensions:
                # 确保扩展名格式正确（以点开头）
                if not ext.startswith("."):
                    ext = f".{ext}"

                # 转为小写用于比较
                ext_lower = ext.lower()

                # 检查同一类型内是否有重复
                if ext_lower in type_extensions[file_type]:
                    internal_duplicates.append((ext, file_type_names[file_type]))
                else:
                    type_extensions[file_type].add(ext_lower)

                # 检查是否在不同类型间有重复
                if ext_lower in extension_to_type:
                    existing_type = extension_to_type[ext_lower]
                    if existing_type != file_type:  # 只有不同类型间的重复才记录
                        cross_type_duplicates.append((ext, file_type_names[existing_type], file_type_names[file_type]))
                else:
                    extension_to_type[ext_lower] = file_type

        # 处理错误情况
        error_messages = []

        # 处理同一类型内的重复
        if internal_duplicates:
            internal_duplicate_details = []
            for ext, type_name in internal_duplicates:
                internal_duplicate_details.append(f"扩展名 {ext} 在 {type_name} 类型中重复")

            error_messages.append(
                "文件类型设置有误：同一类型内不能有重复的文件后缀。\n" + "\n".join(internal_duplicate_details)
            )

        # 处理跨类型的重复
        if cross_type_duplicates:
            cross_duplicate_details = []
            for ext, type1, type2 in cross_type_duplicates:
                cross_duplicate_details.append(f"扩展名 {ext} 在 {type1} 和 {type2} 类型中均存在")

            error_messages.append(
                "文件类型设置有误：同一个文件后缀不能属于不同的文件类型。\n" + "\n".join(cross_duplicate_details)
            )

        # 如果有任何错误，抛出异常
        if error_messages:
            raise HTTPException(code=400, msg="\n\n".join(error_messages))

    async def create_or_update_settings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建或更新系统设置

        如果不存在设置记录，创建新记录；如果存在，则更新现有记录

        Args:
            data: 系统设置数据

        Returns:
            更新后的系统设置字典
        """
        # 获取当前用户ID
        user_id = CTX_USER_ID.get()

        # 移除可能存在的default_server_id字段
        if "default_server_id" in data:
            data.pop("default_server_id")

        # 检查各种服务器ID是否存在
        server_id_fields = ["default_download_server_id", "default_media_server_id"]

        for field in server_id_fields:
            if data.get(field):
                server = await MediaServer.filter(id=data[field]).first()
                if not server:
                    raise HTTPException(code=404, msg=f"指定的服务器ID不存在: {data[field]}")

        # 验证文件类型扩展名是否有重复
        self._validate_file_extensions(data)

        # 验证日志目录路径
        if 'logs_directory' in data:
            self._validate_logs_directory(data['logs_directory'])

        # 查找现有设置
        settings = await SystemSettings.all().first()

        # 记录更改前的设置值（用于日志记录）
        old_values = {}
        if settings:
            for field in data.keys():
                if hasattr(settings, field):
                    old_values[field] = getattr(settings, field)

        # 检查是否需要更新版本号（当文件类型相关设置发生变化时）
        file_type_fields = [
            "video_file_types",
            "audio_file_types",
            "image_file_types",
            "subtitle_file_types",
            "metadata_file_types",
        ]

        need_version_update = False

        if settings:
            # 检查文件类型相关设置是否有变化
            for field in file_type_fields:
                if field in data and getattr(settings, field) != data[field]:
                    need_version_update = True
                    break

            # 更新现有设置
            for field, value in data.items():
                # 确认模型中有该字段才进行设置
                if hasattr(settings, field):
                    setattr(settings, field, value)

            # 如果需要更新版本号，则递增版本号
            if need_version_update:
                settings.settings_version = settings.settings_version + 1
                # print(f"文件类型设置已变更，增加设置版本号至: {settings.settings_version}")

            settings.updated_by_id = user_id
            await settings.save()

            # 记录设置更新日志
            self._log_settings_changes(old_values, data, is_create=False)
        else:
            # 确保只包含模型中存在的字段进行创建
            valid_data = {}
            model_instance = SystemSettings()
            for field, value in data.items():
                if hasattr(model_instance, field):
                    valid_data[field] = value

            # 创建新设置，初始版本号为1
            settings = await SystemSettings.create(**valid_data, settings_version=1, updated_by_id=user_id)
            logger.info(f"🆕 创建新的系统设置，初始设置版本号: 1")

            # 记录设置创建日志
            self._log_settings_changes({}, valid_data, is_create=True)

        # 如果更新了日志设置，立即应用
        logs_config_changed = False

        if 'enable_sql_logging' in data:
            set_sql_logging_enabled(data['enable_sql_logging'])
            # 只有当SQL日志设置真的发生变化时才标记为需要重新配置
            if old_values.get('enable_sql_logging') != data['enable_sql_logging']:
                logs_config_changed = True

        if 'log_level' in data:
            set_log_level(data['log_level'])
            # 只有当日志级别真的发生变化时才标记为需要重新配置
            if old_values.get('log_level') != data['log_level']:
                logs_config_changed = True

        if 'logs_directory' in data:
            # 只有当日志目录真的发生变化时才标记为需要重新配置
            if old_values.get('logs_directory') != data['logs_directory']:
                logs_config_changed = True

        if 'log_retention_days' in data:
            # 只有当日志保留天数真的发生变化时才标记为需要重新配置
            if old_values.get('log_retention_days') != data['log_retention_days']:
                logs_config_changed = True

        # 如果日志配置发生变化，重新配置日志记录器
        if logs_config_changed:
            await reconfigure_global_logger_async()

        # 获取更新后的设置
        return await self.get_settings()

    def _log_settings_changes(self, old_values: Dict[str, Any], new_values: Dict[str, Any], is_create: bool = False):
        """
        记录系统设置更改日志

        Args:
            old_values: 更改前的值
            new_values: 更改后的值
            is_create: 是否为创建操作
        """
        if is_create:
            logger.info("🔧 系统设置已创建")
            for field, value in new_values.items():
                field_name = self._get_field_display_name(field)
                logger.info(f"  ✅ {field_name}: {self._format_value_for_log(value)}")
        else:
            changed_fields = []
            for field, new_value in new_values.items():
                old_value = old_values.get(field)
                if old_value != new_value:
                    changed_fields.append((field, old_value, new_value))

            if changed_fields:
                logger.info("🔧 系统设置已更新")
                for field, old_value, new_value in changed_fields:
                    field_name = self._get_field_display_name(field)
                    old_display = self._format_value_for_log(old_value)
                    new_display = self._format_value_for_log(new_value)
                    logger.info(f"  🔄 {field_name}: {old_display} → {new_display}")

    def _get_field_display_name(self, field: str) -> str:
        """
        获取字段的显示名称

        Args:
            field: 字段名

        Returns:
            字段的中文显示名称
        """
        field_names = {
            "default_download_server_id": "默认下载服务器",
            "default_media_server_id": "默认媒体服务器",
            "enable_path_replacement": "启用路径替换",
            "replacement_path": "替换路径",
            "download_threads": "下载线程数",
            "output_directory": "输出目录",
            "video_file_types": "视频文件类型",
            "audio_file_types": "音频文件类型",
            "image_file_types": "图片文件类型",
            "subtitle_file_types": "字幕文件类型",
            "metadata_file_types": "元数据文件类型",
            "enable_task_recovery_periodic_check": "启用任务恢复定期检查",
            "task_recovery_check_interval": "任务恢复检查间隔",
            "task_timeout_hours": "任务超时时间(小时)",
            "heartbeat_timeout_minutes": "心跳超时时间(分钟)",
            "activity_check_minutes": "活动检查间隔(分钟)",
            "recent_activity_minutes": "最近活动时间(分钟)",
            "failure_retry_count": "失败重试次数",
            "retry_interval_seconds": "重试间隔(秒)",
            "enable_sql_logging": "启用SQL日志",
            "log_level": "日志级别",
            "logs_directory": "日志目录",
            "log_retention_days": "日志保留天数",
        }
        return field_names.get(field, field)

    def _format_value_for_log(self, value: Any) -> str:
        """
        格式化值用于日志显示

        Args:
            value: 要格式化的值

        Returns:
            格式化后的字符串
        """
        if value is None:
            return "未设置"
        elif isinstance(value, bool):
            return "启用" if value else "禁用"
        elif isinstance(value, str) and len(value) > 50:
            return f"{value[:47]}..."
        else:
            return str(value)


system_settings_controller = SystemSettingsController(SystemSettings)
