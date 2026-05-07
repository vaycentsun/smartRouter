"""日志行解析器，支持新旧格式"""

import re
import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class LogEntry:
    """解析后的日志条目"""
    timestamp: Optional[str]  # "2026-05-07 14:23:01,234"
    level: Optional[str]      # "INFO"
    levelno: int              # logging.INFO
    name: Optional[str]       # "smart_router.gateway.server"
    message: str              # 日志消息
    raw: str                  # 原始行


def parse_log_line(line: str) -> LogEntry:
    """
    解析日志行，支持新旧格式
    
    新格式: 2026-05-07 14:23:01,234 - name - LEVEL - message
    旧格式: 任意文本（整个作为 message）
    
    Returns:
        LogEntry 对象
    """
    # 尝试匹配新格式
    # 格式: YYYY-MM-DD HH:MM:SS,mmm - name - LEVEL - message
    pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\S+) - (DEBUG|INFO|WARNING|ERROR|CRITICAL) - (.*)$'
    match = re.match(pattern, line.strip())
    
    if match:
        timestamp = match.group(1)
        name = match.group(2)
        level_str = match.group(3)
        message = match.group(4)
        levelno = getattr(logging, level_str, logging.INFO)
        
        return LogEntry(
            timestamp=timestamp,
            level=level_str,
            levelno=levelno,
            name=name,
            message=message,
            raw=line,
        )
    
    # 旧格式：整个行作为 message，标记为 INFO
    return LogEntry(
        timestamp=None,
        level="INFO",
        levelno=logging.INFO,
        name=None,
        message=line.strip(),
        raw=line,
    )
