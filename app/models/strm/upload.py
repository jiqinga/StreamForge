import enum
from tortoise import fields
from app.models.system.utils import BaseModel, TimestampMixin
from app.models.system import User


class UploadStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class UploadRecord(BaseModel, TimestampMixin):
    """文件上传记录"""
    id = fields.IntField(pk=True, description="记录ID")
    filename = fields.CharField(max_length=255, description="原始文件名")
    file_path = fields.CharField(max_length=1000, null=True, description="服务器存储路径（旧版本兼容）")
    filesize = fields.BigIntField(description="文件大小（字节）")
    file_content = fields.BinaryField(description="文件内容", null=True)
    uploader = fields.ForeignKeyField("app_system.User", related_name="upload_records", description="上传者")
    status = fields.CharEnumField(UploadStatus, default=UploadStatus.UPLOADED, description="记录状态")
    parsed_result = fields.JSONField(null=True, description="解析结果缓存")
    parse_time = fields.DatetimeField(null=True, description="解析完成时间")

    class Meta:
        table = "strm_upload_records"
        table_description = "文件上传记录表"
        default_connection = "conn_system"


__all__ = ["UploadRecord", "UploadStatus"] 