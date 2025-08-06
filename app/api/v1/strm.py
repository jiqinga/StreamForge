"""
STRM管理模块API

注意：异常处理最佳实践
-------------------------------
本项目推荐使用自定义的HTTPException类而不是FastAPI的HTTPException类。

推荐用法:
```python
from app.core.exceptions import HTTPException
raise HTTPException(code="4001", msg="认证失败")
```

而不是:
```python
from fastapi import HTTPException
raise HTTPException(status_code=401, detail="认证失败")
```

系统已添加兼容层处理两种类型的异常，但为保持一致性，请尽量使用自定义HTTPException。
"""

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Body,
    Query,
    Path,
    Request,
    status,
    BackgroundTasks,
)
from types import SimpleNamespace
import json
from app.controllers.strm.upload import (
    handle_file_upload,
    parse_uploaded_file,
    delete_upload_record,
    download_upload_file,
    get_parse_result,
    handle_url_upload,
    get_directory_content,
    search_files,
)
from app.controllers.strm.task_controller import (
    create_strm_task,
    get_task_status,
    get_task_files,
    get_task_directory_content,
    get_user_tasks,
    delete_task,
    cancel_task,
    continue_task,
    start_strm_task,
    get_task_logs,
    get_file_preview

    # process_strm_task,
)
from app.core.dependency import get_current_user, check_token, AuthControl
from app.models.system import User
from app.schemas.base import Success, SuccessExtra
from app.schemas.strm.schemas import (
    ParseRequest,
    UploadHistoryResponse,
    UrlUploadRequest,
    MediaServerResponse,
    StrmTaskCreate,
    StrmTaskResponse,
    SystemSettingsUpdate,
    SystemSettingsResponse,
    MediaServerBase,
)
from app.models.strm.upload import UploadRecord
from app.models.strm import MediaServer
from typing import List, Optional
from fastapi.responses import FileResponse, JSONResponse
from app.core.exceptions import HTTPException
from app.controllers.strm import system_settings_controller
from app.controllers.strm.server_controller import server_controller
import asyncio
from datetime import datetime
from app.models.strm import TaskStatus, ProcessType
from tortoise.exceptions import ValidationError

router_strm = APIRouter()


