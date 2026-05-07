"""Gateway 测试共享配置

修复 Python 3.9 下 asyncio.run() 关闭事件循环后，
litellm 导入创建 asyncio.Lock() 失败的兼容性问题。
"""

import asyncio
import pytest


@pytest.fixture(autouse=True)
def ensure_event_loop():
    """确保每个测试都有可用的事件循环"""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield
