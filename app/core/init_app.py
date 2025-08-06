from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

# from fastapi.exceptions import HTTPException as FastAPIHTTPException
from tortoise.contrib.fastapi import register_tortoise
from tortoise.exceptions import MultipleObjectsReturned

from app.api import api_router
from app.controllers import role_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    FastAPIHttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.log.log import logger, get_global_logger_instance

from app.core.middlewares import APILoggerMiddleware, APILoggerAddResponseMiddleware
from app.models.system import Menu, Role, User, Button, Api
from app.models.system import StatusType, IconType, MenuType
from app.settings import APP_SETTINGS


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=APP_SETTINGS.CORS_ORIGINS,
            allow_credentials=APP_SETTINGS.CORS_ALLOW_CREDENTIALS,
            allow_methods=APP_SETTINGS.CORS_ALLOW_METHODS,
            allow_headers=APP_SETTINGS.CORS_ALLOW_HEADERS,
        ),
        Middleware(APILoggerMiddleware),
        Middleware(APILoggerAddResponseMiddleware),
    ]
    return middleware


def register_db(app: FastAPI):
    register_tortoise(
        app,
        config=APP_SETTINGS.TORTOISE_ORM,
        generate_schemas=True,
    )


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)  # type: ignore
    # app.add_exception_handler(FastAPIHTTPException, FastAPIHttpExcHandle)  # 添加FastAPI原生HTTPException的处理
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)

    # 添加注释，说明异常处理的最佳实践
    # logger.info("已注册异常处理器，包括自定义HTTPException和FastAPI原生HTTPException")
    # logger.info("建议在代码中统一使用app.core.exceptions.HTTPException，而不是fastapi.exceptions.HTTPException")


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def modify_db():
    command = Command(tortoise_config=APP_SETTINGS.TORTOISE_ORM, app="app_system")
    try:
        await command.init_db(safe=True)
    except FileExistsError:
        ...

    try:
        await command.init()
    except Exception:
        ...

    await command.migrate()
    await command.upgrade(run_in_transaction=True)


