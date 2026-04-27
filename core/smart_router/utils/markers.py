import re
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class MarkerResult:
    stage: Optional[str] = None
    difficulty: Optional[str] = None


MARKER_PATTERN = re.compile(r'\[(stage|difficulty):(\w+)\]', re.IGNORECASE)


def parse_markers(messages: List[Dict]) -> MarkerResult:
    """
    从消息列表中提取阶段标记和难度标记。
    扫描所有消息的 content 字段，取第一个匹配的标记。
    """
    result = MarkerResult()
    
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        
        for match in MARKER_PATTERN.finditer(content):
            key = match.group(1).lower()
            value = match.group(2).lower()
            
            if key == "stage" and result.stage is None:
                result.stage = value
            elif key == "difficulty" and result.difficulty is None:
                result.difficulty = value
            
            # 两者都找到后提前退出
            if result.stage is not None and result.difficulty is not None:
                return result
    
    return result


def strip_markers(text: str) -> str:
    """从文本中移除标记，避免干扰模型输入"""
    return MARKER_PATTERN.sub("", text).strip()
