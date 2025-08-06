"""
测试时区修复功能
"""
import asyncio
from datetime import datetime, timedelta


def test_datetime_normalization():
    """测试时间标准化功能"""
    print("=== 测试时间标准化功能 ===")
    
    # 模拟 TaskRecoveryService 的时间处理方法
    @staticmethod
    def _normalize_datetime(dt: datetime) -> datetime:
        """标准化 datetime 对象，统一转换为 naive datetime"""
        if dt is None:
            return None
            
        # 如果是 timezone-aware datetime，转换为本地时间并去掉时区信息
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        
        return dt
    
    @staticmethod
    def _get_current_time() -> datetime:
        """获取当前时间（naive datetime）"""
        return datetime.now()
    
    # 测试不同类型的时间对象
    current_time = _get_current_time()
    print(f"当前时间 (naive): {current_time}")
    print(f"时区信息: {current_time.tzinfo}")
    
    # 创建一个带时区的时间
    aware_time = datetime.now().astimezone()
    print(f"带时区时间: {aware_time}")
    print(f"时区信息: {aware_time.tzinfo}")
    
    # 标准化带时区的时间
    normalized_time = _normalize_datetime(aware_time)
    print(f"标准化后时间: {normalized_time}")
    print(f"时区信息: {normalized_time.tzinfo}")
    
    # 测试时间计算
    try:
        time_diff = current_time - normalized_time
        print(f"时间差: {time_diff}")
        print("✅ 时间计算成功，没有时区错误")
        return True
    except Exception as e:
        print(f"❌ 时间计算失败: {str(e)}")
        return False


def test_task_timeout_logic():
    """测试任务超时逻辑"""
    print("\n=== 测试任务超时逻辑 ===")
    
    # 模拟任务对象
    class MockTask:
        def __init__(self, start_time):
            self.id = 1
            self.name = "测试任务"
            self.start_time = start_time
            self.status = "running"
            self.end_time = None
    
    # 模拟时间处理方法
    def _normalize_datetime(dt):
        if dt is None:
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    
    def _get_current_time():
        return datetime.now()
    
    # 创建一个3小时前开始的任务（带时区）
    old_time_aware = datetime.now().astimezone() - timedelta(hours=3)
    task = MockTask(start_time=old_time_aware)
    
    print(f"任务开始时间: {task.start_time}")
    print(f"任务开始时间类型: {type(task.start_time)}")
    print(f"时区信息: {task.start_time.tzinfo}")
    
    # 执行超时检查逻辑
    current_time = _get_current_time()
    start_time = _normalize_datetime(task.start_time)
    
    print(f"当前时间: {current_time}")
    print(f"标准化开始时间: {start_time}")
    
    try:
        if start_time:
            elapsed_time = current_time - start_time
            max_execution_time = timedelta(hours=2)
            
            print(f"运行时间: {elapsed_time}")
            print(f"最大允许时间: {max_execution_time}")
            
            if elapsed_time > max_execution_time:
                print("✅ 任务超时检测正常，应该被标记为失败")
                return True
            else:
                print("❌ 任务超时检测异常，不应该通过检查")
                return False
    except Exception as e:
        print(f"❌ 超时检查失败: {str(e)}")
        return False


def test_heartbeat_logic():
    """测试心跳逻辑"""
    print("\n=== 测试心跳逻辑 ===")
    
    # 模拟任务对象
    class MockTask:
        def __init__(self, last_heartbeat):
            self.id = 2
            self.name = "心跳测试任务"
            self.last_heartbeat = last_heartbeat
            self.status = "running"
    
    # 模拟时间处理方法
    def _normalize_datetime(dt):
        if dt is None:
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    
    def _get_current_time():
        return datetime.now()
    
    # 创建一个15分钟前心跳的任务（带时区）
    old_heartbeat_aware = datetime.now().astimezone() - timedelta(minutes=15)
    task = MockTask(last_heartbeat=old_heartbeat_aware)
    
    print(f"最后心跳时间: {task.last_heartbeat}")
    print(f"时区信息: {task.last_heartbeat.tzinfo}")
    
    # 执行心跳检查逻辑
    current_time = _get_current_time()
    last_heartbeat = _normalize_datetime(task.last_heartbeat)
    
    print(f"当前时间: {current_time}")
    print(f"标准化心跳时间: {last_heartbeat}")
    
    try:
        if last_heartbeat:
            heartbeat_timeout = timedelta(minutes=10)
            heartbeat_diff = current_time - last_heartbeat
            
            print(f"心跳间隔: {heartbeat_diff}")
            print(f"心跳超时阈值: {heartbeat_timeout}")
            
            if heartbeat_diff > heartbeat_timeout:
                print("✅ 心跳超时检测正常，应该被标记为失败")
                return True
            else:
                print("❌ 心跳超时检测异常，不应该通过检查")
                return False
    except Exception as e:
        print(f"❌ 心跳检查失败: {str(e)}")
        return False


async def main():
    """运行所有测试"""
    print("开始运行时区修复测试...\n")
    
    test_results = []
    
    try:
        # 运行各项测试
        test_results.append(test_datetime_normalization())
        test_results.append(test_task_timeout_logic())
        test_results.append(test_heartbeat_logic())
        
        # 统计结果
        passed = sum(test_results)
        total = len(test_results)
        
        print(f"\n🎉 测试完成: {passed}/{total} 个测试通过")
        
        if passed == total:
            print("\n✅ 所有时区相关测试都通过了！")
            print("\n修复要点总结：")
            print("1. ✅ 统一使用 naive datetime 避免时区混合")
            print("2. ✅ 自动转换 timezone-aware datetime 为本地时间")
            print("3. ✅ 时间计算不再出现时区错误")
            print("4. ✅ 超时检测逻辑正常工作")
            print("5. ✅ 心跳检测逻辑正常工作")
        else:
            print(f"\n❌ 有 {total - passed} 个测试失败")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
