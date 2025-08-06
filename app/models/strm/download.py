from tortoise import fields
from datetime import datetime
from app.models.system.utils import BaseModel, TimestampMixin, StrEnum
from .models import TaskStatus, ProcessType, FileType


class DownloadTaskStatus(StrEnum):
    PENDING = "pending"  # 等待下载
    DOWNLOADING = "downloading"  # 正在下载
    COMPLETED = "completed"  # 下载完成
    FAILED = "failed"  # 下载失败
    CANCELED = "canceled"  # 已取消
    RETRY = "retry"  # 等待重试


class DownloadTask(BaseModel, TimestampMixin):
    """下载任务记录"""

    id = fields.IntField(pk=True, description="任务ID")
    task = fields.ForeignKeyField("app_system.StrmTask", related_name="download_tasks", description="所属STRM任务")
    source_path = fields.CharField(max_length=1000, description="源文件路径")
    target_path = fields.CharField(max_length=1000, null=True, description="目标文件路径")
    file_type = fields.CharEnumField(FileType, description="文件类型")
    process_type = fields.CharEnumField(ProcessType, description="处理类型")
    status = fields.CharEnumField(DownloadTaskStatus, default=DownloadTaskStatus.PENDING, description="下载状态")
    priority = fields.IntField(default=0, description="优先级（数字越小优先级越高）")
    attempt_count = fields.IntField(default=0, description="尝试次数")
    max_attempts = fields.IntField(default=3, description="最大尝试次数")
    file_size = fields.BigIntField(null=True, description="文件大小(字节)")
    download_started = fields.DatetimeField(null=True, description="下载开始时间")
    download_completed = fields.DatetimeField(null=True, description="下载完成时间")
    download_duration = fields.FloatField(null=True, description="下载耗时(秒)")
    download_speed = fields.FloatField(null=True, description="下载速度(字节/秒)")
    worker_id = fields.CharField(max_length=100, null=True, description="处理该任务的工作线程ID")
    error_message = fields.TextField(null=True, description="错误信息")
    retry_after = fields.DatetimeField(null=True, description="重试时间")

    class Meta:
        table = "strm_download_tasks"
        table_description = "下载任务队列表"
        default_connection = "conn_system"
        indexes = [
            # 单字段索引
            ("task_id",),
            ("status",),
            ("process_type",),
            # 复合索引 - 用于优化任务列表查询
            ("task_id", "status"),
            ("task_id", "process_type"),
            ("task_id", "process_type", "status"),
        ]


class DownloadLog(BaseModel, TimestampMixin):
    """下载日志记录"""

    id = fields.IntField(pk=True, description="日志ID")
    task = fields.ForeignKeyField("app_system.StrmTask", related_name="download_logs", description="关联的任务")
    file_path = fields.CharField(max_length=1000, description="文件路径")
    target_path = fields.CharField(max_length=1000, null=True, description="目标路径")
    file_type = fields.CharEnumField(FileType, default=FileType.OTHER, description="文件类型")
    file_size = fields.BigIntField(null=True, description="文件大小（字节）")
    download_time = fields.FloatField(null=True, description="下载耗时（秒）")
    download_speed = fields.FloatField(null=True, description="下载速度（字节/秒）")
    is_success = fields.BooleanField(default=True, description="是否下载成功")
    log_level = fields.CharField(max_length=20, default="INFO", description="日志级别")
    log_message = fields.TextField(description="日志消息")
    error_message = fields.TextField(null=True, description="错误信息")

    class Meta:
        table = "strm_download_logs"
        table_description = "下载日志记录表"
        default_connection = "conn_system"


class StrmLog(BaseModel, TimestampMixin):
    """STRM生成日志记录"""

    id = fields.IntField(pk=True, description="日志ID")
    task = fields.ForeignKeyField("app_system.StrmTask", related_name="strm_logs", description="关联的任务")
    source_path = fields.CharField(max_length=1000, description="源文件路径")
    target_path = fields.CharField(max_length=1000, null=True, description="生成的STRM文件路径")
    file_type = fields.CharEnumField(FileType, default=FileType.VIDEO, description="文件类型")
    is_success = fields.BooleanField(default=True, description="是否生成成功")
    log_level = fields.CharField(max_length=20, default="INFO", description="日志级别")
    log_message = fields.TextField(description="日志消息")
    error_message = fields.TextField(null=True, description="错误信息")
    generation_time = fields.FloatField(null=True, description="生成耗时（秒）")

    class Meta:
        table = "strm_generation_logs"
        table_description = "STRM生成日志记录表"
        default_connection = "conn_system"


__all__ = ["DownloadTask", "DownloadTaskStatus", "DownloadLog", "StrmLog"]
