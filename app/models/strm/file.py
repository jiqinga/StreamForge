from tortoise import fields

from app.models.system.utils import BaseModel, TimestampMixin
from .models import FileType


class StrmFile(BaseModel, TimestampMixin):
    """生成的STRM文件记录"""
    id = fields.IntField(pk=True, description="文件ID")
    task = fields.ForeignKeyField("app_system.StrmTask", related_name="strm_files", description="所属任务")
    source_path = fields.CharField(max_length=1000, description="源文件路径")
    target_path = fields.CharField(max_length=1000, description="生成的STRM文件路径")
    file_type = fields.CharEnumField(FileType, description="文件类型")
    file_size = fields.BigIntField(null=True, description="文件大小(字节)")
    is_success = fields.BooleanField(default=True, description="是否生成成功")
    error_message = fields.TextField(null=True, description="错误信息")
    
    class Meta:
        table = "strm_files"
        table_description = "STRM文件记录表"
        default_connection = "conn_system"


__all__ = ["StrmFile"] 