# 认证用户从请求中
async def authenticate_user_from_request(request: Request, token: Optional[str] = None):
    """
    从请求中认证用户

    支持两种方式：
    1. 从授权头获取Bearer令牌
    2. 从URL查询参数获取令牌

    Args:
        request: FastAPI请求对象
        token: 可选令牌，如果已从其他地方获取

    Returns:
        认证的用户或None
    """
    from app.log.log import log

    current_user = None

    # 如果提供了token，直接使用
    if token:
        try:
            status, code, decode_data = check_token(token)
            if status and decode_data["data"]["tokenType"] == "accessToken":
                user_id = decode_data["data"]["userId"]
                current_user = await User.filter(id=user_id).first()
                if current_user:
                    log.debug(f"使用提供的token认证成功: 用户 {current_user.user_name}")
                else:
                    log.warning(f"使用提供的token认证失败: 用户ID {user_id} 不存在")
            else:
                log.warning(f"使用提供的token认证失败: 状态码 {code}")
        except Exception as e:
            log.error(f"处理提供的token时出错: {str(e)}")
            return None

    # 如果没有提供token或认证失败，尝试从授权头获取
    if not current_user:
        authorization = request.headers.get("authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            try:
                status, code, decode_data = check_token(token)
                if status and decode_data["data"]["tokenType"] == "accessToken":
                    user_id = decode_data["data"]["userId"]
                    current_user = await User.filter(id=user_id).first()
                    if current_user:
                        log.debug(f"使用授权头token认证成功: 用户 {current_user.user_name}")
                    else:
                        log.warning(f"使用授权头token认证失败: 用户ID {user_id} 不存在")
                else:
                    log.warning(f"使用授权头token认证失败: 状态码 {code}")
            except Exception as e:
                log.error(f"处理授权头token时出错: {str(e)}")

    # 如果仍未认证，尝试从URL查询参数获取令牌
    if not current_user:
        params = dict(request.query_params)
        token = params.get("token")
        if token:
            try:
                status, code, decode_data = check_token(token)
                if status and decode_data["data"]["tokenType"] == "accessToken":
                    user_id = decode_data["data"]["userId"]
                    current_user = await User.filter(id=user_id).first()
                    if current_user:
                        log.debug(f"使用URL查询参数token认证成功: 用户 {current_user.user_name}")
                    else:
                        log.warning(f"使用URL查询参数token认证失败: 用户ID {user_id} 不存在")
                else:
                    log.warning(f"使用URL查询参数token认证失败: 状态码 {code}")
            except Exception as e:
                log.error(f"处理URL查询参数token时出错: {str(e)}")

    return current_user


@router_strm.post("/upload", summary="上传115目录树文件")
async def upload_115_directory_tree_file(current_user: User = Depends(get_current_user), file: UploadFile = File(...)):
    """
    上传115目录树文件。
    - **current_user**: 当前已登录用户。
    - **file**: 要上传的文件。
    """
    upload_record = await handle_file_upload(file, current_user)

    # 将 ORM 对象转换为字典，以便可以序列化为 JSON
    result = {
        "id": upload_record.id,
        "filename": upload_record.filename,
        "filesize": upload_record.filesize,
        "status": upload_record.status.value if upload_record.status else None,
        "create_time": upload_record.create_time.isoformat() if upload_record.create_time else None,
        "uploader_id": upload_record.uploader_id,
        "parse_time": upload_record.parse_time.isoformat() if upload_record.parse_time else None,
    }

    return Success(data=result)


@router_strm.post("/upload-url", summary="通过URL上传115目录树文件")
async def upload_115_directory_tree_from_url(
    current_user: User = Depends(get_current_user), data: UrlUploadRequest = Body(...)
):
    """
    通过URL上传115目录树文件。
    - **current_user**: 当前已登录用户。
    - **data**: 包含URL的请求数据。
    """
    # 获取URL
    url = data.url
    # 移除可能的引号（前端有时会带引号）
    if url.startswith('"') and url.endswith('"'):
        url = url[1:-1]
    if url.startswith("'") and url.endswith("'"):
        url = url[1:-1]

    # 使用控制器处理URL上传
    upload_record = await handle_url_upload(url, current_user)

    # 将 ORM 对象转换为字典，以便可以序列化为 JSON
    result = {
        "id": upload_record.id,
        "filename": upload_record.filename,
        "filesize": upload_record.filesize,
        "status": upload_record.status.value if upload_record.status else None,
        "create_time": upload_record.create_time.isoformat() if upload_record.create_time else None,
        "uploader_id": upload_record.uploader_id,
        "parse_time": upload_record.parse_time.isoformat() if upload_record.parse_time else None,
    }

    return Success(data=result)


@router_strm.post("/parse", summary="解析已上传的115目录树文件")
async def parse_directory_tree_file(current_user: User = Depends(get_current_user), data: ParseRequest = Body(...)):
    """
    解析已上传的115目录树文件。
    - **current_user**: 当前已登录用户。
    - **data**: 包含记录ID的请求数据。
    """
    result_data = await parse_uploaded_file(data.record_id, current_user)

    # 确保返回的是可序列化的字典
    if isinstance(result_data, UploadRecord):
        result = {
            "id": result_data.id,
            "filename": result_data.filename,
            "filesize": result_data.filesize,
            "status": result_data.status.value if result_data.status else None,
            "create_time": result_data.create_time.isoformat() if result_data.create_time else None,
            "uploader_id": result_data.uploader_id,
            "parse_time": result_data.parse_time.isoformat() if result_data.parse_time else None,
            "parsed_result": result_data.parsed_result,
        }
    else:
        result = result_data

    return Success(data=result)


@router_strm.get("/history", summary="获取上传历史记录", response_model=UploadHistoryResponse)
async def get_upload_history(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
):
    """
    获取当前用户的文件上传历史记录。
    """
    skip = (page - 1) * page_size
    records = await UploadRecord.filter(uploader=current_user).offset(skip).limit(page_size).order_by("-create_time")
    total = await UploadRecord.filter(uploader=current_user).count()

    # 将 ORM 对象转换为字典以便可序列化为 JSON
    record_dicts = []
    for record in records:
        record_dict = {
            "id": record.id,
            "filename": record.filename,
            "filesize": record.filesize,
            "status": record.status.value,
            "create_time": record.create_time.isoformat(),
            "uploader_id": record.uploader_id,
            "parse_time": record.parse_time.isoformat() if record.parse_time else None,
        }
        record_dicts.append(record_dict)

    return Success(data={"total": total, "page": page, "page_size": page_size, "records": record_dicts})


@router_strm.delete("/history/{record_id}", summary="删除上传记录")
async def delete_history_record(
    record_id: int = Path(..., description="记录ID"), current_user: User = Depends(get_current_user)
):
    """
    删除上传记录及对应的文件。
    - **record_id**: 要删除的记录ID.
    - **current_user**: 当前已登录用户.
    """
    await delete_upload_record(record_id, current_user)
    return Success(data={"message": "记录已成功删除"})


@router_strm.get("/download/{record_id}", summary="下载已上传的文件", response_class=FileResponse)
async def download_file(
    request: Request,
    record_id: int = Path(..., description="记录ID"),
    token: Optional[str] = Query(None, description="认证令牌，可通过查询参数传递"),
):
    """
    下载已上传的文件。支持两种认证方式：
    1. 通过Authorization头传递Bearer token (标准方式)
    2. 通过URL查询参数传递token (便于直接下载)

    - **record_id**: 要下载的记录ID.
    - **token**: 可选参数，通过查询参数传递认证令牌.
    """
    # 尝试获取用户
    current_user = None

    # 方法1: 从请求头获取token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token = auth_header.replace("Bearer ", "")
        if bearer_token:
            status, code, decode_data = check_token(bearer_token)
            if status:
                if decode_data["data"]["tokenType"] == "accessToken":
                    user_id = decode_data["data"]["userId"]
                    current_user = await User.filter(id=user_id).first()

    # 方法2: 从查询参数获取token
    if current_user is None and token:
        status, code, decode_data = check_token(token)
        if status:
            if decode_data["data"]["tokenType"] == "accessToken":
                user_id = decode_data["data"]["userId"]
                current_user = await User.filter(id=user_id).first()

    # 如果没有通过任何方式获取到current_user，则认证失败
    if current_user is None:
        raise HTTPException(code="4001", msg="Authentication failed, valid token required")

    return await download_upload_file(record_id, current_user)


@router_strm.get("/result/{record_id}", summary="获取文件解析结果")
async def get_file_parse_result(
    record_id: int = Path(..., description="记录ID"),
    current_user: User = Depends(get_current_user),
    file_type: str = Query("all", description="文件类型过滤器 (all, video, audio, image, subtitle, metadata, other)"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    all_files: bool = Query(False, description="是否获取所有文件（不分页）"),
):
    """
    获取已解析文件的解析结果，支持按文件类型过滤和分页。
    - **record_id**: 要获取结果的记录ID。
    - **current_user**: 当前已登录用户。
    - **file_type**: 可选的文件类型过滤器，默认为"all"。
    - **page**: 页码，默认为1。
    - **page_size**: 每页数量，默认为10。
    - **all_files**: 是否返回所有文件（不进行分页），默认为false。
    """
    result = await get_parse_result(record_id, current_user, file_type, page, page_size, all_files)
    return Success(data=result)


@router_strm.get("/directory/{record_id}", summary="获取目录内容")
async def get_directory(
    record_id: int = Path(..., description="记录ID"),
    current_user: User = Depends(get_current_user),
    directory_path: str = Query("/", description="目录路径，默认为根目录"),
    file_type: str = Query("all", description="文件类型过滤器 (all, video, audio, image, subtitle, metadata, other)"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    """
    获取指定目录下的文件和子目录。
    此API采用懒加载方式，每次只返回指定目录下的直接文件和子目录，不会递归获取所有内容。

    - **record_id**: 要获取结果的记录ID。
    - **current_user**: 当前已登录用户。
    - **directory_path**: 目录路径，默认为根目录"/"。
    - **file_type**: 可选的文件类型过滤器，默认为"all"。
    - **page**: 页码，默认为1。
    - **page_size**: 每页数量，默认为20。
    """
    result = await get_directory_content(record_id, current_user, directory_path, file_type, page, page_size)
    return Success(data=result)


@router_strm.get("/search/{record_id}", summary="搜索文件")
async def search_parsed_files(
    record_id: int = Path(..., description="记录ID"),
    current_user: User = Depends(get_current_user),
    search_text: str = Query(..., description="搜索文本"),
    file_type: str = Query("all", description="文件类型过滤器 (all, video, audio, image, subtitle, metadata, other)"),
    ignore_case: bool = Query(True, description="是否忽略大小写"),
):
    """
    搜索已解析文件中的匹配项
    - **record_id**: 记录ID
    - **current_user**: 当前用户
    - **search_text**: 要搜索的文本
    - **file_type**: 文件类型过滤器 (all, video, audio, image, subtitle, metadata, other)
    - **ignore_case**: 是否忽略大小写，默认为True
    """
    result = await search_files(record_id, current_user, search_text, file_type, ignore_case)
    return Success(data=result)


# === STRM生成相关API端点 ===


@router_strm.get("/servers", summary="获取媒体服务器列表")
async def get_media_servers(current_user: User = Depends(get_current_user)):
    """
    获取当前用户可用的媒体服务器列表
    """
    servers = await MediaServer.all()
    # 将 ORM 对象转换为字典
    server_list = []
    for server in servers:
        server_dict = {
            "id": server.id,
            "name": server.name,
            "server_type": server.server_type,
            "base_url": server.base_url,
            "description": server.description,
            "auth_required": server.auth_required,
            "create_time": server.create_time.isoformat(),
            "status": server.status,
        }
        server_list.append(server_dict)

    return Success(data=server_list)


@router_strm.post("/generate", summary="创建STRM生成任务")
async def generate_strm(
    background_tasks: BackgroundTasks,
    data: StrmTaskCreate = Body(...),
    current_user: User = Depends(get_current_user),
):
    """
    创建STRM处理任务。

    此接口将根据文件类型自动处理：
    - 视频文件类型生成STRM文件
    - 音频、图片、字幕、元数据文件类型下载资源文件

    Args:
        background_tasks: 后台任务对象，用于异步启动任务
        data: 任务创建数据
        current_user: 当前用户
    """
    from app.log.log import log

    try:
        # 验证记录ID
        record = await UploadRecord.filter(id=data.record_id, uploader=current_user).first()
        if not record:
            raise HTTPException(code=404, msg=f"找不到上传记录ID: {data.record_id}")

        # 验证媒体服务器
        server = await MediaServer.filter(id=data.server_id).first()
        if not server:
            raise HTTPException(code=404, msg=f"找不到媒体服务器ID: {data.server_id}")

        # 验证下载服务器（如果指定了）
        download_server = None
        if data.download_server_id:
            download_server = await MediaServer.filter(id=data.download_server_id).first()
            if not download_server:
                raise HTTPException(code=404, msg=f"找不到下载服务器ID: {data.download_server_id}")
        # 获取系统设置
        settings = await system_settings_controller.get_settings()
        settings = SimpleNamespace(**settings)
        # 创建一个STRM任务
        task = await create_strm_task(
            record_id=data.record_id,
            server_id=data.server_id,
            user=current_user,
            output_dir=data.output_dir,
            custom_name=data.name,
            download_server_id=data.download_server_id,
            threads=settings.download_threads,
        )

        # 添加后台任务来处理STRM任务
        # background_tasks.add_task(process_strm_task, task.id)
        # 在后台启动任务处理
        background_tasks.add_task(
            start_strm_task,
            task_id=task.id,
            user_id=current_user.id,
        )
        log.info(f"已创建STRM处理任务: {task.id}")

        # 构建响应
        return Success(
            data=StrmTaskResponse.from_orm(task).model_dump(),
            msg="任务已创建并开始处理",
        )
    except ValidationError as e:
        log.error(f"输入验证错误: {e}")
        raise HTTPException(code=422, msg=f"输入验证错误: {str(e)}")
    except HTTPException as e:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        log.error(f"STRM任务创建失败: {e}")
        raise HTTPException(code=500, msg=f"创建任务时发生错误: {str(e)}")


@router_strm.get("/tasks", summary="获取用户任务列表")
async def get_tasks(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    search: Optional[str] = Query(None, description="按名称搜索"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    start_date: Optional[str] = Query(None, description="开始日期过滤 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期过滤 (YYYY-MM-DD)"),
):
    """
    获取当前用户的STRM生成任务列表，支持按名称搜索和按状态/日期过滤
    """
    result = await get_user_tasks(
        current_user, page, page_size, search=search, status=status, start_date=start_date, end_date=end_date
    )
    return Success(data=result)


@router_strm.get("/task/{task_id}", summary="获取任务状态")
async def check_task_status(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
):
    """
    获取指定任务的状态和进度
    """
    result = await get_task_status(task_id, current_user)
    return Success(data=result)


@router_strm.get("/task/{task_id}/files", summary="获取任务文件列表")
async def get_task_files_endpoint(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    file_type: Optional[str] = Query(None, description="文件类型过滤: video, audio, image, subtitle, metadata"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="处理状态过滤: completed(成功), failed(失败), canceled(已取消), downloading(处理中), pending(等待中)"),
):
    """
    获取指定任务的文件列表

    - **task_id**: 任务ID
    - **page**: 页码，默认为1
    - **page_size**: 每页数量，默认为10
    - **file_type**: 文件类型过滤，可选值: video, audio, image, subtitle, metadata
    - **search**: 搜索关键词，支持文件名和路径搜索
    - **status**: 处理状态过滤，可选值: completed(成功), failed(失败), canceled(已取消), downloading(处理中), pending(等待中)

    返回文件列表，包含分页信息和统计数据
    """
    result = await get_task_files(task_id, current_user, page, page_size, file_type, search, status)
    return Success(data=result)


@router_strm.get("/task/{task_id}/directory", summary="获取任务目录内容")
async def get_task_directory_content_endpoint(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    directory_path: str = Query("/", description="目录路径"),
):
    """
    获取指定任务的目录内容（用于树形视图懒加载）

    - **task_id**: 任务ID
    - **directory_path**: 目录路径，默认为根目录 "/"

    返回目录下的文件和子目录列表
    """
    result = await get_task_directory_content(task_id, current_user, directory_path)
    return Success(data=result)


@router_strm.post("/task/{task_id}/cancel", summary="取消任务")
async def cancel_task_endpoint(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
):
    """
    取消正在运行或等待中的任务。

    - **task_id**: 任务ID
    - **current_user**: 当前已登录用户

    只有状态为 PENDING 或 RUNNING 的任务可以被取消。
    取消任务会同时取消所有相关的下载任务。
    """
    result = await cancel_task(task_id, current_user)
    return Success(data=result)


@router_strm.post("/task/{task_id}/continue", summary="继续已取消的任务")
async def continue_task_endpoint(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
):
    """
    继续已取消的任务。

    - **task_id**: 任务ID
    - **current_user**: 当前已登录用户

    只有状态为 CANCELED 的任务可以被继续。
    继续任务会重置任务状态并重新启动处理。
    """
    result = await continue_task(task_id, current_user)
    return Success(data=result)


@router_strm.delete("/task/{task_id}", summary="删除任务")
async def delete_task_endpoint(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
):
    """
    删除任务。
    - **task_id**: 任务ID.
    - **current_user**: 当前已登录用户.
    """
    result = await delete_task(task_id, current_user)
    return Success(data=result)


@router_strm.get("/task/{task_id}/logs", summary="获取任务日志")
async def get_task_logs_endpoint(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, description="页码"),
    page_size: int = Query(50, description="每页数量"),
    level: Optional[str] = Query(None, description="日志级别过滤"),
    search: Optional[str] = Query(None, description="日志内容搜索"),
    log_type: Optional[str] = Query(None, description="日志类型过滤，可选值：task、download、strm"),
):
    """
    获取任务的详细日志记录。
    - **task_id**: 任务ID.
    - **current_user**: 当前已登录用户.
    - **page**: 页码，默认为1.
    - **page_size**: 每页数量，默认为50.
    - **level**: 日志级别过滤，可选值：INFO、ERROR等.
    - **search**: 日志内容搜索关键词.
    - **log_type**: 日志类型过滤，可选值：task（任务日志）、download（下载日志）、strm（STRM生成日志）.
    """
    logs = await get_task_logs(task_id, current_user, page, page_size, level, search, log_type)
    return Success(data=logs)


@router_strm.post("/tasks/recover", summary="修复异常任务状态")
async def recover_orphaned_tasks(
    current_user: User = Depends(get_current_user),
):
    """
    手动触发任务状态修复，用于修复程序重启后状态异常的任务。

    - **current_user**: 当前已登录用户

    该接口会检查所有运行中的任务，并根据以下条件修复异常状态：
    1. 任务运行时间超过2小时 -> 标记为失败
    2. 任务心跳超时 -> 标记为失败
    3. 程序重启后无活动的任务 -> 标记为失败
    """
    from app.core.task_recovery import TaskRecoveryService

    result = await TaskRecoveryService.recover_orphaned_tasks()
    return Success(data=result)


@router_strm.get("/task/{task_id}/file/preview", summary="获取任务文件预览")
async def get_task_file_preview(
    task_id: int = Path(..., description="任务ID"),
    file_path: str = Query(..., description="源文件路径，用于查找对应的处理结果"),
    current_user: User = Depends(get_current_user),
):
    """
    获取任务文件预览内容

    此接口通过源文件路径查找对应的处理结果，然后预览目标文件内容：
    - STRM文件：读取STRM文件中的视频链接URL
    - 文本文件：显示下载的文本文件内容
    - 图片文件：返回下载的图片文件信息
    - 其他文件：返回基本文件信息

    - **task_id**: 任务ID
    - **file_path**: 源文件路径（115网盘中的原始路径）
    """
    result = await get_file_preview(task_id, file_path, current_user)
    return Success(data=result)


# === 系统设置相关API端点 ===

# === 服务器管理API端点 ===


@router_strm.post("/server", summary="创建媒体服务器")
async def create_media_server(data: MediaServerBase = Body(...), current_user: User = Depends(get_current_user)):
    """
    创建新的媒体服务器

    - **current_user**: 当前已登录用户
    - **data**: 服务器数据
    """
    server = await server_controller.create_server(data.dict())
    return Success(
        data={
            "id": server.id,
            "name": server.name,
            "server_type": server.server_type,
            "base_url": server.base_url,
            "description": server.description,
            "auth_required": server.auth_required,
            "create_time": server.create_time.isoformat(),
            "status": server.status,
        }
    )


@router_strm.put("/server/{server_id}", summary="更新媒体服务器")
async def update_media_server(
    server_id: int = Path(..., description="服务器ID"),
    data: MediaServerBase = Body(...),
    current_user: User = Depends(get_current_user),
):
    """
    更新媒体服务器信息

    - **server_id**: 要更新的服务器ID
    - **data**: 更新的服务器数据
    - **current_user**: 当前已登录用户
    """
    server = await server_controller.update_server(server_id, data.dict())
    return Success(
        data={
            "id": server.id,
            "name": server.name,
            "server_type": server.server_type,
            "base_url": server.base_url,
            "description": server.description,
            "auth_required": server.auth_required,
            "create_time": server.create_time.isoformat(),
            "status": server.status,
        }
    )


@router_strm.delete("/server/{server_id}", summary="删除媒体服务器")
async def delete_media_server(
    server_id: int = Path(..., description="服务器ID"), current_user: User = Depends(get_current_user)
):
    """
    删除媒体服务器

    - **server_id**: 要删除的服务器ID
    - **current_user**: 当前已登录用户
    """
    await server_controller.remove(id=server_id)
    return Success(data={"message": "服务器已成功删除"})


@router_strm.post("/server/{server_id}/test", summary="测试服务器连接")
async def test_server_connection(
    server_id: int = Path(..., description="服务器ID"), current_user: User = Depends(get_current_user)
):
    """
    测试媒体服务器连接

    - **server_id**: 要测试的服务器ID
    - **current_user**: 当前已登录用户
    """
    result = await server_controller.test_connection(server_id)
    return Success(data=result)


@router_strm.post("/server/test", summary="测试未保存的服务器连接")
async def test_server_connection_without_save(
    data: MediaServerBase = Body(...), current_user: User = Depends(get_current_user)
):
    """
    测试未保存的媒体服务器连接

    - **data**: 服务器数据
    - **current_user**: 当前已登录用户
    """
    result = await server_controller.test_connection_without_save(data.dict())
    return Success(data=result)
