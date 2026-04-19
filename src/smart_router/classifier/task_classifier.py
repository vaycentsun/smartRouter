"""Task Classifier - 任务分类器"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from .types import ClassificationResult, get_default_classification


@dataclass
class TaskTypeResult:
    """任务类型分类结果"""
    task_type: str
    confidence: float
    source: str  # "keyword" | "default"


class TaskTypeClassifier:
    """任务类型分类器（V2 架构）
    
    基于关键词匹配进行任务类型分类
    """
    
    def __init__(self, task_types: Dict[str, Dict]):
        """
        Args:
            task_types: {task_type: {keywords: [...], description: ...}}
        """
        self.task_types = task_types
        self.default_type = "chat"
    
    def classify(self, messages: List[Dict]) -> TaskTypeResult:
        """
        分类任务类型
        
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


class TaskClassifier:
    """统一任务分类器（兼容接口）
    
    组合任务类型分类和难度分类，兼容旧版接口
    """
    
    def __init__(self, rules: List[Dict], embedding_config: Dict):
        """
        Args:
            rules: 分类规则列表
            embedding_config: Embedding 配置（当前未使用）
        """
        self.rules = rules
        self.embedding_config = embedding_config
        self.default_type = "chat"
        self.default_difficulty = "medium"
        
        # 构建 task_types 供内部使用
        task_types = {}
        for rule in rules:
            task_type = rule.get("task_type", "")
            if task_type:
                if task_type not in task_types:
                    task_types[task_type] = {"keywords": [], "description": ""}
                # 将 pattern 转换为 keyword（简化处理）
                pattern = rule.get("pattern", "")
                if pattern:
                    task_types[task_type]["keywords"].append(pattern)
        
        self._type_classifier = TaskTypeClassifier(task_types)
    
    def classify(self, messages: List[Dict]) -> ClassificationResult:
        """
        分类任务
        
        Args:
            messages: 消息列表
            
        Returns:
            ClassificationResult
        """
        # 提取用户输入
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content += msg.get("content", "") + " "
        user_content = user_content.strip().lower()
        
        if not user_content:
            return get_default_classification()
        
        # 规则匹配
        for rule in self.rules:
            pattern = rule.get("pattern", "")
            if self._match_pattern(user_content, pattern):
                return ClassificationResult(
                    task_type=rule.get("task_type", self.default_type),
                    estimated_difficulty=rule.get("difficulty", self.default_difficulty),
                    confidence=0.9,
                    source="rule_engine"
                )
        
        # 默认返回
        return get_default_classification()
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """匹配正则模式"""
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return pattern.lower() in text


__all__ = ["TaskClassifier", "TaskTypeClassifier", "TaskTypeResult"]