async def init_menus():
    menus = await Menu.exists()
    if menus:
        return
    logger.info("初始化菜单")
    constant_menu = [
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="login",
            route_name="login",
            route_path="/login",
            component="layout.blank$view.login",
            order=1,
            i18n_key="route.login",
            props=True,
            constant=True,
            hide_in_menu=True,
        ),
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="403",
            route_name="403",
            route_path="/403",
            component="layout.blank$view.403",
            order=2,
            i18n_key="route.403",
            constant=True,
            hide_in_menu=True,
        ),
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="404",
            route_name="404",
            route_path="/404",
            component="layout.blank$view.404",
            order=3,
            i18n_key="route.404",
            constant=True,
            hide_in_menu=True,
        ),
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="500",
            route_name="500",
            route_path="/500",
            component="layout.blank$view.500",
            order=4,
            i18n_key="route.500",
            constant=True,
            hide_in_menu=True,
        ),
    ]
    await Menu.bulk_create(constant_menu)

    # 1
    await Menu.create(
        status=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.menu,
        menu_name="首页",
        route_name="home",
        route_path="/home",
        component="layout.base$view.home",
        order=1,
        i18n_key="route.home",
        icon="mdi:monitor-dashboard",
        icon_type=IconType.iconify,
    )
    await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.menu,
        menu_name="关于",
        route_name="about",
        route_path="/about",
        component="layout.base$view.about",
        order=99,
        i18n_key="route.about",
        icon="fluent:book-information-24-regular",
        icon_type=IconType.iconify,
    )

    # 16
    root_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="系统管理",
        route_name="manage",
        route_path="/manage",
        component="layout.base",
        order=5,
        i18n_key="route.manage",
        icon="carbon:cloud-service-management",
        icon_type=IconType.iconify,
    )

    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.menu,
        menu_name="日志管理",
        route_name="manage_log",
        route_path="/manage/log",
        component="view.manage_log",
        order=1,
        i18n_key="route.manage_log",
        icon="material-symbols:list-alt-outline",
        icon_type=IconType.iconify,
    )
    button_add_del_batch_del = await Button.create(button_code="B_Add_Del_Batch-del", button_desc="新增_删除_批量删除")

    await parent_menu.by_menu_buttons.add(button_add_del_batch_del)
    await parent_menu.save()

    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.menu,
        menu_name="API管理",
        route_name="manage_api",
        route_path="/manage/api",
        component="view.manage_api",
        order=2,
        i18n_key="route.manage_api",
        icon="ant-design:api-outlined",
        icon_type=IconType.iconify,
    )
    button_refreshAPI = await Button.create(button_code="B_refreshAPI", button_desc="刷新API")

    await parent_menu.by_menu_buttons.add(button_refreshAPI)
    await parent_menu.save()

    children_menu = [
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="用户管理",
            route_name="manage_user",
            route_path="/manage/user",
            component="view.manage_user",
            order=3,
            i18n_key="route.manage_user",
            icon="ic:round-manage-accounts",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="角色管理",
            route_name="manage_role",
            route_path="/manage/role",
            component="view.manage_role",
            order=4,
            i18n_key="route.manage_role",
            icon="carbon:user-role",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="菜单管理",
            route_name="manage_menu",
            route_path="/manage/menu",
            component="view.manage_menu",
            order=5,
            i18n_key="route.manage_menu",
            icon="material-symbols:route",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="用户详情",
            route_name="manage_user-detail",
            route_path="/manage/user-detail/:id",
            component="view.manage_user-detail",
            order=6,
            i18n_key="route.manage_user-detail",
            hide_in_menu=True,
        ),
    ]
    await Menu.bulk_create(children_menu)

    # strm
    strm_root = await Menu.create(
        status=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="STRM管理",
        route_name="strm",
        route_path="/strm",
        component="layout.base",
        order=5,
        i18n_key="route.strm",
        icon="mdi:folder-text",
        icon_type=IconType.iconify,
    )

    strm_upload = await Menu.create(
        status=StatusType.enable,
        parent_id=strm_root.id,
        menu_type=MenuType.menu,
        menu_name="文件上传",
        route_name="strm_upload",
        route_path="/strm/upload",
        component="view.strm_upload",
        order=1,
        i18n_key="route.strm_upload",
        icon="mdi:upload",
        icon_type=IconType.iconify,
    )

    strm_generate = await Menu.create(
        status=StatusType.enable,
        parent_id=strm_root.id,
        menu_type=MenuType.menu,
        menu_name="STRM生成",
        route_name="strm_generate",
        route_path="/strm/generate",
        component="view.strm_generate",
        order=3,
        i18n_key="route.strm_generate",
        icon="mdi:file-export",
        icon_type=IconType.iconify,
    )

    strm_history = await Menu.create(
        status=StatusType.enable,
        parent_id=strm_root.id,
        menu_type=MenuType.menu,
        menu_name="上传历史",
        route_name="strm_history",
        route_path="/strm/history",
        component="view.strm_history",
        order=2,
        i18n_key="route.strm_history",
        icon="mdi:history",
        icon_type=IconType.iconify,
    )

    strm_tasks = await Menu.create(
        status=StatusType.enable,
        parent_id=strm_root.id,
        menu_type=MenuType.menu,
        menu_name="任务管理",
        route_name="strm_tasks",
        route_path="/strm/tasks",
        component="view.strm_tasks",
        order=4,
        i18n_key="route.strm_tasks",
        icon="mdi:clipboard-text-clock",
        icon_type=IconType.iconify,
    )

    # 系统设置菜单移至系统管理模块下
    system_settings = await Menu.create(
        status=StatusType.enable,
        parent_id=root_menu.id,  # 修改为系统管理的ID
        menu_type=MenuType.menu,
        menu_name="系统设置",
        route_name="manage_settings",
        route_path="/manage/settings",
        component="view.manage_settings",
        order=6,
        i18n_key="route.manage_settings",
        icon="mdi:cog",
        icon_type=IconType.iconify,
    )


