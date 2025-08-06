from enum import Enum
from tortoise import fields

from app.models.system.utils import BaseModel, TimestampMixin, StrEnum


class ServerType(StrEnum):
    HTTP = "http"
    HTTPS = "https"
    LOCAL = "local"
    FTP = "ftp"
    WEBDAV = "webdav"
    CD2HOST = "cd2host"  # 下载服务器类型
    XIAOYAHOST = "xiaoyahost"  # 媒体服务器类型


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ProcessType(StrEnum):
    """处理类型"""

    STRM_GENERATION = "strm_generation"  # STRM文件生成
    RESOURCE_DOWNLOAD = "resource_download"  # 资源文件下载
    PENDING_WAIT = "pending_wait"  # 未判定类型


class FileType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    SUBTITLE = "subtitle"
    METADATA = "metadata"
    OTHER = "other"


class ServerStatus(StrEnum):
    UNKNOWN = "unknown"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class MediaServer(BaseModel, TimestampMixin):
    """媒体服务器配置"""

    id = fields.IntField(pk=True, description="服务器ID")
    name = fields.CharField(max_length=100, description="服务器名称")
    server_type = fields.CharEnumField(ServerType, default=ServerType.HTTP, description="服务器类型")
    base_url = fields.CharField(max_length=500, description="服务器基础URL")
    description = fields.TextField(null=True, description="服务器描述")
    auth_required = fields.BooleanField(default=False, description="是否需要认证")
    username = fields.CharField(max_length=100, null=True, description="认证用户名")
    password = fields.CharField(max_length=100, null=True, description="认证密码")
    status = fields.CharEnumField(ServerStatus, default=ServerStatus.UNKNOWN, description="服务器连接状态")
    created_by = fields.ForeignKeyField(
        "app_system.User", related_name="created_servers", null=True, description="创建者"
    )

    class Meta:
        table = "strm_media_servers"
        table_description = "媒体服务器配置表"
        default_connection = "conn_system"


class SystemSettings(BaseModel, TimestampMixin):
    """系统设置"""

    id = fields.IntField(pk=True, description="设置ID")
    default_download_server = fields.ForeignKeyField(
        "app_system.MediaServer", related_name="default_download_in_settings", null=True, description="默认下载服务器"
    )
    default_media_server = fields.ForeignKeyField(
        "app_system.MediaServer", related_name="default_media_in_settings", null=True, description="默认媒体服务器"
    )
    enable_path_replacement = fields.BooleanField(default=True, description="启用路径替换")
    replacement_path = fields.CharField(max_length=500, null=True, default="/nas", description="路径替换值")
    download_threads = fields.IntField(default=1, description="默认下载线程数")
    output_directory = fields.CharField(max_length=500, null=True, description="默认输出目录")
    video_file_types = fields.CharField(max_length=500, null=True, description="视频文件类型")
    audio_file_types = fields.CharField(max_length=500, null=True, description="音频文件类型")
    image_file_types = fields.CharField(max_length=500, null=True, description="图片文件类型")
    subtitle_file_types = fields.CharField(max_length=500, null=True, description="字幕文件类型")
    metadata_file_types = fields.CharField(max_length=500, null=True, description="元数据文件类型")

    # 任务恢复配置
    enable_task_recovery_periodic_check = fields.BooleanField(default=True, description="启用任务恢复定期检查")
    task_recovery_check_interval = fields.IntField(default=1800, description="任务恢复检查间隔（秒）")
    task_timeout_hours = fields.IntField(default=2, description="任务超时时间（小时）")
    heartbeat_timeout_minutes = fields.IntField(default=10, description="心跳超时时间（分钟）")
    activity_check_minutes = fields.IntField(default=30, description="活动检测时间窗口（分钟）")
    recent_activity_minutes = fields.IntField(default=5, description="最近活动检查窗口（分钟）")

    # 重试配置
    failure_retry_count = fields.IntField(default=3, description="失败重试次数")
    retry_interval_seconds = fields.IntField(default=30, description="重试间隔时间（秒）")

    # 日志配置
    enable_sql_logging = fields.BooleanField(default=False, description="启用SQL日志打印")
    log_level = fields.CharField(max_length=10, default="INFO", description="日志级别")
    logs_directory = fields.CharField(max_length=500, null=True, description="日志存放目录")
    log_retention_days = fields.IntField(default=30, description="日志保留天数")

    settings_version = fields.IntField(default=1, description="设置版本号，用于缓存控制")
    updated_by = fields.ForeignKeyField(
        "app_system.User", related_name="updated_settings", null=True, description="更新人"
    )

    class Meta:
        table = "strm_system_settings"
        table_description = "系统设置表"
        default_connection = "conn_system"

    def __str__(self):
        return f"系统设置 (版本 {self.settings_version})"


__all__ = [
    "ServerType",
    "TaskStatus",
    "ProcessType",
    "FileType",
    "ServerStatus",
    "MediaServer",
    "SystemSettings",
]
