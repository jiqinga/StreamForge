from typing import Optional, List, Any, Dict, Set, Tuple
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, validator

from app.models.strm import ServerType, TaskStatus, FileType, ServerStatus, ProcessType
from app.schemas.form import as_form
from app.schemas.base import PageData


# 添加PageInfo类，用于分页信息
class PageInfo(BaseModel):
    """分页信息模型"""

    current: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    total: int = Field(..., description="总记录数")


class TaskTypeEnum(str, Enum):
    STRM_GENERATION = "strm_generation"
    RESOURCE_DOWNLOAD = "resource_download"


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class MediaServerBase(BaseModel):
    """媒体服务器基础模型"""

    name: str = Field(..., description="服务器名称")
    server_type: ServerType = Field(default=ServerType.HTTP, description="服务器类型")
    base_url: str = Field(..., description="服务器基础URL")
    description: Optional[str] = Field(default=None, description="服务器描述")
    auth_required: bool = Field(default=False, description="是否需要认证")
    username: Optional[str] = Field(default=None, description="认证用户名")
    password: Optional[str] = Field(default=None, description="认证密码")
    status: Optional[ServerStatus] = Field(default=ServerStatus.UNKNOWN, description="服务器连接状态")

    class Config:
        from_attributes = True


class MediaServerCreate(MediaServerBase):
    """创建媒体服务器模型"""

    pass


class MediaServerUpdate(BaseModel):
    """更新媒体服务器模型"""

    name: Optional[str] = Field(default=None, description="服务器名称")
    server_type: Optional[ServerType] = Field(default=None, description="服务器类型")
    base_url: Optional[str] = Field(default=None, description="服务器基础URL")
    description: Optional[str] = Field(default=None, description="服务器描述")
    auth_required: Optional[bool] = Field(default=None, description="是否需要认证")
    username: Optional[str] = Field(default=None, description="认证用户名")
    password: Optional[str] = Field(default=None, description="认证密码")
    status: Optional[ServerStatus] = Field(default=None, description="服务器连接状态")


class MediaServerResponse(MediaServerBase):
    """媒体服务器响应模型"""

    id: int = Field(..., description="服务器ID")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class PathMappingBase(BaseModel):
    """路径映射规则基础模型"""

    name: str = Field(..., description="规则名称")
    source_path: str = Field(..., description="源路径")
    target_path: str = Field(..., description="目标路径")
    server_id: int = Field(..., description="所属服务器ID")
    is_regex: bool = Field(default=False, description="是否使用正则表达式")

    class Config:
        from_attributes = True


class PathMappingCreate(PathMappingBase):
    """创建路径映射规则模型"""

    pass


class PathMappingUpdate(BaseModel):
    """更新路径映射规则模型"""

    name: Optional[str] = Field(default=None, description="规则名称")
    source_path: Optional[str] = Field(default=None, description="源路径")
    target_path: Optional[str] = Field(default=None, description="目标路径")
    server_id: Optional[int] = Field(default=None, description="所属服务器ID")
    is_regex: Optional[bool] = Field(default=None, description="是否使用正则表达式")


class PathMappingResponse(PathMappingBase):
    """路径映射规则响应模型"""

    id: int = Field(..., description="映射规则ID")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class FilterRuleBase(BaseModel):
    """文件过滤规则基础模型"""

    name: str = Field(..., description="规则名称")
    file_type: Optional[FileType] = Field(default=None, description="文件类型")
    keyword: Optional[str] = Field(default=None, description="关键词")
    path_pattern: Optional[str] = Field(default=None, description="路径模式")
    is_include: bool = Field(default=True, description="是包含规则还是排除规则")

    class Config:
        from_attributes = True


class FilterRuleCreate(FilterRuleBase):
    """创建文件过滤规则模型"""

    pass


class FilterRuleUpdate(BaseModel):
    """更新文件过滤规则模型"""

    name: Optional[str] = Field(default=None, description="规则名称")
    file_type: Optional[FileType] = Field(default=None, description="文件类型")
    keyword: Optional[str] = Field(default=None, description="关键词")
    path_pattern: Optional[str] = Field(default=None, description="路径模式")
    is_include: Optional[bool] = Field(default=None, description="是包含规则还是排除规则")


class FilterRuleResponse(FilterRuleBase):
    """文件过滤规则响应模型"""

    id: int = Field(..., description="过滤规则ID")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class UploadResult(BaseModel):
    """上传结果模型"""

    filename: str  # 文件名
    path: str  # 存储路径
    record_id: int  # 上传记录ID