async def insert_role(
    children_role: list[Role],
    role_apis: list[tuple[str, str]] = None,
    role_menus: list[str] = None,
    role_buttons: list[str] = None,
):
    if role_apis is None:
        role_apis = []
    if role_menus is None:
        role_menus = []
    if role_buttons is None:
        role_buttons = []

    on_conflict = ("role_code",)
    update_fields = ("role_name", "role_desc")

    await Role.bulk_create(children_role, on_conflict=on_conflict, update_fields=update_fields)

    for role_zs in children_role:
        role_obj = await Role.get(role_code=role_zs.role_code)
        for api_method, api_path in role_apis:
            try:
                api_obj: Api = await Api.get(api_method=api_method, api_path=api_path)
                await role_obj.by_role_apis.add(api_obj)
            except DoesNotExist:
                print("不存在API", api_method, api_path)
                return False

        for route_name in role_menus:
            try:
                menu_obj: Menu = await Menu.get(route_name=route_name)
                await role_obj.by_role_menus.add(menu_obj)
            except MultipleObjectsReturned:
                print("多个菜单", route_name)
                return False

        for button_code in role_buttons:
            button_obj: Button = await Button.get(button_code=button_code)
            await role_obj.by_role_buttons.add(button_obj)

        await role_obj.save()
    return True


async def init_users():
    role_exist = await role_controller.model.exists()
    if not role_exist:
        role_home_menu = await Menu.get(route_name="home")
        # 超级管理员拥有所有菜单 所有按钮
        super_role_obj = await Role.create(
            role_name="超级管理员", role_code="R_SUPER", role_desc="超级管理员", by_role_home=role_home_menu
        )
        role_super_menu_objs = await Menu.filter(constant=False)  # 过滤常量路由(公共路由)
        for menu_obj in role_super_menu_objs:
            await super_role_obj.by_role_menus.add(menu_obj)
        for button_obj in await Button.all():
            await super_role_obj.by_role_buttons.add(button_obj)

        # 管理员拥有 首页 关于 系统管理-API管理 系统管理-用户管理
        role_admin = await Role.create(
            role_name="管理员", role_code="R_ADMIN", role_desc="管理员", by_role_home=role_home_menu
        )

        role_admin_apis = [
            ("post", "/api/v1/system-manage/logs/all/"),
            ("post", "/api/v1/system-manage/apis/all/"),
            ("post", "/api/v1/system-manage/users/all/"),
            ("get", "/api/v1/system-manage/roles"),
            ("post", "/api/v1/system-manage/users"),  # 新增用户
            ("patch", "/api/v1/system-manage/users/{user_id}"),  # 修改用户
            ("delete", "/api/v1/system-manage/users/{user_id}"),  # 删除用户
            ("delete", "/api/v1/system-manage/users"),  # 批量删除用户
        ]
        role_admin_menus = ["home", "about", "function_toggle-auth", "manage_log", "manage_api", "manage_user"]
        role_admin_buttons = ["B_CODE2", "B_CODE3"]
        await insert_role([role_admin], role_admin_apis, role_admin_menus, role_admin_buttons)

        # 普通用户拥有 首页 关于 系统管理-API管理
        role_user = await Role.create(
            role_name="普通用户", role_code="R_USER", role_desc="普通用户", by_role_home=role_home_menu
        )
        role_user_apis = [("post", "/api/v1/system-manage/logs/all/"), ("post", "/api/v1/system-manage/apis/all/")]
        role_user_menus = ["home", "about", "function_toggle-auth", "manage_log", "manage_api"]
        role_user_buttons = ["B_CODE3"]
        await insert_role([role_user], role_user_apis, role_user_menus, role_user_buttons)

    user = await user_controller.model.exists()
    if not user:
        super_role_obj: Role | None = await role_controller.get_by_code("R_SUPER")
        user_super_obj: User = await user_controller.create(
            UserCreate(
                userName="Soybean",  # type: ignore
                userEmail="admin@admin.com",  # type: ignore
                password="123456",
            )
        )
        await user_super_obj.by_user_roles.add(super_role_obj)

        user_super_obj: User = await user_controller.create(
            UserCreate(
                userName="Super",  # type: ignore
                userEmail="admin1@admin.com",  # type: ignore
                password="123456",
            )
        )
        await user_super_obj.by_user_roles.add(super_role_obj)

        admin_role_obj: Role | None = await role_controller.get_by_code("R_ADMIN")
        user_admin_obj = await user_controller.create(
            UserCreate(
                userName="Admin",  # type: ignore
                userEmail="admin2@admin.com",  # type: ignore
                password="123456",
            )
        )
        await user_admin_obj.by_user_roles.add(admin_role_obj)

        user_role_obj: Role | None = await role_controller.get_by_code("R_USER")
        user_user_obj = await user_controller.create(
            UserCreate(
                userName="User",  # type: ignore
                userEmail="user@user.com",  # type: ignore
                password="123456",
            )
        )
        await user_user_obj.by_user_roles.add(user_role_obj)


