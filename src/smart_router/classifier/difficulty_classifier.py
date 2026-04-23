"""难度评估器 - 独立评估难度"""

import re
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass


@dataclass
class DifficultyResult:
    """难度评估结果"""
    difficulty: Literal["easy", "medium", "hard"]
    confidence: float
    source: str  # "rule" | "default"
    matched_rule: Optional[str] = None


class DifficultyClassifier:
    """难度分类器"""
    
    def __init__(self, rules: List[Dict]):
        """
        Args:
            rules: 难度评估规则列表
        """
        self.rules = sorted(rules, key=lambda x: x.get("priority", 1))
        self.default_difficulty = "medium"
    
    def classify(
        self, 
        text: str, 
        task_type: Optional[str] = None
    ) -> DifficultyResult:
        """
        评估难度
        
        Args:
            text: 用户输入文本
            task_type: 任务类型（用于过滤特定规则）
            
        Returns:
            DifficultyResult
        """
        if not text:
            return DifficultyResult(
                difficulty=self.default_difficulty,
                confidence=0.0,
                source="default"
            )
        
        text_lower = text.lower()
        
        # 按优先级遍历规则
        for rule in self.rules:
            # 检查规则是否适用于当前任务类型
            applies_to = rule.get("applies_to")
            if applies_to and task_type not in applies_to:
                continue
            
            condition = rule.get("condition", "")
            
            # 解析条件
            if self._match_condition(text_lower, condition):
                return DifficultyResult(
                    difficulty=rule["difficulty"],
                    confidence=0.8,  # 规则匹配的置信度
                    source="rule",
                    matched_rule=rule.get("description", condition)
                )
        
        # 默认返回 medium
        return DifficultyResult(
            difficulty=self.default_difficulty,
            confidence=0.5,
            source="default"
        )
    
    def _match_condition(self, text: str, condition: str) -> bool:
        """匹配条件"""
        condition = condition.lower()
        
        # 条件 1: length < N
        if match := re.match(r'length\s*<\s*(\d+)', condition):
            length_limit = int(match.group(1))
            return len(text) < length_limit
        
        # 条件 2: length > N
        if match := re.match(r'length\s*>\s*(\d+)', condition):
            length_limit = int(match.group(1))
            return len(text) > length_limit
        
        # 条件 3: keyword:xxx|yyy
        if match := re.match(r'keyword:([\w\|]+)', condition):
            keywords = match.group(1).split("|")
            for kw in keywords:
                if kw in text:
                    return True
            return False
        
        # 条件 4: contains:xxx|yyy
        if match := re.match(r'contains:([\w\|]+)', condition):
            keywords = match.group(1).split("|")
            for kw in keywords:
                if kw in text:
                    return True
            return False
        
        # 默认：字符串包含
        return condition in text
