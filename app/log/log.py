import sys
import time
import logging
import re
import os
from datetime import datetime
from types import FrameType
from typing import cast, Dict
from pathlib import Path
from loguru import logger

from app.core.ctx import CTX_X_REQUEST_ID
from app.settings import APP_SETTINGS

# 配置Tortoise ORM的日志记录器
tortoise_logger = logging.getLogger("tortoise")
# 默认设置为WARNING级别，禁用SQL日志
tortoise_logger.setLevel(logging.WARNING)

# 日志配置控制标志
_sql_logging_enabled = False
_current_log_level = "DEBUG"  # 默认日志级别


async def get_logs_directory() -> Path:
    """获取日志目录路径，优先从数据库读取，否则使用默认配置"""
    try:
        # 尝试从数据库读取系统设置
        from app.models.strm import SystemSettings
        settings = await SystemSettings.all().first()

        if settings and settings.logs_directory:
            # 如果数据库中有配置，使用数据库配置
            logs_dir = Path(settings.logs_directory)

            # 如果是相对路径，相对于项目根目录
            if not logs_dir.is_absolute():
                logs_dir = APP_SETTINGS.BASE_DIR / logs_dir

            # 确保目录存在
            logs_dir.mkdir(parents=True, exist_ok=True)
            return logs_dir.resolve()

    except Exception as e:
        # 如果读取数据库失败，使用默认配置
        print(f"读取日志目录配置失败，使用默认配置: {e}")

    # 使用默认配置 app/logs
    default_logs_dir = APP_SETTINGS.BASE_DIR / "app/logs"
    default_logs_dir.mkdir(parents=True, exist_ok=True)
    return default_logs_dir


async def get_log_retention_days() -> int:
    """获取日志保留天数，优先从数据库读取，否则使用默认值"""
    try:
        # 尝试从数据库读取系统设置
        from app.models.strm import SystemSettings
        settings = await SystemSettings.all().first()

        if settings and hasattr(settings, 'log_retention_days') and settings.log_retention_days:
            return settings.log_retention_days

    except Exception as e:
        # 如果读取数据库失败，使用默认值
        print(f"读取日志保留天数配置失败，使用默认值: {e}")

    # 使用默认值 30天
    return 30


def get_logs_directory_sync() -> Path:
    """同步版本的获取日志目录路径"""
    try:
        # 对于同步调用，使用默认配置 app/logs
        # 这主要用于应用启动时的初始化
        default_logs_dir = APP_SETTINGS.BASE_DIR / "app/logs"
        default_logs_dir.mkdir(parents=True, exist_ok=True)
        return default_logs_dir
    except Exception as e:
        print(f"获取日志目录失败: {e}")
        # 如果默认目录也失败，使用当前目录下的logs
        fallback_dir = Path("logs")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


def get_log_retention_days_sync() -> int:
    """同步版本的获取日志保留天数"""
    try:
        # 对于同步调用，尝试读取SQLite数据库
        import sqlite3
        db_path = APP_SETTINGS.BASE_DIR / "app_system.sqlite3"

        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT log_retention_days FROM strm_system_settings LIMIT 1")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] is not None:
                return int(result[0])

    except Exception as e:
        print(f"读取日志保留天数配置失败，使用默认值: {e}")

    # 使用默认值 30天
    return 30


def set_sql_logging_enabled(enabled: bool):
    """设置SQL日志是否启用"""
    global _sql_logging_enabled

    # 只在状态真正改变时才打印日志和调整设置
    if _sql_logging_enabled != enabled:
        _sql_logging_enabled = enabled

        # 动态调整Tortoise ORM日志级别
        if enabled:
            tortoise_logger.setLevel(logging.DEBUG)
            logger.info("🗄️ SQL日志已启用")
        else:
            tortoise_logger.setLevel(logging.WARNING)
            logger.info("🗄️ SQL日志已禁用")


def set_log_level(level: str):
    """设置日志级别"""
    global _current_log_level

    # 只在级别真正改变时才打印日志和更新设置
    new_level = level.upper()
    if _current_log_level != new_level:
        _current_log_level = new_level
        logger.info(f"📊 日志级别已设置为: {_current_log_level}")


def get_current_log_level() -> str:
    """获取当前日志级别"""
    return _current_log_level


def is_sql_logging_enabled() -> bool:
    """检查SQL日志是否启用"""
    return _sql_logging_enabled


def x_request_id_filter(record):
    record["x_request_id"] = CTX_X_REQUEST_ID.get()
    return record["x_request_id"]


# 请求计时器，用于存储每个请求的开始时间和处理时间
class RequestTimer:
    _instance = None
    _request_times: Dict[str, float] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RequestTimer, cls).__new__(cls)
        return cls._instance

    def start_timer(self, request_id):
        """开始计时"""
        self._request_times[request_id] = time.time()

    def get_elapsed_time(self, request_id):
        """获取处理时间（毫秒）"""
        start_time = self._request_times.get(request_id)
        if start_time:
            elapsed = (time.time() - start_time) * 1000
            # 清理，防止内存泄漏
            del self._request_times[request_id]
            return elapsed
        return None


# 全局请求计时器实例
request_timer = RequestTimer()


