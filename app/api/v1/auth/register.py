#!/usr/bin/env python
# encoding: utf-8
'''
Author              : 寂情啊
Date                : 2025-05-30 17:22:31
LastEditors         : 寂情啊
LastEditTime        : 2025-05-30 17:23:03
FilePath            : fast-soy-adminappapiv1authregister.py
Description         : 说明
倾尽绿蚁花尽开，问潭底剑仙安在哉
'''
from fastapi import APIRouter, Body

from app.api.v1.utils import insert_log
from app.controllers.user import user_controller
from app.models.system import LogType, LogDetailType, Role
from app.schemas.base import Fail, Success
from app.schemas.users import UserRegister
from app.log import log

router = APIRouter()


@router.post("/register", summary="用户注册")
async def user_register(user_in: UserRegister):
    """
    用户注册API
    
    参数:
    - user_in: 用户注册信息，包括用户名、密码等
    
    返回:
    - 成功: 返回成功信息和用户ID
    - 失败: 返回错误信息
    """
    # 检查用户名是否已存在
    user_obj = await user_controller.get_by_username(user_in.user_name)
    if user_obj:
        log.info(f"用户注册失败，用户名已存在: {user_in.user_name}")
        return Fail(code="4090", msg="此用户名已被使用")
    
    # 检查邮箱是否已存在（如果提供了邮箱）
    if user_in.user_email:
        user_email_obj = await user_controller.get_by_email(user_in.user_email)
        if user_email_obj:
            log.info(f"用户注册失败，邮箱已存在: {user_in.user_email}")
            return Fail(code="4090", msg="此邮箱已被使用")
    
    # 创建用户
    new_user = await user_controller.create(obj_in=user_in)
    
    # 分配普通用户角色（R_USER）
    user_role = await Role.filter(role_code="R_USER").first()
    if user_role:
        await user_controller.update_roles_by_code(new_user, ["R_USER"])
    else:
        log.error(f"分配角色失败，普通用户角色(R_USER)不存在")
        
    # 记录日志
    await insert_log(log_type=LogType.UserLog, log_detail_type=LogDetailType.UserRegister, by_user_id=new_user.id)
    
    log.info(f"用户注册成功，用户名: {user_in.user_name}")
    return Success(msg="注册成功", data={"userId": new_user.id}) 