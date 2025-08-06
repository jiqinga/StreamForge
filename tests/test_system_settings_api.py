"""
测试系统设置API接口
"""
import pytest
from httpx import AsyncClient
from app.main import app


class TestSystemSettingsAPI:
    """系统设置API测试"""

    @pytest.mark.asyncio
    async def test_get_settings_with_task_recovery_fields(self):
        """测试获取系统设置是否包含任务恢复配置字段"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 这里需要先登录获取token，简化测试暂时跳过认证
            # 实际测试时需要添加认证头
            response = await client.get("/api/v1/system-manage/settings")
            
            # 检查响应状态
            assert response.status_code == 200
            
            # 检查响应数据结构
            data = response.json()
            assert "code" in data
            assert "data" in data
            
            settings_data = data["data"]
            
            # 检查任务恢复配置字段是否存在
            task_recovery_fields = [
                "enable_task_recovery_periodic_check",
                "task_recovery_check_interval", 
                "task_timeout_hours",
                "heartbeat_timeout_minutes",
                "activity_check_minutes",
                "recent_activity_minutes"
            ]
            
            for field in task_recovery_fields:
                assert field in settings_data, f"缺少任务恢复配置字段: {field}"
            
            # 检查默认值是否正确
            if settings_data.get("id") == 0:  # 默认设置
                assert settings_data["enable_task_recovery_periodic_check"] is True
                assert settings_data["task_recovery_check_interval"] == 1800
                assert settings_data["task_timeout_hours"] == 2
                assert settings_data["heartbeat_timeout_minutes"] == 10
                assert settings_data["activity_check_minutes"] == 30
                assert settings_data["recent_activity_minutes"] == 5


if __name__ == "__main__":
    # 运行测试
    import asyncio
    
    async def run_test():
        test_instance = TestSystemSettingsAPI()
        await test_instance.test_get_settings_with_task_recovery_fields()
        print("✅ 系统设置API测试通过")
    
    asyncio.run(run_test())