class Logger:
    """输出日志到文件和控制台"""

    def __init__(self):
        self.logger = logger
        self.logger.remove()
        # 使用同步版本获取日志目录（用于初始化）
        logs_dir = get_logs_directory_sync()
        self._setup_loggers(logs_dir)

    def _setup_loggers(self, logs_dir: Path = None):
        """设置日志记录器"""
        if logs_dir is None:
            logs_dir = get_logs_directory_sync()

        log_name = f"Fast_{time.strftime('%Y-%m-%d', time.localtime()).replace('-', '_')}.log"
        log_path = logs_dir / log_name

        # 获取当前日志级别
        current_level = get_current_log_level()

        # 设置控制台输出
        self.logger.add(sys.stdout, level=current_level)

        # 获取日志保留天数设置
        retention_days = get_log_retention_days_sync()

        # 设置文件输出，使用动态的保留天数
        self.logger.add(
            log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} - "
            "{process.name} | "
            "{thread.name} | "
            "<red> {x_request_id} </red> | "
            "{module}.{function}:{line} - {level} -{message}",
            encoding="utf-8",
            retention=f"{retention_days} days",
            backtrace=True,
            diagnose=True,
            enqueue=True,
            rotation="00:00",
            filter=x_request_id_filter,
            level=current_level,
        )

    def reconfigure_loggers(self):
        """重新配置日志记录器（当设置发生变化时调用）"""
        self.logger.remove()
        # 重新获取日志目录配置
        logs_dir = get_logs_directory_sync()
        self._setup_loggers(logs_dir)
        logger.info("🔄 日志配置已重新加载")

    async def reconfigure_loggers_async(self):
        """异步重新配置日志记录器（当设置发生变化时调用）"""
        self.logger.remove()
        # 异步获取日志目录配置
        logs_dir = await get_logs_directory()
        self._setup_loggers(logs_dir)
        logger.info("🔄 日志配置已重新加载")

    @staticmethod
    def init_config():
        LOGGER_NAMES = ("uvicorn.asgi", "uvicorn.access", "uvicorn", "tortoise")

        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in LOGGER_NAMES:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler()]
            # 为Tortoise ORM默认设置WARNING级别，禁用SQL查询日志
            # SQL日志的启用/禁用通过set_sql_logging_enabled函数控制
            if logger_name == "tortoise":
                logging_logger.setLevel(logging.WARNING)

    def get_logger(self):
        return self.logger


# 全局Logger实例
_global_logger_instance = None


def get_global_logger_instance():
    """获取全局Logger实例"""
    global _global_logger_instance
    if _global_logger_instance is None:
        _global_logger_instance = Logger()
    return _global_logger_instance


def reconfigure_global_logger():
    """重新配置全局日志记录器"""
    global _global_logger_instance
    if _global_logger_instance is not None:
        _global_logger_instance.reconfigure_loggers()


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = cast(FrameType, frame.f_back)
            depth += 1

        message = record.getMessage()

        # 处理SQL日志
        if record.name == "tortoise":
            # 检查是否启用SQL日志
            if not _sql_logging_enabled:
                return  # 如果未启用SQL日志，直接返回不处理

            # 为SQL查询添加特殊格式
            if "SELECT" in message or "INSERT" in message or "UPDATE" in message or "DELETE" in message:
                message = f"🗄️ SQL: {message}"
            elif "PRAGMA" in message:
                message = f"🔧 PRAGMA: {message}"
            else:
                message = f"📊 DB: {message}"

        # 处理访问日志
        elif record.name == "uvicorn.access":
            # 匹配访问日志格式: 127.0.0.1:34957 - "GET /api/v1/auth/user-info HTTP/1.1" 200
            access_log_pattern = r'([^:]+):(\d+) - "([A-Z]+) ([^ ]+) HTTP/\d\.\d" (\d+)'
            match = re.match(access_log_pattern, message)

            if match:
                client_ip, client_port, method, path, status = match.groups()

                # 从APILoggerMiddleware中获取处理时间
                elapsed_time = getattr(record, "process_time", None)
                if elapsed_time is None:
                    # 尝试从当前上下文获取request_id
                    request_id = CTX_X_REQUEST_ID.get()
                    if request_id:
                        elapsed_time = request_timer.get_elapsed_time(request_id)

                # 添加处理时间到日志消息
                if elapsed_time is not None:
                    message = f"{message} - {elapsed_time:.2f}ms"

        logger.opt(depth=depth, exception=record.exc_info).log(level, message)


async def reconfigure_global_logger_async():
    """异步重新配置全局日志记录器"""
    global_logger = get_global_logger_instance()
    if global_logger:
        await global_logger.reconfigure_loggers_async()
        # 重新配置后，清理旧的日志文件
        await cleanup_old_log_files()


async def cleanup_old_log_files():
    """清理超过保留期的旧日志文件"""
    try:
        from datetime import datetime, timedelta
        import os

        # 获取日志目录和保留天数
        logs_dir = await get_logs_directory()
        retention_days = await get_log_retention_days()

        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # 扫描日志目录
        if logs_dir.exists():
            log_files_removed = 0
            for log_file in logs_dir.glob("Fast_*.log"):
                try:
                    # 从文件名提取日期 (Fast_2025_05_16.log)
                    file_name = log_file.stem  # Fast_2025_05_16
                    date_part = file_name.replace("Fast_", "")  # 2025_05_16
                    file_date = datetime.strptime(date_part, "%Y_%m_%d")

                    # 如果文件日期早于截止日期，删除文件
                    if file_date < cutoff_date:
                        log_file.unlink()
                        log_files_removed += 1
                        logger.info(f"🗑️ 已删除过期日志文件: {log_file.name}")

                except (ValueError, OSError) as e:
                    logger.warning(f"⚠️ 处理日志文件 {log_file.name} 时出错: {e}")

            if log_files_removed > 0:
                logger.info(f"🧹 日志清理完成，共删除 {log_files_removed} 个过期文件")
            else:
                logger.info("✅ 没有需要清理的过期日志文件")

    except Exception as e:
        logger.error(f"❌ 清理旧日志文件时出错: {e}")


Loggers = Logger()
Loggers.init_config()
log = Loggers.get_logger()
