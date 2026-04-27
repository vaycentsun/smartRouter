"""Token 估算工具

提供轻量级的 token 估算功能，无需依赖 tiktoken 等外部库。
采用字符数比例法进行估算：
- 英文：约 4 字符/token
- 中文：约 1.5 字符/token
- 混合文本：动态加权平均

精度足以满足路由决策中的上下文窗口过滤需求。
"""

import re
from typing import List, Dict, Optional


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数量
    
    Args:
        text: 输入文本
        
    Returns:
        估算的 token 数（向上取整）
    """
    if not text:
        return 0
    
    # 分离中英文
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text)
    non_chinese_chars = total_chars - chinese_chars
    
    # 中文约 1.5 字符/token，英文/其他约 4 字符/token
    chinese_tokens = chinese_chars / 1.5
    other_tokens = non_chinese_chars / 4.0
    
    # 向上取整，保证不会低估
    return max(1, int(chinese_tokens + other_tokens + 0.999))


def estimate_messages_tokens(messages: Optional[List[Dict]]) -> int:
    """估算消息列表的总 token 数量
    
    包含：
    - 每条消息内容的 token
    - 每条消息的格式开销（role、分隔符等）约 4 tokens
    - 整体 prompt 框架开销约 3 tokens
    
    Args:
        messages: OpenAI 格式的消息列表
        
    Returns:
        估算的总 token 数
    """
    if not messages:
        return 0
    
    total = 0
    
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        
        # 每条消息固定开销：role + content 键 + 分隔符
        total += 4
        
        content = msg.get("content", "")
        if content:
            total += estimate_tokens(str(content))
    
    # 整体 prompt 框架开销
    total += 3
    
    return total
