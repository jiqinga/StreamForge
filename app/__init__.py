from contextlib import asynccontextmanager
from datetime import datetime
import asyncio

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from starlette.staticfiles import StaticFiles

from app.api.v1.utils import refresh_api_list
from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_menus,
    init_users,
    make_middlewares,
    modify_db,
    register_db,
    register_exceptions,
    register_routers,
    init_system_settings,
)

from app.log import log
from app.models.system import Log
from app.models.system import LogType, LogDetailType

try:
    from app.settings import APP_SETTINGS
except ImportError:
    raise SettingNotFound("Can not import settings")


def create_app() -> FastAPI:
    if APP_SETTINGS.DEBUG:
        _app = FastAPI(
            title=APP_SETTINGS.APP_TITLE,
            description=APP_SETTINGS.APP_DESCRIPTION,
            version=APP_SETTINGS.VERSION,
            openapi_url="/openapi.json",
            middleware=make_middlewares(),
            lifespan=lifespan,
        )
    else:
        _app = FastAPI(
            title=APP_SETTINGS.APP_TITLE,
            description=APP_SETTINGS.APP_DESCRIPTION,
            version=APP_SETTINGS.VERSION,
            openapi_url=None,
            middleware=make_middlewares(),
            lifespan=lifespan,
        )
    register_db(_app)
    register_exceptions(_app)
    register_routers(_app, prefix="/api")

    redis = aioredis.from_url(url=APP_SETTINGS.REDIS_URL)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    return _app


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_time = datetime.now()
    try:
        log.info("🚀 开始初始化应用...")

        # 在应用启动最开始就禁用SQL日志
        from app.log.log import set_sql_logging_enabled
        set_sql_logging_enabled(False)

        await modify_db()
        log.info("🗄️ 数据库迁移和升级已完成")

        # 提前初始化系统设置，确保SQL日志配置在其他数据库操作之前生效
        await init_system_settings()
        log.info("⚙️ 系统设置初始化完成")

        await init_menus()
        log.info("📋 菜单初始化完成")

        await refresh_api_list()
        log.info("🔄 API列表刷新完成")

        await init_users()
        log.info("👤 用户初始化完成")

        # 初始化任务恢复服务
        from app.core.task_recovery import setup_task_recovery
        await setup_task_recovery()  # 从数据库读取配置
        log.info("🔧 任务恢复服务初始化完成")

        # 初始化重试服务
        from app.core.retry_service import setup_retry_service
        await setup_retry_service()
        log.info("🔄 重试服务初始化完成")

        log.info("✅ 应用初始化完成，等待请求...")
        await Log.create(log_type=LogType.SystemLog, log_detail_type=LogDetailType.SystemStart)
        yield

    finally:
        # 关闭重试服务
        try:
            from app.core.retry_service import shutdown_retry_service
            await shutdown_retry_service()
            log.info("🔄 重试服务已关闭")
        except Exception as e:
            log.error(f"❌ 关闭重试服务时发生错误: {str(e)}")

        end_time = datetime.now()
        runtime = (end_time - start_time).total_seconds() / 60
        log.info(f"⏱️ App {_app.title} runtime: {runtime} min")  # noqa
        await Log.create(log_type=LogType.SystemLog, log_detail_type=LogDetailType.SystemStop)


app = create_app()

app.mount("/static", StaticFiles(directory=APP_SETTINGS.STATIC_ROOT), name="static")
