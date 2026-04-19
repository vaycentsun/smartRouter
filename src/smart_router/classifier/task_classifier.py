"""v2 任务分类器 - 仅识别任务类型，不涉及难度"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TaskTypeResult:
    """任务分类结果"""
    task_type: str
    confidence: float
    source: str  # "keyword" | "default"


class TaskTypeClassifier:
    """任务类型分类器（v2 架构）"""
    
    def __init__(self, task_types: Dict[str, Dict]):
        """
        Args:
            task_types: {task_type: {keywords: [...], ...}}
        """
        self.task_types = task_types
        self.default_type = "chat"
    
    def classify(self, messages: List[Dict]) -> TaskTypeResult:
        """
        分类任务类型（仅识别类型，不判断难度）
        
        Args:
            messages: 消息列表
            
        Returns:
            TaskTypeResult
        """
        # 提取用户输入
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content += msg.get("content", "") + " "
        user_content = user_content.strip().lower()
        
        if not user_content:
            return TaskTypeResult(
                task_type=self.default_type,
                confidence=0.0,
                source="default"
            )
        
        # 关键词匹配
        best_match = None
        best_score = 0.0
        
        for task_type, config in self.task_types.items():
            keywords = config.get("keywords", [])
            score = self._calculate_match_score(user_content, keywords)
            
            if score > best_score:
                best_score = score
                best_match = task_type
        
        if best_match and best_score > 0:
            return TaskTypeResult(
                task_type=best_match,
                confidence=min(best_score, 1.0),
                source="keyword"
            )
        
        # 默认返回 chat
        return TaskTypeResult(
            task_type=self.default_type,
            confidence=0.0,
            source="default"
        )
    
    def _calculate_match_score(self, text: str, keywords: List[str]) -> float:
        """计算匹配分数"""
        if not keywords:
            return 0.0
        
        matched_count = 0
        for keyword in keywords:
            # 支持正则表达式
            try:
                if re.search(keyword, text, re.IGNORECASE):
                    matched_count += 1
            except re.error:
                # 普通字符串匹配
                if keyword.lower() in text:
                    matched_count += 1
        
        # 计算匹配率
        return matched_count / len(keywords)
