"""
STRM文件上传处理控制器

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

import shutil
import time
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.settings import APP_SETTINGS
from app.utils.strm.parser import TreeParser, parse_directory_tree_sync
from typing import Dict, Any, Union
from app.models.system import User
from app.models.strm.upload import UploadRecord, UploadStatus
from fastapi.responses import FileResponse
import aiofiles
import aiohttp
import re
from app.utils.strm.processor import process_directory_tree
from app.settings import config
import uuid
import tempfile

UPLOAD_DIR = Path(APP_SETTINGS.BASE_DIR) / "strm_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 不再需要生成唯一文件名，因为文件内容直接存储在数据库中


async def handle_file_upload(file: UploadFile, user: User) -> UploadRecord:
    """
    处理文件上传，验证并将文件内容保存至数据库，同时创建上传记录。
    :param file: 上传的文件对象.
    :param user: 当前用户.
    :return: 创建的上传记录对象.
    """
    if not file.filename.endswith(".txt"):
        raise HTTPException(code=400, msg="无效的文件类型, 只支持 .txt 文件。")

    file_size = file.file.seek(0, 2)
    file.file.seek(0)
    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(code=413, msg="文件太大, 超过 10MB。")

    # 读取文件内容到内存
    try:
        file_content = await file.read()
    finally:
        await file.close()

    # 创建上传记录，直接保存文件内容到数据库
    upload_record = await UploadRecord.create(
        filename=file.filename,  # 保存原始文件名，用于显示和下载
        filesize=file_size,
        file_content=file_content,  # 保存文件内容到数据库
        uploader=user,
        status=UploadStatus.UPLOADED,
    )

    return upload_record


async def parse_uploaded_file(record_id: int, user: User) -> Dict[str, Any]:
    """
    解析已上传的文件
    :param record_id: 上传记录的ID
    :param user: 当前用户，用于验证权限
    :return: 解析结果
    """
    # 获取上传记录
    record = await UploadRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(code=404, msg="上传记录不存在")

    # 检查权限，只能解析自己上传的文件
    if record.uploader_id != user.id:
        raise HTTPException(code=403, msg="没有权限解析此记录")

    # 检查文件状态
    if record.status not in [UploadStatus.UPLOADED, UploadStatus.FAILED]:
        raise HTTPException(code=400, msg="文件状态无效")

    # 获取文件内容
    content = None
    if record.file_content:
        content = record.file_content
    elif record.file_path:
        path = Path(record.file_path)
        if path.exists():
            content = path.read_bytes()
        else:
            raise HTTPException(code=404, msg="文件不存在")
    else:
        raise HTTPException(code=404, msg="文件内容不存在")

    # 创建临时文件
    temp_file_path = UPLOAD_DIR / f"temp_{record_id}.txt"

    await record.update_from_dict({"status": UploadStatus.PARSING})
    await record.save()

    # 写入临时文件用于解析
    with temp_file_path.open("wb") as f:
        f.write(content)

    try:
        # 获取系统设置，用于正确识别文件类型
        from app.models.strm import SystemSettings

        settings = await SystemSettings.all().first()

        # 使用系统设置解析文件
        if settings:
            parser = TreeParser(settings)
            print(f"使用系统设置解析文件，记录ID: {record_id}")
            current_settings_version = settings.settings_version
        else:
            # 如果没有系统设置，则使用默认配置
            parser = TreeParser()
            print(f"没有找到系统设置，使用默认配置解析文件，记录ID: {record_id}")
            current_settings_version = 1  # 默认版本号

        parsed_files = parser.parse_file(str(temp_file_path))

        # 添加详细日志，查看文件类型分布
        file_types = {}
        subtitle_files = []

        for f in parsed_files:
            file_type = f["file_type"]
            file_types[file_type] = file_types.get(file_type, 0) + 1

            # 记录所有被识别为字幕的文件
            if file_type == "subtitle":
                subtitle_files.append(f["path"])

        print(f"文件类型统计: {file_types}")
        print(f"字幕文件示例(最多5个): {subtitle_files[:5] if subtitle_files else '无'}")

        # 计算统计信息
        stats = {
            "total": len(parsed_files),
            "video": len([f for f in parsed_files if f["file_type"] == "video"]),
            "audio": len([f for f in parsed_files if f["file_type"] == "audio"]),
            "image": len([f for f in parsed_files if f["file_type"] == "image"]),
            "subtitle": len([f for f in parsed_files if f["file_type"] == "subtitle"]),
            "metadata": len([f for f in parsed_files if f["file_type"] == "metadata"]),
            "other": len([f for f in parsed_files if f["file_type"] == "other"]),
        }

        # 手动修正统计数据，确保与实际文件类型一致
        # 如果没有特定类型的文件，将统计值设为0
        for key in ["video", "audio", "image", "subtitle", "metadata", "other"]:
            if key not in file_types:
                stats[key] = 0

        # 创建完整结果用于存储到数据库，包含设置版本号
        full_result = {
            "file_name": record.filename,  # 使用数据库中保存的原始文件名
            "parsed_files": parsed_files,  # 存储完整的解析结果
            "total_files": len(parsed_files),
            "stats": stats,
            "settings_version": current_settings_version,  # 存储当前系统设置版本号
        }

        # 创建简化结果用于返回给前端，不包含完整的文件列表
        simplified_result = {
            "file_name": record.filename,
            "total_files": len(parsed_files),
            "stats": stats,
            "settings_version": current_settings_version,
            # 返回空的文件列表，避免前端代码需要大量修改
            "parsed_files": [],
        }

        # 更新记录，记录解析时间
        from datetime import datetime

        await record.update_from_dict(
            {"status": UploadStatus.PARSED, "parsed_result": full_result, "parse_time": datetime.now()}
        )
        await record.save()

        # 解析完成后删除临时文件
        if temp_file_path.exists():
            temp_file_path.unlink()

        # 返回简化结果给前端
        return simplified_result
    except Exception as e:
        await record.update_from_dict({"status": UploadStatus.FAILED})
        await record.save()

        # 发生错误时也删除临时文件
        if temp_file_path.exists():
            temp_file_path.unlink()

        raise HTTPException(code=500, msg=f"解析文件失败: {str(e)}")


async def delete_upload_record(record_id: int, user: User) -> None:
    """
    删除上传记录
    :param record_id: 上传记录的ID
    :param user: 当前用户，用于验证权限
    :return: None
    """
    # 获取上传记录
    record = await UploadRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(code=404, msg="上传记录不存在")

    # 检查权限，只能删除自己上传的文件
    if record.uploader_id != user.id:
        raise HTTPException(code=403, msg="没有权限删除此记录")

    # 处理旧记录：尝试删除物理文件（如果存在）
    if record.file_path:
        file_path = Path(record.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                # 如果文件删除失败，记录错误但继续删除数据库记录
                print(f"删除文件失败: {str(e)}")

    # 删除数据库记录
    await record.delete()


from fastapi.responses import Response


async def download_upload_file(record_id: int, user: User) -> Response:
    """
    下载已上传的文件
    :param record_id: 上传记录的ID
    :param user: 当前用户，用于验证权限
    :return: 文件响应
    """
    # 获取上传记录
    record = await UploadRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(code=404, msg="上传记录不存在")

    # 检查权限，只能下载自己上传的文件
    if record.uploader_id != user.id:
        raise HTTPException(code=403, msg="没有权限下载此文件")

    # 获取文件内容
    try:
        # 首先尝试从数据库中获取文件内容
        if record.file_content is not None:
            content = record.file_content
        # 如果数据库中没有文件内容，但有file_path，则尝试从文件系统读取
        elif record.file_path:
            file_path = Path(record.file_path)
            if file_path.exists():
                content = file_path.read_bytes()
            else:
                raise HTTPException(code=404, msg=f"文件不存在于指定路径: {record.file_path}")
        else:
            raise HTTPException(code=404, msg="文件内容不存在于数据库且未指定文件路径")
    except Exception as e:
        # 捕获所有可能的异常并提供更详细的错误信息
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(code=500, msg=f"获取文件内容时出错: {str(e)}")

    # 返回文件响应
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


async def get_parse_result(
    record_id: int, user: User, file_type: str = "all", page: int = 1, page_size: int = 10, all_files: bool = False
) -> Dict[str, Any]:
    """
    获取已解析文件的解析结果，支持按文件类型过滤和分页

    判断文件/目录的逻辑：
    - 以斜杠（/）结尾的路径被视为目录
    - 不以斜杠结尾的路径被视为文件

    :param record_id: 上传记录的ID
    :param user: 当前用户，用于验证权限
    :param file_type: 文件类型过滤器 (all, video, audio, image, subtitle, metadata, other)
    :param page: 页码
    :param page_size: 每页数量
    :param all_files: 是否获取所有文件（不分页）
    :return: 包含过滤和分页后的解析结果
    """
    # 获取上传记录
    record = await UploadRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(code=404, msg="上传记录不存在")

    # 检查权限，只能查看自己上传的文件的解析结果
    # if record.uploader_id != user.id:
    #     raise HTTPException(code=403, msg="没有权限查看此记录")

    # 检查文件状态
    if record.status != UploadStatus.PARSED:
        raise HTTPException(code=400, msg="文件尚未成功解析")

    # 检查并返回解析结果
    if not record.parsed_result:
        raise HTTPException(code=404, msg="解析结果不存在")

    # 导入check_and_update_parse_result函数
    from app.utils.strm.parser import check_and_update_parse_result

    # 检查并更新解析结果，如有需要
    updated, current_result = await check_and_update_parse_result(record)

    # 复制解析结果，不修改当前结果
    result = dict(current_result)

    # 获取所有文件
    parsed_files = result.get("parsed_files", [])

    # 根据文件类型进行过滤
    if file_type != "all":
        # 过滤指定类型的文件
        filtered_files = [f for f in parsed_files if f.get("file_type") == file_type]
        # 使用结果中的stats数据作为总数
        total_count = result.get("stats", {}).get(file_type, 0)
    else:
        # 所有文件
        filtered_files = parsed_files
        total_count = result.get("stats", {}).get("total", len(parsed_files))

    # 计算分页 - 如果all_files参数为True，则不进行分页
    if all_files:
        paginated_files = filtered_files
    else:
        start = (page - 1) * page_size
        end = min(start + page_size, len(filtered_files))
        paginated_files = filtered_files[start:end] if start < len(filtered_files) else []

    # 处理文件路径，确保文件路径不以斜杠结尾，而目录路径以斜杠结尾
    for item in paginated_files:
        # 使用路径是否以斜杠结尾判断是否为目录
        is_directory = item.get("path", "").endswith("/")

        # 更新is_directory属性
        item["is_directory"] = is_directory

        # 设置相应的属性
        if is_directory:
            item["file_type"] = "directory"
            item["mime_type"] = "directory"
            # 确保目录路径以斜杠结尾
            if "path" in item and not item["path"].endswith("/"):
                item["path"] = item["path"] + "/"
        else:
            # 确保文件路径不以斜杠结尾
            if "path" in item and item["path"].endswith("/"):
                item["path"] = item["path"].rstrip("/")

    # 更新结果
    result["parsed_files"] = paginated_files
    result["pagination"] = {
        "page": page,
        "page_size": page_size,
        "total": total_count,
    }

    # 添加版本检查更新信息
    result["version_check_update"] = {
        "applied": updated,
        "current_version": result.get("settings_version", 1),
    }

    return result


async def handle_url_upload(url: str, user: User) -> UploadRecord:
    """
    从URL下载并处理115目录树文件
    :param url: 文件的URL地址
    :param user: 当前用户，上传者
    :return: 上传记录对象
    """
    from app.log.log import log

    if not url or not isinstance(url, str):
        log.warning(f"无效的URL: {url}")
        raise HTTPException(code=400, msg="无效的URL")

    # 提取文件名
    filename = get_filename_from_url(url)
    if not filename or not filename.lower().endswith(".txt"):
        filename = f"downloaded_{uuid.uuid4().hex}.txt"

    log.info(f"开始从URL下载文件: {url}, 将保存为: {filename}")

    temp_path = None
    try:
        # 创建临时文件用于下载
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
                temp_path = temp_file.name
            log.info(f"创建临时文件: {temp_path}")
        except Exception as e:
            log.error(f"创建临时文件失败: {str(e)}")
            raise HTTPException(code=500, msg=f"创建临时文件失败: {str(e)}")

        # 从URL下载文件
        try:
            file_size = await download_file(url, temp_path)
            log.info(f"文件下载完成, 大小: {file_size} 字节")
        except HTTPException as he:
            log.error(f"下载文件时遇到HTTP错误: {he.msg}")
            raise
        except Exception as e:
            log.error(f"下载文件失败: {str(e)}", exc_info=True)
            raise HTTPException(code=500, msg=f"下载文件失败: {str(e)}")

        if file_size <= 0:
            log.error(f"下载的文件大小异常: {file_size} 字节")
            raise HTTPException(code=400, msg="下载文件大小为0或下载失败")

        # 读取下载的文件内容
        try:
            async with aiofiles.open(temp_path, "rb") as f:
                file_content = await f.read()
            log.info(f"成功读取文件内容, 大小: {len(file_content)} 字节")
        except Exception as e:
            log.error(f"读取下载文件内容失败: {str(e)}", exc_info=True)
            raise HTTPException(code=500, msg=f"读取下载文件内容失败: {str(e)}")

        # 创建上传记录
        try:
            record = UploadRecord(
                filename=filename,
                file_path=None,  # 不保存临时文件路径，因为它会被删除
                filesize=file_size,
                file_content=file_content,  # 保存文件内容到数据库
                uploader=user,
                status=UploadStatus.UPLOADED,
            )
            await record.save()
            log.info(f"成功创建上传记录, ID: {record.id}")
        except Exception as e:
            log.error(f"保存上传记录到数据库失败: {str(e)}", exc_info=True)
            raise HTTPException(code=500, msg=f"保存上传记录到数据库失败: {str(e)}")

        # 处理完成后删除临时文件
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
                log.info(f"成功删除临时文件: {temp_path}")
        except Exception as e:
            log.warning(f"删除临时文件失败: {str(e)}")

        return record

    except Exception as e:
        # 确保临时文件被删除
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
                log.info(f"异常处理中删除临时文件: {temp_path}")
        except Exception as cleanup_error:
            log.warning(f"清理临时文件失败: {str(cleanup_error)}")

        # 记录详细错误信息
        if isinstance(e, HTTPException):
            log.error(f"URL上传处理中的HTTP异常: {e.msg}, 状态码: {e.code}")
            raise
        else:
            log.error(f"URL上传处理中的未知异常: {str(e)}", exc_info=True)
            raise HTTPException(code=500, msg=f"从URL上传文件失败: {str(e)}")


async def download_file(url: str, destination: str) -> int:
    """
    从URL下载文件到指定路径
    :param url: 文件URL
    :param destination: 保存路径
    :return: 下载的文件大小
    """
    from app.log.log import log

    log.info(f"开始从URL下载文件: {url} 到路径: {destination}")

    try:
        # 设置合理的超时时间和重试策略
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                log.info(f"发送HTTP GET请求到: {url}")
                async with session.get(url) as response:
                    log.info(
                        f"收到响应，状态码: {response.status}, 内容类型: {response.headers.get('Content-Type', '未知')}"
                    )

                    if response.status != 200:
                        log.error(f"下载失败：HTTP状态码 {response.status}, URL: {url}")
                        raise HTTPException(
                            code=response.status,
                            msg=f"下载文件失败，HTTP状态码: {response.status}, 响应: {await response.text()[:200]}",
                        )

                    # 检查内容类型，对非文本文件给出警告
                    content_type = response.headers.get("Content-Type", "").lower()
                    if content_type and "text/plain" not in content_type and "text" not in content_type:
                        log.warning(f"下载的文件可能不是文本文件，内容类型: {content_type}")

                    # 获取内容长度
                    content_length = response.headers.get("Content-Length")
                    if content_length:
                        log.info(f"预期下载文件大小: {content_length} 字节")

                    log.info(f"开始读取响应内容")
                    content = await response.read()
                    log.info(f"成功读取响应内容，大小: {len(content)} 字节")

                    # 写入文件
                    try:
                        log.info(f"开始将内容写入文件: {destination}")
                        async with aiofiles.open(destination, "wb") as f:
                            await f.write(content)
                        log.info(f"成功将内容写入文件: {destination}")
                    except Exception as write_error:
                        log.error(f"写入文件失败: {str(write_error)}", exc_info=True)
                        raise HTTPException(code=500, msg=f"写入下载内容到文件失败: {str(write_error)}")

                    return len(content)
            except aiohttp.ClientResponseError as e:
                log.error(f"HTTP响应错误: {str(e)}, URL: {url}", exc_info=True)
                raise HTTPException(code=e.status, msg=f"HTTP响应错误: {str(e)}")
            except aiohttp.ClientConnectionError as e:
                log.error(f"连接服务器失败: {str(e)}, URL: {url}", exc_info=True)
                raise HTTPException(code=503, msg=f"连接服务器失败: {str(e)}")
            except aiohttp.ClientPayloadError as e:
                log.error(f"下载内容错误: {str(e)}, URL: {url}", exc_info=True)
                raise HTTPException(code=500, msg=f"下载内容错误: {str(e)}")
            except aiohttp.ClientError as e:
                log.error(f"HTTP客户端错误: {str(e)}, URL: {url}", exc_info=True)
                raise HTTPException(code=400, msg=f"下载文件失败: {str(e)}")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        log.error(f"下载文件时发生未知错误: {str(e)}, URL: {url}", exc_info=True)
        raise HTTPException(code=500, msg=f"下载文件时发生未知错误: {str(e)}")


def get_filename_from_url(url: str) -> str:
    """
    从URL中提取文件名
    :param url: 文件URL
    :return: 文件名
    """
    try:
        # 尝试从URL路径中提取文件名
        from urllib.parse import urlparse, unquote

        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)

        # 提取路径中的最后一部分作为文件名
        filename = os.path.basename(path)

        if filename:
            return filename

        # 如果无法从路径提取，生成随机文件名
        return f"file_{uuid.uuid4().hex}.txt"
    except:
        return f"file_{uuid.uuid4().hex}.txt"


async def get_directory_content(
    record_id: int,
    user: User,
    path: str = "/",
    file_type: str = "all",
    page: int = 1,
    page_size: int = 20,
    recursive: bool = False,
) -> Dict[str, Any]:
    """
    获取目录内容

    判断文件/目录的逻辑：
    - 以斜杠（/）结尾的路径被视为目录
    - 不以斜杠结尾的路径被视为文件

    :param record_id: 上传记录的ID
    :param user: 当前用户，用于验证权限
    :param path: 目录路径（相对于根目录）
    :param file_type: 文件类型过滤器 (all, video, audio, image, subtitle, metadata, other)
    :param page: 页码
    :param page_size: 每页数量
    :param recursive: 是否递归获取所有子目录内容
    :return: 目录内容
    """
    # 获取上传记录
    record = await UploadRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(code=404, msg="上传记录不存在")

    # 检查权限，只能查看自己上传的文件的解析结果
    if record.uploader_id != user.id:
        raise HTTPException(code=403, msg="没有权限查看此记录")

    # 检查文件状态
    if record.status != UploadStatus.PARSED:
        raise HTTPException(code=400, msg="文件尚未成功解析")

    # 检查解析结果是否存在
    if not record.parsed_result or "parsed_files" not in record.parsed_result:
        raise HTTPException(code=404, msg="解析结果不存在")

    # 导入check_and_update_parse_result函数进行版本检查
    from app.utils.strm.parser import check_and_update_parse_result

    # 检查并更新解析结果，如有需要
    updated, current_result = await check_and_update_parse_result(record)

    # 获取所有文件
    all_files = current_result.get("parsed_files", [])

    # 规范化路径
    normalized_path = path.strip("/")
    if normalized_path:
        normalized_path = "/" + normalized_path + "/"
    else:
        normalized_path = "/"

    # 查找指定目录下的所有文件和子目录
    if recursive:
        # 递归模式: 获取指定路径及其所有子路径下的文件
        if normalized_path == "/":
            # 根目录，获取所有文件
            filtered_items = all_files
        else:
            # 获取指定目录及其子目录下的所有文件
            filtered_items = [f for f in all_files if f.get("path", "").startswith(normalized_path)]
    else:
        # 非递归模式: 只获取指定路径下的直接文件和子目录
        filtered_items = []
        directories = set()

        for file in all_files:
            file_path = file.get("path", "")

            # 检查文件是否在指定目录下
            if file_path.startswith(normalized_path):
                remaining_path = file_path[len(normalized_path) :].strip("/")

                if not remaining_path:
                    # 文件直接位于当前目录
                    filtered_items.append(file)
                else:
                    # 检查是否有子目录
                    if "/" in remaining_path:
                        # 有子目录，添加第一级子目录
                        sub_dir = remaining_path.split("/")[0]
                        if sub_dir:
                            directories.add(sub_dir)
                    else:
                        # 这是直接位于当前目录下的文件
                        filtered_items.append(file)

        # 添加子目录到结果中
        for dir_name in directories:
            dir_path = normalized_path + dir_name + "/"
            filtered_items.append({"file_name": dir_name, "path": dir_path, "is_directory": True})

    # 如果指定了文件类型筛选，则过滤结果
    if file_type != "all":
        filtered_items = [
            item for item in filtered_items if item.get("file_type") == file_type or item.get("is_directory", False)
        ]

    # 计算总数
    total = len(filtered_items)

    # 分页
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    paginated_items = filtered_items[start:end] if start < total else []

    # 处理文件路径，使其符合前端展示要求
    for item in paginated_items:
        # 使用路径是否以斜杠结尾判断是否为目录
        is_directory = item.get("path", "").endswith("/")

        # 更新is_directory属性
        item["is_directory"] = is_directory

        # 设置相应的属性
        if is_directory:
            item["file_type"] = "directory"
            item["mime_type"] = "directory"
            # 确保目录路径以斜杠结尾
            if "path" in item and not item["path"].endswith("/"):
                item["path"] = item["path"] + "/"
        else:
            # 确保文件路径不以斜杠结尾
            if "path" in item and item["path"].endswith("/"):
                item["path"] = item["path"].rstrip("/")

        # 确保path属性存在
        if "path" not in item:
            item["path"] = "/"

    # 构建返回结果
    return {
        "path": normalized_path,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paginated_items,
        "file_type": file_type,
        "updated_by_version_check": updated,  # 添加标识，表明是否因版本检查而更新
    }


async def search_files(
    record_id: int,
    user: User,
    query: str = "",
    file_type: str = "all",
    page: int = 1,
    page_size: int = 20,
    path: str = "/",
) -> Dict[str, Any]:
    """
    搜索文件

    判断文件/目录的逻辑：
    - 以斜杠（/）结尾的路径被视为目录
    - 不以斜杠结尾的路径被视为文件

    :param record_id: 上传记录的ID
    :param user: 当前用户，用于验证权限
    :param query: 搜索关键字
    :param file_type: 文件类型过滤器 (all, video, audio, image, subtitle, metadata, other)
    :param page: 页码
    :param page_size: 每页数量
    :param path: 搜索路径限制，默认搜索所有路径
    :return: 搜索结果
    """
    # 获取上传记录
    record = await UploadRecord.get_or_none(id=record_id)
    if not record:
        raise HTTPException(code=404, msg="上传记录不存在")

    # 检查权限，只能查看自己上传的文件的解析结果
    if record.uploader_id != user.id:
        raise HTTPException(code=403, msg="没有权限查看此记录")

    # 检查文件状态
    if record.status != UploadStatus.PARSED:
        raise HTTPException(code=400, msg="文件尚未成功解析")

    # 检查解析结果是否存在
    if not record.parsed_result or "parsed_files" not in record.parsed_result:
        raise HTTPException(code=404, msg="解析结果不存在")

    # 导入check_and_update_parse_result函数进行版本检查
    from app.utils.strm.parser import check_and_update_parse_result

    # 检查并更新解析结果，如有需要
    updated, current_result = await check_and_update_parse_result(record)

    # 获取所有文件
    all_files = current_result.get("parsed_files", [])

    # 规范化路径
    normalized_path = path.strip("/")
    if normalized_path:
        normalized_path = "/" + normalized_path + "/"
    else:
        normalized_path = "/"

    # 过滤路径
    if normalized_path != "/":
        path_filtered_files = [f for f in all_files if f.get("path", "").startswith(normalized_path)]
    else:
        path_filtered_files = all_files

    # 过滤文件类型
    if file_type != "all":
        type_filtered_files = [f for f in path_filtered_files if f.get("file_type") == file_type]
    else:
        type_filtered_files = path_filtered_files

    # 搜索匹配
    query = query.lower()
    if query:
        matched_files = []
        for file in type_filtered_files:
            # 检查文件名和路径是否包含搜索关键字
            file_name = file.get("file_name", "").lower()
            file_path = file.get("path", "").lower()

            if query in file_name or query in file_path:
                matched_files.append(file)
    else:
        # 无搜索关键字时返回所有匹配的文件类型
        matched_files = type_filtered_files

    # 计算总数
    total = len(matched_files)

    # 分页
    start = (page - 1) * page_size
    end = min(start + page_size, total)
    paginated_files = matched_files[start:end] if start < total else []

    # 处理文件路径，使其符合前端展示要求
    for item in paginated_files:
        # 使用路径是否以斜杠结尾判断是否为目录
        is_directory = item.get("path", "").endswith("/")

        # 更新is_directory属性
        item["is_directory"] = is_directory

        # 设置相应的属性
        if is_directory:
            item["file_type"] = "directory"
            item["mime_type"] = "directory"
            # 确保目录路径以斜杠结尾
            if "path" in item and not item["path"].endswith("/"):
                item["path"] = item["path"] + "/"
        else:
            # 确保文件路径不以斜杠结尾
            if "path" in item and item["path"].endswith("/"):
                item["path"] = item["path"].rstrip("/")

    # 返回结果
    return {
        "query": query,
        "file_type": file_type,
        "path": normalized_path,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paginated_files,
        "updated_by_version_check": updated,  # 添加标识，表明是否因版本检查而更新
    }
