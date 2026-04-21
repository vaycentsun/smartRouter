"""Task Classifier - 任务分类器"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from .types import ClassificationResult, get_default_classification
from .difficulty_classifier import DifficultyClassifier, DifficultyResult


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


# 默认难度评估规则
# 优先级：keyword (1) > length (2)，确保语义关键词优先于长度判断
DEFAULT_DIFFICULTY_RULES = [
    {
        "condition": "keyword:复杂|详细|深入|架构|设计模式|优化|重构|性能|并发|分布式",
        "difficulty": "hard",
        "description": "复杂关键词",
        "priority": 1
    },
    {
        "condition": "keyword:step by step|一步步|详细步骤|完整实现|全面分析",
        "difficulty": "hard",
        "description": "深度分析关键词",
        "priority": 1
    },
    {
        "condition": "keyword:简单|easy|快速|简述|简短|总结一下",
        "difficulty": "easy",
        "description": "简单关键词",
        "priority": 1
    },
    {
        "condition": "length > 500",
        "difficulty": "hard",
        "description": "长文本",
        "priority": 2
    },
    {
        "condition": "length < 20",
        "difficulty": "easy",
        "description": "极短文本",
        "priority": 2
    }
]


class TaskClassifier:
    """统一任务分类器（兼容接口）
    
    组合任务类型分类和动态难度评估，兼容旧版接口。
    难度不再硬编码为 medium，而是基于文本特征动态评估。
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
        
        # 初始化动态难度评估器
        self._difficulty_classifier = DifficultyClassifier(DEFAULT_DIFFICULTY_RULES)
    
    def classify(self, messages: List[Dict]) -> ClassificationResult:
        """
        分类任务
        
        流程：
        1. 提取用户输入并拼接
        2. 规则匹配确定任务类型
        3. 动态难度评估（基于文本长度、关键词、对话轮数）
        4. 多轮对话提升难度档位
        
        Args:
            messages: 消息列表
            
        Returns:
            ClassificationResult
        """
        # 提取用户输入
        user_content = ""
        user_message_count = 0
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if content:
                    user_content += content + " "
                    user_message_count += 1
        user_content = user_content.strip().lower()
        
        if not user_content:
            return get_default_classification()
        
        # 规则匹配确定任务类型
        matched_task_type = None
        for rule in self.rules:
            pattern = rule.get("pattern", "")
            if self._match_pattern(user_content, pattern):
                matched_task_type = rule.get("task_type", self.default_type)
                break
        
        task_type = matched_task_type or self.default_type
        source = "rule_engine" if matched_task_type else "default"
        
        # 动态难度评估
        difficulty_result = self._difficulty_classifier.classify(user_content, task_type=task_type)
        difficulty = difficulty_result.difficulty
        
        # 多轮对话提升难度：超过 3 轮 user 消息，难度升一档
        if user_message_count > 3:
            difficulty = self._bump_difficulty(difficulty)
        
        # 计算置信度
        if matched_task_type:
            confidence = 0.9 if difficulty_result.source == "rule" else 0.7
        else:
            confidence = 0.5 if difficulty_result.source == "rule" else 0.3
        
        return ClassificationResult(
            task_type=task_type,
            estimated_difficulty=difficulty,
            confidence=confidence,
            source="dynamic_difficulty" if difficulty_result.source == "rule" else source
        )
    
    def _bump_difficulty(self, difficulty: str) -> str:
        """提升难度一档
        
        Args:
            difficulty: 当前难度
            
        Returns:
            提升后的难度
        """
        order = ["easy", "medium", "hard"]
        try:
            idx = order.index(difficulty)
            if idx < len(order) - 1:
                return order[idx + 1]
        except ValueError:
            pass
        return difficulty
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """匹配正则模式"""
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            return pattern.lower() in text


__all__ = ["TaskClassifier", "TaskTypeClassifier", "TaskTypeResult"]