class ParseRequest(BaseModel):
    """文件解析请求"""

    record_id: int = Field(..., description="上传记录ID")
    save_result: bool = Field(default=True, description="是否保存解析结果")


class DirectoryRequest(BaseModel):
    """获取目录内容请求"""

    record_id: int = Field(..., description="上传记录ID")
    path: str = Field(default="", description="目录路径")


class SearchRequest(BaseModel):
    """搜索文件请求"""

    record_id: int = Field(..., description="上传记录ID")
    keyword: str = Field(..., description="搜索关键词")
    filter_type: str = Field(default="all", description="筛选类型")


class UploadHistoryResponse(BaseModel):
    """上传历史记录响应"""

    code: int = Field(..., description="状态码")
    msg: str = Field(..., description="消息")
    data: List[Dict[str, Any]] = Field(..., description="数据")
    page_info: PageInfo = Field(..., description="分页信息")


class StrmTaskCreate(BaseModel):
    """创建STRM任务的请求模型"""

    record_id: int = Field(..., description="上传记录ID")
    server_id: int = Field(..., description="媒体服务器ID")
    name: Optional[str] = Field(None, description="任务名称")
    output_dir: Optional[str] = Field(None, description="自定义输出目录")
    download_server_id: Optional[int] = Field(None, description="下载服务器ID")
    threads: int = Field(1, description="下载线程数", ge=1, le=20)


