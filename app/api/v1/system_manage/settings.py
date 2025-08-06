#!/usr/bin/env python
# encoding: utf-8
"""
Author              : 寂情啊
Date                : 2025-06-18 17:24:04
LastEditors         : 寂情啊
LastEditTime        : 2025-07-01 15:25:15
FilePath            : fast-soy-adminappapiv1system_managesettings.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
"""

#!/usr/bin/env python
# encoding: utf-8
"""
Author              : 寂情啊
Date                : 2025-06-18 17:24:04
LastEditors         : 寂情啊
LastEditTime        : 2025-06-30 10:41:46
FilePath            : fast-soy-adminappapiv1system_managesettings.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
"""

#!/usr/bin/env python
# encoding: utf-8
"""
Author              : 寂情啊
Date                : 2025-06-18 17:24:04
LastEditors         : 寂情啊
LastEditTime        : 2025-06-30 10:40:17
FilePath            : fast-soy-adminappapiv1system_managesettings.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
"""

#!/usr/bin/env python
# encoding: utf-8
"""
Author              : 寂情啊
Date                : 2025-06-18 17:24:04
LastEditors         : 寂情啊
LastEditTime        : 2025-06-30 09:28:22
FilePath            : fast-soy-adminappapiv1system_managesettings.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
"""

#!/usr/bin/env python
# encoding: utf-8
"""
Author              : 寂情啊
Date                : 2025-06-18 17:24:04
LastEditors         : 寂情啊
LastEditTime        : 2025-06-27 16:47:04
FilePath            : fast-soy-adminappapiv1system_managesettings.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
"""

#!/usr/bin/env python
# encoding: utf-8
"""
Author              : 寂情啊
Date                : 2025-06-18 17:24:04
LastEditors         : 寂情啊
LastEditTime        : 2025-06-27 16:25:03
FilePath            : fast-soy-adminappapiv1system_managesettings.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
"""

from fastapi import APIRouter, Depends, Body
from app.core.dependency import get_current_user
from app.models.system import User
from app.schemas.base import Success
from app.schemas.strm.schemas import SystemSettingsUpdate, SystemSettingsResponse
from app.controllers.strm import system_settings_controller
from datetime import datetime

router = APIRouter()


@router.get("/settings", summary="获取系统设置", response_model=SystemSettingsResponse)
async def get_system_settings(current_user: User = Depends(get_current_user)):
    """
    获取系统设置。如果设置不存在，则返回默认设置。

    - **current_user**: 当前登录用户，必须拥有管理权限。
    """
    settings = await system_settings_controller.get_settings()
    if not settings:
        # 返回默认设置，而不是空对象
        return Success(
            data={
                "id": 0,
                "default_download_server_id": None,
                "default_download_server": None,
                "default_media_server_id": None,
                "default_media_server": None,
                "enable_path_replacement": True,
                "replacement_path": "/nas",
                "download_threads": 1,
                "output_directory": "strm_output",
                "video_file_types": "mp4,mkv,avi,mov,wmv,flv,mpg,mpeg,m4v,ts,m2ts",
                "audio_file_types": "mp3,flac,wav,aac,ogg,m4a,wma,ape",
                "image_file_types": "jpg,jpeg,png,gif,bmp,webp,tiff,svg",
                "subtitle_file_types": "srt,ass,ssa,vtt,sub,idx",
                "metadata_file_types": "nfo,xml,json,txt",
                # 任务恢复配置默认值
                "enable_task_recovery_periodic_check": True,
                "task_recovery_check_interval": 1800,
                "task_timeout_hours": 2,
                "heartbeat_timeout_minutes": 10,
                "activity_check_minutes": 30,
                "recent_activity_minutes": 5,
                "failure_retry_count": 3,
                "retry_interval_seconds": 30,
                # 日志配置默认值
                "enable_sql_logging": False,
                "log_level": "INFO",
                "logs_directory": "app/logs",
                "update_time": datetime.now(),
                "settings_version": 1,
            }
        )
    return Success(data=settings)


@router.post("/settings", summary="更新系统设置", response_model=SystemSettingsResponse)
async def update_system_settings(
    current_user: User = Depends(get_current_user), data: SystemSettingsUpdate = Body(...)
):
    """
    更新系统设置。如果设置不存在，则创建新设置。

    - **current_user**: 当前登录用户，必须拥有管理权限。
    - **data**: 要更新的设置数据。
    """
    settings = await system_settings_controller.create_or_update_settings(data.dict(exclude_none=True))
    return Success(data=settings)