async def init_system_settings():
    """初始化系统默认设置，包括文件类型配置"""
    from app.models.strm import SystemSettings
    from app.controllers.strm import system_settings_controller
    import os

    systemsetting = await SystemSettings.exists()
    if systemsetting:
        # 如果系统设置已存在，初始化SQL日志设置
        await system_settings_controller.init_sql_logging()
        return
    logger.info("初始化系统设置")
    # 获取程序运行目录下的strm_output文件夹路径
    output_dir = os.path.join(os.getcwd(), "strm_output")

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建STRM输出目录: {output_dir}")
    await SystemSettings.create(
        enable_path_replacement=True,
        replacement_path="/nas",
        download_threads=1,
        output_directory=output_dir,
        video_file_types="mkv,iso,ts,mp4,avi,rmvb,wmv,m2ts,mpg,flv,rm,mov",
        audio_file_types="mp3,flac,wav,aac,ogg,m4a,wma",
        image_file_types="jpg,jpeg,png,gif,bmp,tiff,svg,heic,webp",
        subtitle_file_types="srt,ass,ssa,vtt,sub,idx",
        metadata_file_types="nfo,xml,json,txt",
        enable_sql_logging=False,  # 默认禁用SQL日志
        logs_directory="app/logs",  # 默认日志目录
    )

    # 初始化全局Logger实例
    get_global_logger_instance()

    # 初始化所有日志设置
    await system_settings_controller.init_all_logging_settings()


# async def init_media_servers():
#     """初始化默认媒体服务器"""
#     from app.models.strm import MediaServer, ServerType, ServerStatus
#     from app.controllers.strm.server_controller import server_controller
#
#     try:
#         # 检查是否已存在媒体服务器
#         servers_exist = await MediaServer.exists()
#         if servers_exist:
#             return
#
#         # 直接创建媒体服务器，不依赖用户
#         # 使用模型直接创建媒体服务器，而不使用控制器
#         # 创建默认HTTP服务器
#         await MediaServer.create(
#             name="本地HTTP服务器",
#             server_type=ServerType.HTTP,
#             base_url="http://localhost:8000",
#             description="本地测试HTTP服务器",
#             auth_required=False,
#             status=ServerStatus.UNKNOWN,
#         )
#
#         # 创建HTTPS服务器
#         await MediaServer.create(
#             name="本地HTTPS服务器",
#             server_type=ServerType.HTTPS,
#             base_url="https://localhost:8443",
#             description="本地测试HTTPS服务器",
#             auth_required=False,
#             status=ServerStatus.UNKNOWN,
#         )
#
#         # 创建默认下载服务器
#         await MediaServer.create(
#             name="默认下载服务器",
#             server_type=ServerType.CD2HOST,
#             base_url="http://download.example.com",
#             description="默认下载服务器配置",
#             auth_required=False,
#             status=ServerStatus.UNKNOWN,
#         )
#
#         # 创建默认媒体服务器
#         await MediaServer.create(
#             name="默认媒体服务器",
#             server_type=ServerType.XIAOYAHOST,
#             base_url="http://media.example.com",
#             description="默认媒体服务器配置",
#             auth_required=False,
#             status=ServerStatus.UNKNOWN,
#         )
#
#         logger.info("已成功创建默认媒体服务器")
#     except Exception as e:
#         logger.error(f"创建默认媒体服务器失败: {str(e)}")
#         # 记录更多诊断信息
#         try:
#             tables = await MediaServer._meta.db.executor.execute_query(
#                 "SELECT name FROM sqlite_master WHERE type='table'"
#             )
#             logger.info(f"数据库表列表: {tables}")
#         except Exception as table_e:
#             logger.error(f"检查数据库表失败: {str(table_e)}")
