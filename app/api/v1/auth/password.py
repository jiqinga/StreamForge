from fastapi import APIRouter, Body, Depends, HTTPException
from datetime import datetime, timedelta
import secrets
import string

from app.api.v1.utils import insert_log
from app.controllers.user import user_controller
from app.core.dependency import DependAuth
from app.core.ctx import CTX_USER_ID
from app.models.system import LogType, LogDetailType
from app.schemas.base import Fail, Success
from app.schemas.users import UpdatePassword
from app.utils.security import verify_password, get_password_hash
from app.log import log

router = APIRouter()

# 模拟验证码存储 - 在实际生产环境中应该使用Redis等缓存
reset_codes = {}


@router.post("/send-reset-code", summary="发送密码重置验证码")
async def send_reset_code(email: str = Body(..., embed=True)):
    """
    发送密码重置验证码
    
    参数:
    - email: 用户注册的邮箱
    
    返回:
    - 成功: 返回成功信息
    - 失败: 返回错误信息
    """
    # 检查邮箱是否存在
    user = await user_controller.get_by_email(email)
    if not user:
        # 出于安全考虑，即使邮箱不存在也返回成功，避免邮箱枚举攻击
        log.info(f"请求密码重置验证码，但邮箱不存在: {email}")
        return Success(msg="验证码已发送，请检查您的邮箱")
    
    # 生成6位随机验证码
    code = ''.join(secrets.choice(string.digits) for _ in range(6))
    
    # 保存验证码（过期时间10分钟）
    expiry = datetime.now() + timedelta(minutes=10)
    reset_codes[email] = {"code": code, "expiry": expiry}
    
    # TODO: 实际发送邮件的代码（当前仅记录日志）
    log.info(f"为邮箱 {email} 生成密码重置验证码: {code}")
    
    # 记录日志
    await insert_log(log_type=LogType.UserLog, log_detail_type=LogDetailType.UserResetPasswordSendCode, by_user_id=user.id)
    
    return Success(msg="验证码已发送，请检查您的邮箱")


@router.post("/reset-password", summary="重置密码")
async def reset_password(
    email: str = Body(...),
    code: str = Body(...),
    new_password: str = Body(...)
):
    """
    重置密码
    
    参数:
    - email: 用户邮箱
    - code: 验证码
    - new_password: 新密码
    
    返回:
    - 成功: 返回成功信息
    - 失败: 返回错误信息
    """
    # 检查邮箱是否存在
    user = await user_controller.get_by_email(email)
    if not user:
        return Fail(code="4040", msg="邮箱不存在")
    
    # 验证验证码
    if email not in reset_codes:
        return Fail(code="4040", msg="验证码无效或已过期")
    
    reset_info = reset_codes[email]
    if reset_info["expiry"] < datetime.now():
        # 验证码过期，删除它
        del reset_codes[email]
        return Fail(code="4040", msg="验证码已过期")
    
    if reset_info["code"] != code:
        return Fail(code="4040", msg="验证码错误")
    
    # 更新密码
    user.password = get_password_hash(new_password)
    await user.save()
    
    # 删除验证码
    del reset_codes[email]
    
    # 记录日志
    await insert_log(log_type=LogType.UserLog, log_detail_type=LogDetailType.UserResetPasswordSuccess, by_user_id=user.id)
    
    log.info(f"用户 {user.user_name} 密码重置成功")
    return Success(msg="密码重置成功")


@router.post("/update-password", summary="修改密码", dependencies=[DependAuth])
async def update_password(password_in: UpdatePassword):
    """
    修改当前用户密码
    
    参数:
    - password_in: 包含旧密码和新密码的对象
    
    返回:
    - 成功: 返回成功信息
    - 失败: 返回错误信息
    """
    user_id = CTX_USER_ID.get()
    user = await user_controller.get(id=user_id)
    
    # 验证旧密码
    if not verify_password(password_in.old_password, user.password):
        await insert_log(log_type=LogType.UserLog, log_detail_type=LogDetailType.UserUpdatePasswordFail, by_user_id=user_id)
        return Fail(code="4040", msg="旧密码错误")
    
    # 更新密码
    user.password = get_password_hash(password_in.new_password)
    await user.save()
    
    # 记录日志
    await insert_log(log_type=LogType.UserLog, log_detail_type=LogDetailType.UserUpdatePasswordSuccess, by_user_id=user_id)
    
    log.info(f"用户 {user.user_name} 修改密码成功")
    return Success(msg="密码修改成功") 