"""ErrorCounter — 基于内存的 5 分钟滑动窗口错误计数器

使用 collections.deque 存储时间戳，自动清理过期条目。
"""

import time
from collections import deque
from typing import Optional


class ErrorCounter:
    """5 分钟滑动窗口错误计数器
    
    接口：
    - record(is_error: bool) -> 记录一次请求结果
    - get_error_rate() -> float 返回窗口内错误率
    """

    def __init__(self, window_seconds: int = 300):
        self._window_seconds = window_seconds
        # 存储 (timestamp, is_error) 元组
        self._entries: deque = deque()

    def record(self, is_error: bool) -> None:
        """记录一次请求结果
        
        Args:
            is_error: True 表示错误响应，False 表示成功响应
        """
        now = time.time()
        self._entries.append((now, is_error))
        self._cleanup(now)

    def get_error_rate(self) -> float:
        """获取当前窗口内的错误率"""
        now = time.time()
        self._cleanup(now)
        if not self._entries:
            return 0.0
        error_count = sum(1 for _, is_error in self._entries if is_error)
        return error_count / len(self._entries)

    def _cleanup(self, now: Optional[float] = None) -> None:
        """清理过期的条目"""
        if now is None:
            now = time.time()
        cutoff = now - self._window_seconds
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()
