"""Task Classifier - 任务分类器（重构版）

支持两种分类方式：
1. L1 Keywords: 基于关键词匹配（快速、精确）
2. L2 Embedding: 基于示例相似度匹配（模糊、泛化）

分类流程：
1. 先尝试 L1 keywords 匹配
2. 如果未命中，尝试 L2 embedding 相似度匹配
3. 如果仍未命中，返回默认类型
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from .types import ClassificationResult, get_default_classification
from .difficulty_classifier import DifficultyClassifier, DifficultyResult
from .embedding_matcher import SimpleEmbeddingMatcher


@dataclass
class TaskTypeResult:
    """任务类型分类结果"""
    task_type: str
    confidence: float
    source: str  # "keyword" | "embedding" | "default"


class TaskTypeClassifier:
    """任务类型分类器（支持 Keywords + Embedding 匹配）
    
    基于关键词匹配和示例相似度进行任务类型分类。
    """
    
    def __init__(self, task_types: Dict[str, Dict]):
        """
        Args:
            task_types: {
                task_type: {
                    keywords: [...],      # 用于 L1 精确匹配
                    examples: [...],      # 用于 L2 相似度匹配
                    description: ...
                }
            }
        """
        self.task_types = task_types
        self.default_type = "chat"
        
        # 构建示例映射用于 Embedding 匹配
        self.examples_map = {
            task_type: config.get("examples", [])
            for task_type, config in task_types.items()
            if config.get("examples")
        }
        
        # 初始化 Embedding 匹配器（阈值 0.28 适合短中文文本）
        self._embedding_matcher = SimpleEmbeddingMatcher(threshold=0.28)
    
    def classify(self, messages: List[Dict]) -> TaskTypeResult:
        """
        分类任务类型
        
        流程：
        1. L1: 关键词匹配（快速精确）
        2. L2: 示例相似度匹配（模糊泛化）
        3. 默认回退
        
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
        
        # L1: 关键词匹配
        keyword_result = self._classify_by_keywords(user_content)
        if keyword_result is not None:
            return keyword_result
        
        # L2: 示例相似度匹配
        embedding_result = self._classify_by_embedding(user_content)
        if embedding_result is not None:
            return embedding_result
        
        # 默认返回 chat
        return TaskTypeResult(
            task_type=self.default_type,
            confidence=0.0,
            source="default"
        )
    
    def _classify_by_keywords(self, text: str) -> Optional[TaskTypeResult]:
        """L1: 基于关键词匹配"""
        best_match = None
        best_score = 0.0
        
        for task_type, config in self.task_types.items():
            keywords = config.get("keywords", [])
            score = self._calculate_keyword_score(text, keywords)
            
            if score > best_score:
                best_score = score
                best_match = task_type
        
        if best_match and best_score > 0:
            return TaskTypeResult(
                task_type=best_match,
                confidence=min(best_score, 1.0),
                source="keyword"
            )
        
        return None
    
    def _classify_by_embedding(self, text: str) -> Optional[TaskTypeResult]:
        """L2: 基于示例相似度匹配"""
        if not self.examples_map:
            return None
        
        task_type, score = self._embedding_matcher.find_best_match(text, self.examples_map)
        
        if task_type is not None:
            return TaskTypeResult(
                task_type=task_type,
                confidence=min(score, 1.0),
                source="embedding"
            )
        
        return None
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """计算关键词匹配分数
        
        匹配多个关键词时给予额外奖励，以提高区分度。
        """
        if not keywords:
            return 0.0
        
        matched = []
        for keyword in keywords:
            # 支持正则表达式
            try:
                if re.search(keyword, text, re.IGNORECASE):
                    matched.append(keyword)
            except re.error:
                # 普通字符串匹配
                if keyword.lower() in text:
                    matched.append(keyword)
        
        if not matched:
            return 0.0
        
        # 基础分：匹配率
        base_score = len(matched) / len(keywords)
        # 多关键词匹配 bonus：每多匹配一个关键词加 0.15
        bonus = 0.15 * (len(matched) - 1)
        
        return base_score + bonus


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
    """统一任务分类器（重构版）
    
    组合任务类型分类和动态难度评估，支持 keywords 和 examples。
    
    分类流程：
    1. L1 Keywords: 基于配置中的 keywords 进行快速匹配
    2. L2 Embedding: 基于配置中的 examples 进行相似度匹配
    3. L3 Rules: 回退到旧的规则引擎（向后兼容）
    """
    
    def __init__(
        self,
        rules: List[Dict],
        embedding_config: Dict,
        task_configs: Optional[Dict[str, Dict]] = None
    ):
        """
        Args:
            rules: 分类规则列表（向后兼容）
            embedding_config: Embedding 配置
            task_configs: 任务配置字典 {
                task_type: {
                    keywords: [...],
                    examples: [...]
                }
            }
        """
        self.rules = rules
        self.embedding_config = embedding_config
        self.default_type = "chat"
        self.default_difficulty = "medium"
        
        # 构建 task_types 供 TaskTypeClassifier 使用
        task_types = {}
        
        if task_configs:
            # 使用新的 task_configs（包含 keywords 和 examples）
            for task_type, config in task_configs.items():
                task_types[task_type] = {
                    "keywords": config.get("keywords", []),
                    "examples": config.get("examples", []),
                    "description": config.get("description", "")
                }
        else:
            # 向后兼容：从 rules 构建（旧行为）
            for rule in rules:
                task_type = rule.get("task_type", "")
                if task_type:
                    if task_type not in task_types:
                        task_types[task_type] = {"keywords": [], "examples": [], "description": ""}
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
        2. L1/L2 任务类型分类（keywords + embedding）
        3. 动态难度评估
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
        
        # 任务类型分类（L1 keywords / L2 embedding）
        type_result = self._type_classifier.classify(messages)
        task_type = type_result.task_type
        
        # 动态难度评估
        difficulty_result = self._difficulty_classifier.classify(user_content, task_type=task_type)
        difficulty = difficulty_result.difficulty
        
        # 多轮对话提升难度：超过 3 轮 user 消息，难度升一档
        if user_message_count > 3:
            difficulty = self._bump_difficulty(difficulty)
        
        # 计算置信度
        confidence = type_result.confidence
        if type_result.source == "keyword":
            confidence = max(confidence, 0.9)
        elif type_result.source == "embedding":
            confidence = max(confidence, 0.6)
        
        # 确定 source（向后兼容）
        # 如果任务类型已明确分类（keyword/embedding），保留其 source
        # 只有当任务类型是默认回退且难度评估器命中了规则时，才使用 dynamic_difficulty
        if type_result.source == "default" and difficulty_result.source == "rule":
            source = "dynamic_difficulty"
        else:
            source = type_result.source
        
        return ClassificationResult(
            task_type=task_type,
            estimated_difficulty=difficulty,
            confidence=confidence,
            source=source
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
