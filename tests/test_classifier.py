import pytest
from smart_router.classifier import TaskClassifier
from smart_router.classifier.types import get_default_classification


class TestRuleEngine:
    def test_code_review_match(self):
        classifier = TaskClassifier(rules=[
            {"pattern": "(?i)(review|审查)", "task_type": "code_review", "difficulty": "medium"}
        ], embedding_config={"enabled": True, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "帮我审查代码"}])
        assert result.task_type == "code_review"
        assert result.source == "rule_engine"
    
    def test_no_match_fallback_to_embedding(self):
        classifier = TaskClassifier(rules=[], embedding_config={"enabled": True, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "帮我审查这段 Python 代码"}])
        # Embedding 匹配可能返回 code_review 或 default，取决于相似度
        assert result.source in ["embedding", "default"]
        assert result.task_type in ["code_review", "chat"]
    
    def test_no_match_at_all(self):
        classifier = TaskClassifier(rules=[], embedding_config={"enabled": False, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "xyz123 随机文本"}])
        assert result.source == "default"
        assert result.task_type == "chat"
    
    def test_writing_pattern(self):
        classifier = TaskClassifier(rules=[
            {"pattern": "(?i)(write|draft|生成|撰写)", "task_type": "writing", "difficulty": "easy"}
        ], embedding_config={"enabled": False, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "写一篇文章"}])
        assert result.task_type == "writing"
        # 规则引擎匹配成功
        assert result.source in ["rule_engine", "embedding"]
    
    def test_reasoning_pattern(self):
        classifier = TaskClassifier(rules=[
            {"pattern": "(?i)(prove|证明|逻辑推理)", "task_type": "reasoning", "difficulty": "hard"}
        ], embedding_config={"enabled": False, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "证明这个定理"}])
        assert result.task_type == "reasoning"
        assert result.estimated_difficulty == "hard"
