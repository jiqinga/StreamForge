"""
媒体服务器控制器，用于管理媒体服务器配置
"""

import httpx
from typing import List, Optional, Dict, Any
import asyncio
import ipaddress
from urllib.parse import urlparse

from app.models.strm import MediaServer, ServerStatus, ServerType, SystemSettings
from app.core.crud import CRUDBase
from app.core.ctx import CTX_USER_ID
from app.log.log import log


class ServerController(CRUDBase):
    """媒体服务器控制器"""

    async def create_server(self, data: Dict[str, Any]) -> MediaServer:
        """
        创建媒体服务器

        Args:
            data: 服务器数据

        Returns:
            创建的服务器对象
        """
        # 获取当前用户ID
        user_id = CTX_USER_ID.get()

        # 如果没有提供状态，设置为未知
        if "status" not in data:
            data["status"] = ServerStatus.UNKNOWN

        # 创建服务器
        server = await MediaServer.create(**data, created_by_id=user_id)

        return server

    async def update_server(self, server_id: int, data: Dict[str, Any]) -> MediaServer:
        """
        更新媒体服务器

        Args:
            server_id: 服务器ID
            data: 更新数据

        Returns:
            更新后的服务器对象
        """
        server = await self.get(id=server_id)

        # 更新服务器
        for field, value in data.items():
            setattr(server, field, value)

        await server.save()

        return server

    async def get_default_server(self) -> Optional[MediaServer]:
        """
        获取默认媒体服务器

        注意: 此方法已废弃，保留是为了兼容现有代码，将始终返回None
        后续版本可能会完全移除此方法

        Returns:
            始终返回None
        """
        log.warning("调用已废弃的get_default_server方法，此方法将在未来版本中移除")
        return None

    async def _is_valid_url(self, url: str) -> bool:
        """
        验证URL是否有效

        Args:
            url: 要验证的URL

        Returns:
            URL是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    async def _is_private_ip(self, hostname: str) -> bool:
        """
        检查主机名是否是私有IP地址

        Args:
            hostname: 主机名或IP地址

        Returns:
            是否是私有IP地址
        """
        try:
            # 尝试将主机名解析为IP地址
            ip = ipaddress.ip_address(hostname)
            return ip.is_private
        except ValueError:
            # 如果不是有效的IP地址，则返回False
            return False

    async def _test_server_connection(self, server_type, base_url, auth_required=False, username=None, password=None):
        """
        内部方法：测试服务器连接核心逻辑

        Args:
            server_type: 服务器类型（枚举或字符串）
            base_url: 服务器基础URL
            auth_required: 是否需要认证
            username: 认证用户名
            password: 认证密码

        Returns:
            (success, message, status) 元组
        """
        success = False
        message = "未知错误"
        status = "error"

        try:
            # 处理服务器类型
            if isinstance(server_type, str):
                server_type_str = server_type.lower()
            else:
                server_type_str = str(server_type).lower()

            # 日志记录测试连接开始
            # log.info(f"开始测试服务器连接 - 类型: {server_type_str}, URL: {base_url}")

            # 检查URL是否为空
            if not base_url or base_url.strip() == "":
                message = "服务器URL不能为空"
                log.warning(f"服务器连接测试失败: {message}")
                return False, message, "error"

            # 检查服务器类型
            is_http = server_type == ServerType.HTTP or (isinstance(server_type, str) and server_type_str == "http")
            is_https = server_type == ServerType.HTTPS or (isinstance(server_type, str) and server_type_str == "https")
            is_cd2host = server_type == ServerType.CD2HOST or (
                isinstance(server_type, str) and server_type_str == "cd2host"
            )
            is_xiaoyahost = server_type == ServerType.XIAOYAHOST or (
                isinstance(server_type, str) and server_type_str == "xiaoyahost"
            )

            # 根据服务器类型进行不同的连接测试
            if is_http or is_https:
                # 对HTTP/HTTPS服务器进行连接测试
                url = base_url
                if not url.startswith(("http://", "https://")):
                    url = f"{'https://' if is_https else 'http://'}{url}"

                # 验证URL格式
                if not await self._is_valid_url(url):
                    message = "无效的URL格式"
                    log.warning(f"服务器连接测试失败: {message}, URL: {url}")
                    return False, message, "error"

                # 设置HTTP客户端
                timeout = 10.0  # 10秒超时
                headers = {}
                auth = None

                # 如果需要认证
                if auth_required and username:
                    auth = (username, password or "")

                log.info(f"尝试连接到HTTP(S)服务器: {url}")
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, headers=headers, auth=auth)
                    response.raise_for_status()

                    success = True
                    message = f"连接成功 (HTTP {response.status_code})"
                    status = "success"
                    log.info(f"成功连接到服务器: {url}, 状态码: {response.status_code}")

            elif is_cd2host:
                # 对CD2HOST服务器进行实际连接测试
                # log.info(f"尝试连接到CD2HOST服务器: {base_url}")

                # 解析URL，确保格式正确
                if not await self._is_valid_url(base_url) and not await self._is_private_ip(base_url):
                    message = "无效的CD2HOST服务器地址"
                    log.warning(f"CD2HOST服务器连接测试失败: {message}")
                    return False, message, "error"

                # 实际测试连接 - 这里假设CD2HOST使用REST API
                url = base_url
                if not url.startswith(("http://", "https://")):
                    url = f"http://{url}"  # 默认使用HTTP

                # 添加API端点路径
                if not url.endswith("/"):
                    url += "/"
                url += "api/status"  # 假设有status API端点

                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(url)
                        if response.is_success:
                            success = True
                            message = "CD2HOST服务器连接成功"
                            status = "success"
                            log.info(f"成功连接到CD2HOST服务器: {base_url}")
                        else:
                            message = f"CD2HOST服务器响应错误: {response.status_code}"
                            log.warning(f"CD2HOST服务器连接测试失败: {message}")
                except Exception as e:
                    message = f"CD2HOST服务器连接错误: {str(e)}"
                    log.warning(f"CD2HOST服务器连接测试失败: {message}")

            elif is_xiaoyahost:
                # 对XIAOYAHOST服务器进行实际连接测试
                # log.info(f"尝试连接到XIAOYAHOST服务器: {base_url}")

                # 解析URL，确保格式正确
                if not await self._is_valid_url(base_url) and not await self._is_private_ip(base_url):
                    message = "无效的XIAOYAHOST服务器地址"
                    log.warning(f"XIAOYAHOST服务器连接测试失败: {message}")
                    return False, message, "error"

                # 实际测试连接 - 这里假设XIAOYAHOST使用REST API
                url = base_url
                if not url.startswith(("http://", "https://")):
                    url = f"http://{url}"  # 默认使用HTTP

                # 添加API端点路径
                if not url.endswith("/"):
                    url += "/"
                url += "api/health"  # 假设有health API端点

                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(url)
                        if response.is_success:
                            success = True
                            message = "XIAOYAHOST服务器连接成功"
                            status = "success"
                            log.info(f"成功连接到XIAOYAHOST服务器: {base_url}")
                        else:
                            message = f"XIAOYAHOST服务器响应错误: {response.status_code}"
                            log.warning(f"XIAOYAHOST服务器连接测试失败: {message}")
                except Exception as e:
                    message = f"XIAOYAHOST服务器连接错误: {str(e)}"
                    log.warning(f"XIAOYAHOST服务器连接测试失败: {message}")

            else:
                # 对于不支持的服务器类型，显示值
                server_type_display = str(server_type)
                if hasattr(server_type, "value"):
                    server_type_display = server_type.value
                message = f"不支持的服务器类型: {server_type_display}"
                status = "warning"
                log.warning(f"不支持的服务器类型: {server_type_display}")

        except httpx.HTTPStatusError as e:
            message = f"HTTP错误 {e.response.status_code}: {e.response.reason_phrase}"
            status = "error"
            log.error(f"HTTP错误: {message}")
        except httpx.RequestError as e:
            message = f"请求错误: {str(e)}"
            status = "error"
            log.error(f"请求错误: {str(e)}")
        except httpx.TimeoutException:
            message = "连接超时"
            status = "error"
            log.error(f"连接超时: {base_url}")
        except Exception as e:
            message = f"连接错误: {str(e)}"
            status = "error"
            log.error(f"连接测试过程中出现未处理的错误: {str(e)}")

        return success, message, status

    async def test_connection_without_save(self, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        测试未保存的服务器连接

        Args:
            server_data: 服务器数据

        Returns:
            测试结果
        """
        # 获取服务器信息
        server_type = server_data.get("server_type", ServerType.HTTP)
        base_url = server_data.get("base_url", "")
        auth_required = server_data.get("auth_required", False)
        username = server_data.get("username")
        password = server_data.get("password")

        # 测试连接
        success, message, status = await self._test_server_connection(
            server_type, base_url, auth_required, username, password
        )

        return {
            "success": success,
            "message": message,
            "status": status,
            "server": {
                "name": server_data.get("name", "未命名服务器"),
                "server_type": server_type,
                "base_url": base_url,
                "description": server_data.get("description"),
                "auth_required": auth_required,
            },
        }

    async def test_connection(self, server_id: int) -> Dict[str, Any]:
        """
        测试服务器连接

        Args:
            server_id: 服务器ID

        Returns:
            测试结果
        """
        server = await self.get(id=server_id)

        # 测试连接
        success, message, status = await self._test_server_connection(
            server.server_type, server.base_url, server.auth_required, server.username, server.password
        )

        # 更新服务器状态并保存到数据库
        server.status = status
        await server.save()

        return {
            "success": success,
            "message": message,
            "status": status,
            "server": {
                "id": server.id,
                "name": server.name,
                "server_type": server.server_type,
                "base_url": server.base_url,
                "description": server.description,
                "auth_required": server.auth_required,
                "status": status,
            },
        }

    async def remove(self, **kwargs) -> None:
        """
        重写基类的remove方法，添加对系统设置的处理逻辑

        Args:
            **kwargs: 查询参数，通常是 id=server_id
        """
        from app.models.strm import SystemSettings
        from app.log.log import log

        # 获取要删除的服务器
        server = await self.get(**kwargs)

        # 检查系统设置中是否存在对该服务器的引用
        settings = await SystemSettings.all().first()
        if settings:
            updated = False

            # 检查默认下载服务器引用
            if settings.default_download_server_id == server.id:
                log.warning(f"删除服务器 {server.name} (ID: {server.id}) 前清除系统设置中的默认下载服务器引用")
                settings.default_download_server_id = None
                updated = True

            # 检查默认媒体服务器引用
            if settings.default_media_server_id == server.id:
                log.warning(f"删除服务器 {server.name} (ID: {server.id}) 前清除系统设置中的默认媒体服务器引用")
                settings.default_media_server_id = None
                updated = True

            # 如果有更新，保存设置
            if updated:
                await settings.save()
                log.info(f"已更新系统设置，移除对即将删除的服务器 {server.name} (ID: {server.id}) 的引用")

        # 调用父类的删除方法
        await super().remove(**kwargs)


# 创建服务器控制器实例
server_controller = ServerController(MediaServer)
