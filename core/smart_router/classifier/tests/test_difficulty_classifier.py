"""难度分类器测试"""

import pytest
from smart_router.classifier.difficulty_classifier import DifficultyClassifier, DifficultyResult


class TestDifficultyClassifier:
    """难度分类器测试"""
    
    @pytest.fixture
    def classifier(self):
        return DifficultyClassifier([
            {
                "condition": "length < 30",
                "difficulty": "easy",
                "description": "短文本",
                "priority": 1
            },
            {
                "condition": "length > 200",
                "difficulty": "hard",
                "description": "长文本",
                "priority": 1
            },
            {
                "condition": "keyword:简单|easy|快速",
                "difficulty": "easy",
                "description": "简单关键词",
                "priority": 2
            },
            {
                "condition": "keyword:复杂|详细|深入",
                "difficulty": "hard",
                "description": "复杂关键词",
                "priority": 2
            },
            {
                "condition": "keyword:架构|设计模式",
                "difficulty": "hard",
                "applies_to": ["code_review"],
                "description": "架构相关",
                "priority": 3
            }
        ])
    
    def test_short_text_easy(self, classifier):
        """测试短文本为 easy"""
        result = classifier.classify("简短的问题")
        
        assert result.difficulty == "easy"
        assert result.source == "rule"
    
    def test_long_text_hard(self, classifier):
        """测试长文本为 hard"""
        # 需要超过 200 个字符，且不满足 length < 30
        text = "这是一个需要详细深入分析的复杂问题" + "需要详细分析。" * 30
        assert len(text) > 200  # 确保长度超过 200
        
        result = classifier.classify(text)
        
        assert result.difficulty == "hard"
        assert result.source == "rule"
    
    def test_keyword_easy(self, classifier):
        """测试简单关键词"""
        result = classifier.classify("简单解释一下什么是 Python")
        
        assert result.difficulty == "easy"
    
    def test_keyword_hard(self, classifier):
        """测试复杂关键词"""
        # 长度超过 30，不满足 length < 30，所以会检查关键词
        text = "这是一个需要详细深入分析的复杂问题，需要认真考虑各种因素和背景知识"
        assert len(text) > 30, f"文本长度只有 {len(text)}，需要超过 30"
        
        result = classifier.classify(text)
        
        assert result.difficulty == "hard"
    
    def test_task_specific_rule(self, classifier):
        """测试特定任务类型规则"""
        # 架构关键词只在 code_review 中生效
        # 长度超过 30，不满足 length < 30
        text = "请详细分析一下architecture design patterns的相关问题"
        assert len(text) > 30, f"文本长度只有 {len(text)}，需要超过 30"
        
        result = classifier.classify(text, task_type="code_review")
        assert result.difficulty == "hard"
        
        # 在 writing 中不生效，应该是 medium（默认）
        # 使用不包含复杂关键词的文本，长度在 30-200 之间
        text_writing = "Please help me analyze this problem structure and relationships"
        assert len(text_writing) > 30, f"文本长度 {len(text_writing)}，需要超过 30"
        result = classifier.classify(text_writing, task_type="writing")
        assert result.difficulty == "medium"
    
    def test_default_medium(self, classifier):
        """测试默认 medium"""
        # 长度在 30-200 之间，不满足任何特定规则
        text = "这是一个普通长度的问题，不长也不短，刚好适合测试默认规则的使用"
        assert 30 <= len(text) <= 200, f"文本长度 {len(text)}，需要在 30-200 之间"
        
        result = classifier.classify(text)
        
        assert result.difficulty == "medium"
        assert result.source == "default"
    
    def test_empty_input(self, classifier):
        """测试空输入"""
        result = classifier.classify("")
        
        assert result.difficulty == "medium"

    def test_contains_condition(self):
        """测试 contains: 条件分支"""
        classifier = DifficultyClassifier([
            {
                "condition": "contains:foo|bar",
                "difficulty": "hard",
                "description": "包含特定关键词",
                "priority": 1
            }
        ])
        
        result = classifier.classify("this text contains foo keyword")
        assert result.difficulty == "hard"
        assert result.source == "rule"
        
        result2 = classifier.classify("this text contains bar keyword")
        assert result2.difficulty == "hard"
        
        result3 = classifier.classify("this text has neither")
        assert result3.difficulty == "medium"

    def test_string_contains_condition(self):
        """测试默认字符串包含条件"""
        classifier = DifficultyClassifier([
            {
                "condition": "testkeyword",
                "difficulty": "hard",
                "description": "字符串包含",
                "priority": 1
            }
        ])
        
        result = classifier.classify("this has testkeyword in it")
        assert result.difficulty == "hard"
        
        result2 = classifier.classify("this does not")
        assert result2.difficulty == "medium"
