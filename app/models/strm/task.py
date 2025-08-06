from tortoise import fields
from datetime import datetime
from typing import Optional

from app.models.system.utils import BaseModel, TimestampMixin
from .models import TaskStatus


class StrmTask(BaseModel, TimestampMixin):
    """STRM生成任务"""

    id = fields.IntField(pk=True, description="任务ID")
    name = fields.CharField(max_length=200, description="任务名称")
    status = fields.CharEnumField(TaskStatus, default=TaskStatus.PENDING, description="任务状态")
    server = fields.ForeignKeyField("app_system.MediaServer", related_name="tasks", description="使用的服务器")
    download_server = fields.ForeignKeyField(
        "app_system.MediaServer", related_name="download_tasks", null=True, description="下载服务器"
    )
    source_file = fields.CharField(max_length=500, description="源文件路径")
    output_dir = fields.CharField(max_length=500, description="输出目录")
    total_files = fields.IntField(default=0, description="总文件数")
    processed_files = fields.IntField(default=0, description="已处理文件数")
    success_files = fields.IntField(default=0, description="成功生成文件数")
    failed_files = fields.IntField(default=0, description="失败文件数")
    start_time = fields.DatetimeField(null=True, description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")
    created_by = fields.ForeignKeyField("app_system.User", related_name="created_tasks", description="创建者")
    log_file = fields.CharField(max_length=500, null=True, description="日志文件路径或额外信息")
    log_content = fields.TextField(null=True, description="日志内容文本")
    download_duration = fields.FloatField(null=True, description="处理耗时(秒)")
    threads = fields.IntField(default=1, description="下载线程数")

    class Meta:
        table = "strm_tasks"
        table_description = "STRM生成任务表"
        default_connection = "conn_system"
        indexes = [
            # 单字段索引
            ("created_by_id",),
            ("status",),
            ("create_time",),
            ("name",),
            # 复合索引 - 用于优化任务列表查询
            ("created_by_id", "status"),
            ("created_by_id", "create_time"),
        ]

    def _add_emoji_to_message(self, message: str, level: str) -> str:
        """
        为日志消息添加合适的emoji

        Args:
            message: 原始日志消息
            level: 日志级别

        Returns:
            添加了emoji的日志消息
        """
        # 如果消息已经包含emoji，直接返回
        if any(ord(char) > 127 for char in message[:10]):  # 简单检测是否已有emoji
            return message

        # 根据消息内容和级别添加emoji
        message_lower = message.lower()

        # 错误相关
        if level == "ERROR" or "错误" in message or "失败" in message or "error" in message_lower:
            if "网络" in message or "请求" in message or "下载" in message:
                return f"❌ {message}"
            else:
                return f"🚫 {message}"

        # 成功相关
        if "成功" in message or "完成" in message or "success" in message_lower:
            if "strm" in message_lower or "生成" in message:
                return f"✅ {message}"
            elif "下载" in message:
                return f"📥 {message}"
            else:
                return f"✅ {message}"

        # 进度相关
        if "进度" in message or "progress" in message_lower or "%" in message:
            return f"📊 {message}"

        # 任务开始/结束
        if "开始" in message or "启动" in message or "start" in message_lower:
            return f"🚀 {message}"
        elif "结束" in message or "完成" in message or "finish" in message_lower:
            return f"🏁 {message}"

        # 线程相关
        if "线程" in message or "thread" in message_lower:
            return f"🧵 {message}"

        # 目录/文件相关
        if "创建目录" in message or "目录" in message:
            return f"📁 {message}"
        elif "文件" in message and ("生成" in message or "创建" in message):
            return f"📄 {message}"

        # 统计相关
        if "统计" in message or "总计" in message or "汇总" in message:
            return f"📈 {message}"

        # 警告相关
        if level == "WARNING" or level == "WARN" or "警告" in message:
            return f"⚠️ {message}"

        # 信息相关
        if level == "INFO":
            if "任务信息" in message or "配置" in message or "设置" in message:
                return f"ℹ️ {message}"
            elif "服务器" in message:
                return f"🖥️ {message}"
            else:
                return f"📝 {message}"

        # 默认情况
        return message

    async def log(self, message: str, level: str = "INFO") -> None:
        """
        向任务日志添加一条记录

        Args:
            message: 日志消息
            level: 日志级别，默认为INFO
        """
        # 为消息添加emoji
        enhanced_message = self._add_emoji_to_message(message, level)

        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{level}] {enhanced_message}"

        if self.log_content:
            self.log_content += f"\n{log_line}"
        else:
            self.log_content = log_line

        await self.save(update_fields=["log_content"])


__all__ = ["StrmTask"]