class StrmFileDetail(BaseModel):
    """STRM文件详情模型"""

    id: int = Field(..., description="文件ID")
    source_path: str = Field(..., description="源文件路径")
    target_path: str = Field(..., description="生成的STRM文件路径")
    file_type: str = Field(..., description="文件类型")
    file_size: Optional[int] = Field(default=None, description="文件大小(字节)")
    is_success: bool = Field(..., description="是否生成成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class StrmTaskDetail(BaseModel):
    """STRM任务详情模型"""

    id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    total_files: int = Field(..., description="总文件数")
    processed_files: int = Field(..., description="已处理文件数")
    success_files: int = Field(..., description="成功生成文件数")
    failed_files: int = Field(..., description="失败文件数")
    progress: int = Field(..., description="进度百分比")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    end_time: Optional[str] = Field(default=None, description="结束时间")
    output_dir: str = Field(..., description="输出目录")
    files: List[StrmFileDetail] = Field(default_factory=list, description="文件列表（最多10条）")
    file_count: int = Field(..., description="文件总数")


class StrmTaskBrief(BaseModel):
    """STRM任务简要信息模型"""

    id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    total_files: int = Field(..., description="总文件数")
    processed_files: int = Field(..., description="已处理文件数")
    success_files: int = Field(..., description="成功生成文件数")
    failed_files: int = Field(..., description="失败文件数")
    progress: int = Field(..., description="进度百分比")
    start_time: Optional[str] = Field(default=None, description="开始时间")
    end_time: Optional[str] = Field(default=None, description="结束时间")


class StrmTaskResponse(BaseModel):
    """STRM任务响应模型"""

    id: int
    name: str
    status: str
    server_id: int
    server_name: Optional[str] = None
    source_file: str
    output_dir: str
    total_files: int
    processed_files: int
    success_files: int
    failed_files: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    create_time: Optional[str] = None
    download_server_id: Optional[int] = None
    download_server_name: Optional[str] = None
    threads: int = 1

    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建响应模型"""
        return cls(
            id=obj.id,
            name=obj.name,
            status=obj.status,
            server_id=obj.server_id,
            server_name=obj.server.name if hasattr(obj, "server") and obj.server else None,
            source_file=obj.source_file,
            output_dir=obj.output_dir,
            total_files=obj.total_files,
            processed_files=obj.processed_files,
            success_files=obj.success_files,
            failed_files=obj.failed_files,
            start_time=obj.start_time.isoformat() if obj.start_time else None,
            end_time=obj.end_time.isoformat() if obj.end_time else None,
            create_time=obj.create_time.isoformat() if obj.create_time else None,
            download_server_id=obj.download_server_id if hasattr(obj, "download_server_id") else None,
            download_server_name=obj.download_server.name
            if hasattr(obj, "download_server") and obj.download_server
            else None,
            threads=obj.threads if hasattr(obj, "threads") else 1,
        )


class StrmGenerateResult(BaseModel):
    """STRM生成结果模型"""

    task_id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    result: Dict[str, Any] = Field(..., description="处理结果")


class StrmGenerateResponse(BaseModel):
    """STRM生成结果模型"""

    task_id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    result: Dict[str, Any] = Field(..., description="处理结果")


class SystemSettingsBase(BaseModel):
    """系统设置基础模型"""

    default_server_id: Optional[int] = Field(default=None, description="默认服务器ID（旧版本兼容）")
    default_download_server_id: Optional[int] = Field(default=None, description="默认下载服务器ID")
    default_media_server_id: Optional[int] = Field(default=None, description="默认媒体服务器ID")
    enable_path_replacement: bool = Field(default=True, description="启用路径替换")
    replacement_path: Optional[str] = Field(default="/nas", description="路径替换值")
    download_threads: int = Field(default=1, description="默认下载线程数")
    output_directory: Optional[str] = Field(default=None, description="默认输出目录")
    video_file_types: Optional[str] = Field(default=None, description="视频文件类型")
    audio_file_types: Optional[str] = Field(default=None, description="音频文件类型")
    image_file_types: Optional[str] = Field(default=None, description="图片文件类型")
    subtitle_file_types: Optional[str] = Field(default=None, description="字幕文件类型")
    metadata_file_types: Optional[str] = Field(default=None, description="元数据文件类型")

    # 任务恢复配置
    enable_task_recovery_periodic_check: bool = Field(default=True, description="启用任务恢复定期检查")
    task_recovery_check_interval: int = Field(default=1800, description="任务恢复检查间隔（秒）")
    task_timeout_hours: int = Field(default=2, description="任务超时时间（小时）")
    heartbeat_timeout_minutes: int = Field(default=10, description="心跳超时时间（分钟）")
    activity_check_minutes: int = Field(default=30, description="活动检测时间窗口（分钟）")
    recent_activity_minutes: int = Field(default=5, description="最近活动检查窗口（分钟）")

    # 重试配置
    failure_retry_count: int = Field(default=3, description="失败重试次数")
    retry_interval_seconds: int = Field(default=30, description="重试间隔时间（秒）")

    # 日志配置
    enable_sql_logging: bool = Field(default=False, description="启用SQL日志打印")
    log_level: str = Field(default="INFO", description="日志级别")
    logs_directory: Optional[str] = Field(default=None, description="日志存放目录")
    log_retention_days: int = Field(default=30, description="日志保留天数")

    class Config:
        from_attributes = True


class SystemSettingsUpdate(BaseModel):
    """系统设置更新模型"""

    default_server_id: Optional[int] = Field(default=None, description="默认服务器ID（旧版本兼容）")
    default_download_server_id: Optional[int] = Field(default=None, description="默认下载服务器ID")
    default_media_server_id: Optional[int] = Field(default=None, description="默认媒体服务器ID")
    enable_path_replacement: Optional[bool] = Field(default=None, description="启用路径替换")
    replacement_path: Optional[str] = Field(default=None, description="路径替换值")
    download_threads: Optional[int] = Field(default=None, description="默认下载线程数")
    output_directory: Optional[str] = Field(default=None, description="默认输出目录")
    video_file_types: Optional[str] = Field(default=None, description="视频文件类型")
    audio_file_types: Optional[str] = Field(default=None, description="音频文件类型")
    image_file_types: Optional[str] = Field(default=None, description="图片文件类型")
    subtitle_file_types: Optional[str] = Field(default=None, description="字幕文件类型")
    metadata_file_types: Optional[str] = Field(default=None, description="元数据文件类型")

    # 任务恢复配置
    enable_task_recovery_periodic_check: Optional[bool] = Field(default=None, description="启用任务恢复定期检查")
    task_recovery_check_interval: Optional[int] = Field(default=None, description="任务恢复检查间隔（秒）")
    task_timeout_hours: Optional[int] = Field(default=None, description="任务超时时间（小时）")
    heartbeat_timeout_minutes: Optional[int] = Field(default=None, description="心跳超时时间（分钟）")
    activity_check_minutes: Optional[int] = Field(default=None, description="活动检测时间窗口（分钟）")
    recent_activity_minutes: Optional[int] = Field(default=None, description="最近活动检查窗口（分钟）")

    # 重试配置
    failure_retry_count: Optional[int] = Field(default=None, description="失败重试次数")
    retry_interval_seconds: Optional[int] = Field(default=None, description="重试间隔时间（秒）")

    # 日志配置
    enable_sql_logging: Optional[bool] = Field(default=None, description="启用SQL日志打印")
    log_level: Optional[str] = Field(default=None, description="日志级别")
    logs_directory: Optional[str] = Field(default=None, description="日志存放目录")
    log_retention_days: Optional[int] = Field(default=None, description="日志保留天数")


class SystemSettingsResponse(SystemSettingsBase):
    """系统设置响应模型"""

    id: int = Field(..., description="设置ID")
    default_server: Optional[MediaServerResponse] = Field(default=None, description="默认服务器详情（旧版本兼容）")
    default_download_server: Optional[MediaServerResponse] = Field(default=None, description="默认下载服务器详情")
    default_media_server: Optional[MediaServerResponse] = Field(default=None, description="默认媒体服务器详情")
    update_time: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class DirectoryResponse(BaseModel):
    path: str = Field(..., description="目录路径")
    files: List[Dict] = Field(..., description="文件列表")
    directories: List[Dict] = Field(..., description="子目录列表")
    total: int = Field(..., description="总条目数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页大小")


class UrlUploadRequest(BaseModel):
    """URL上传请求模型"""

    url: str = Field(..., description="文件URL地址")

    @validator("url")
    def validate_url(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("无效的URL")
        # 添加基本的URL格式验证
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL必须以http://或https://开头")
        return v


class UploadHistoryItem(BaseModel):
    id: int = Field(..., description="记录ID")
    filename: str = Field(..., description="文件名")
    filesize: int = Field(..., description="文件大小（字节）")
    status: str = Field(..., description="状态")
    create_time: str = Field(..., description="创建时间")
    uploader_id: int = Field(..., description="上传者ID")
    parse_time: Optional[str] = Field(None, description="解析时间")


class ResourceDownloadTaskDetail(BaseModel):
    id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    task_type: str = Field(..., description="任务类型")
    strm_task_id: Optional[int] = Field(None, description="关联的STRM任务ID")
    server: Dict[str, Any] = Field(..., description="下载服务器信息")
    source_file: str = Field(..., description="源文件路径")
    output_dir: str = Field(..., description="输出目录")
    total_files: int = Field(..., description="总文件数")
    processed_files: int = Field(..., description="已处理文件数")
    success_files: int = Field(..., description="成功下载文件数")
    failed_files: int = Field(..., description="失败文件数")
    progress: int = Field(..., description="进度百分比")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    elapsed_time: Optional[str] = Field(None, description="已用时间")
    created_by: Dict[str, Any] = Field(..., description="创建者")
    create_time: str = Field(..., description="创建时间")
    error: Optional[str] = Field(None, description="错误信息")
    file_types: Optional[str] = Field(None, description="下载文件类型")
    threads: int = Field(1, description="下载线程数")


class ResourceDownloadTaskBrief(BaseModel):
    id: int = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    task_type: str = Field(..., description="任务类型")
    strm_task_id: Optional[int] = Field(None, description="关联的STRM任务ID")
    total_files: int = Field(..., description="总文件数")
    processed_files: int = Field(..., description="已处理文件数")
    success_files: int = Field(..., description="成功下载文件数")
    progress: int = Field(..., description="进度百分比")
    create_time: str = Field(..., description="创建时间")
    file_types: Optional[str] = Field(None, description="下载文件类型")


class ResourceDownloadTaskResponse(BaseModel):
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    tasks: List[ResourceDownloadTaskBrief] = Field(..., description="任务列表")


__all__ = [
    "MediaServerCreate",
    "MediaServerUpdate",
    "MediaServerResponse",
    "PathMappingCreate",
    "PathMappingUpdate",
    "PathMappingResponse",
    "FilterRuleCreate",
    "FilterRuleUpdate",
    "FilterRuleResponse",
    "ParseRequest",
    "DirectoryRequest",
    "SearchRequest",
    "UploadHistoryResponse",
    "UploadResult",
    "StrmTaskCreate",
    "StrmTaskResponse",
    "StrmTaskDetail",
    "StrmTaskBrief",
    "StrmFileDetail",
    "StrmGenerateResult",
    "StrmGenerateResponse",
    "SystemSettingsBase",
    "SystemSettingsUpdate",
    "SystemSettingsResponse",
    "DirectoryResponse",
    "UploadHistoryItem",
    "ResourceDownloadTaskDetail",
    "ResourceDownloadTaskBrief",
    "ResourceDownloadTaskResponse",
    "TaskStatusEnum",
    "TaskTypeEnum",
    "UrlUploadRequest",
]
