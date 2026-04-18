from typing import List, Dict

from .types import ClassificationResult, get_default_classification
from .rule_engine import RuleEngine
from .embedding import EmbeddingMatcher


class TaskClassifier:
    """任务分类器：L1 规则引擎 → L2 Embedding 匹配的流水线"""
    
    def __init__(self, rules: List[Dict], embedding_config: Dict):
        self.rule_engine = RuleEngine(rules)
        self.embedding_matcher = EmbeddingMatcher(
            custom_types=embedding_config.get("custom_types", [])
        )
    
    def classify(self, messages: List[Dict]) -> ClassificationResult:
        """
        分类流程：
        1. 先尝试 L1 规则引擎（快、确定性强）
        2. 规则无匹配 → L2 Embedding 匹配
        3. 两者都失败 → 返回默认分类（chat, medium）
        """
        # L1 规则引擎
        result = self.rule_engine.classify(messages)
        if result is not None:
            return result
        
        # L2 Embedding 匹配
        result = self.embedding_matcher.classify(messages)
        if result is not None:
            return result
        
        # 降级到默认值
        return get_default_classification()
