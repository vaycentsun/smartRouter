import re
from typing import List, Dict, Optional

from .types import ClassificationResult


class RuleEngine:
    """L1 规则引擎：基于正则关键词匹配"""
    
    def __init__(self, rules: List[Dict]):
        """
        rules: [{"pattern": str, "task_type": str, "difficulty": str}]
        """
        self.rules = []
        for rule in rules:
            self.rules.append({
                "pattern": re.compile(rule["pattern"]),
                "task_type": rule["task_type"],
                "difficulty": rule["difficulty"],
            })
    
    def classify(self, messages: List[Dict]) -> Optional[ClassificationResult]:
        """
        扫描消息内容，返回第一个匹配的规则结果。
        若无匹配，返回 None。
        """
        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            
            for rule in self.rules:
                if rule["pattern"].search(content):
                    return ClassificationResult(
                        task_type=rule["task_type"],
                        estimated_difficulty=rule["difficulty"],
                        confidence=0.8,
                        source="rule_engine"
                    )
        
        return None
