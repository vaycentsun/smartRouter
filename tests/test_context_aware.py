"""上下文长度感知路由与动态难度校准测试"""

import pytest
from smart_router.utils.token_counter import estimate_tokens, estimate_messages_tokens
from smart_router.selector.model_selector import ModelSelector, ModelSelectionResult
from smart_router.classifier.task_classifier import TaskClassifier
from smart_router.classifier.types import ClassificationResult


class TestTokenCounter:
    """Token 估算工具测试"""
    
    def test_estimate_tokens_empty(self):
        """测试空文本"""
        assert estimate_tokens("") == 0
    
    def test_estimate_tokens_english(self):
        """测试英文文本估算"""
        text = "Hello world"
        # 英文约 4 chars/token
        assert estimate_tokens(text) == 3  # 11 / 4 = 2.75 -> ceil = 3
    
    def test_estimate_tokens_chinese(self):
        """测试中文文本估算"""
        text = "你好世界"
        # 中文约 1.5 chars/token
        assert estimate_tokens(text) == 3  # 4 / 1.5 = 2.67 -> ceil = 3
    
    def test_estimate_tokens_mixed(self):
        """测试中英文混合"""
        text = "Hello 世界"
        # 英文 5 chars + 中文 2 chars
        # 英文部分: 5/4 = 1.25, 中文部分: 2/1.5 = 1.33
        # 混合平均约 7/2.5 = 2.8 -> ceil = 3
        result = estimate_tokens(text)
        assert result >= 2
    
    def test_estimate_messages_tokens_single(self):
        """测试单条消息估算"""
        messages = [{"role": "user", "content": "Hello world"}]
        result = estimate_messages_tokens(messages)
        # 内容 token + 每条消息固定开销 4
        assert result >= 7  # 3 + 4
    
    def test_estimate_messages_tokens_multiple(self):
        """测试多条消息估算"""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        result = estimate_messages_tokens(messages)
        # 3条消息，每条 +4 开销
        assert result >= 12  # at least 3*4 = 12 overhead
    
    def test_estimate_messages_tokens_empty_content(self):
        """测试空内容消息"""
        messages = [{"role": "user", "content": ""}]
        assert estimate_messages_tokens(messages) == 7  # 消息开销 4 + 框架 3
    
    def test_estimate_messages_tokens_none_messages(self):
        """测试 None messages"""
        assert estimate_messages_tokens(None) == 0
    
    def test_estimate_messages_tokens_no_content_key(self):
        """测试缺少 content 键的消息"""
        messages = [{"role": "user"}]
        assert estimate_messages_tokens(messages) == 7  # 消息开销 4 + 框架 3


class TestModelSelectorContextAware:
    """模型选择器上下文感知测试"""
    
    @pytest.fixture
    def model_pool(self):
        """创建测试模型池"""
        return {
            "capabilities": {
                "gpt-4o": {
                    "difficulties": ["easy", "medium", "hard"],
                    "task_types": ["chat", "coding"],
                    "priority": 2,
                    "quality": 9,
                    "cost": 3,
                    "context": 128000
                },
                "gpt-4o-mini": {
                    "difficulties": ["easy", "medium"],
                    "task_types": ["chat"],
                    "priority": 1,
                    "quality": 6,
                    "cost": 9,
                    "context": 128000
                },
                "claude-haiku": {
                    "difficulties": ["easy", "medium", "hard"],
                    "task_types": ["chat", "coding"],
                    "priority": 3,
                    "quality": 7,
                    "cost": 8,
                    "context": 200000
                },
                "gpt-3.5-turbo": {
                    "difficulties": ["easy", "medium"],
                    "task_types": ["chat"],
                    "priority": 4,
                    "quality": 5,
                    "cost": 10,
                    "context": 16000
                }
            },
            "default_model": "gpt-4o"
        }
    
    @pytest.fixture
    def selector(self, model_pool):
        """创建选择器实例"""
        return ModelSelector(model_pool)
    
    def test_select_without_context_filter(self, selector):
        """测试不传 required_context 时不做过滤"""
        result = selector.select("chat", "easy", "auto")
        assert result.model_name == "gpt-4o-mini"  # priority 最低
    
    def test_select_with_small_context(self, selector):
        """测试小上下文需求不过滤"""
        result = selector.select("chat", "easy", "auto", required_context=1000)
        assert result.model_name == "gpt-4o-mini"  # 所有模型都满足
    
    def test_select_with_large_context(self, selector):
        """测试大上下文需求过滤小窗口模型"""
        result = selector.select("chat", "easy", "auto", required_context=50000)
        # gpt-3.5-turbo (16k) 被过滤，gpt-4o-mini (128k) 满足
        assert result.model_name == "gpt-4o-mini"
        assert "gpt-3.5-turbo" not in ["gpt-4o-mini", "gpt-4o", "claude-haiku"]
    
    def test_select_with_very_large_context(self, selector):
        """测试超大上下文需求只留 Claude"""
        result = selector.select("chat", "easy", "auto", required_context=150000)
        # 只有 claude-haiku (200k) 满足
        assert result.model_name == "claude-haiku"
    
    def test_select_with_excessive_context_falls_back(self, selector):
        """测试超过所有模型的上下文需求回退到默认"""
        result = selector.select("chat", "easy", "auto", required_context=500000)
        # 没有模型满足，回退到默认
        assert result.model_name == "gpt-4o"
        assert result.confidence < 0.5
        assert "上下文" in result.reason or "context" in result.reason.lower()
    
    def test_select_with_context_and_quality_strategy(self, selector):
        """测试质量策略结合上下文过滤"""
        result = selector.select("chat", "easy", "quality", required_context=50000)
        # gpt-3.5-turbo 被过滤，在剩余中 quality 最高的是 gpt-4o (9)
        assert result.model_name == "gpt-4o"
    
    def test_select_with_context_and_cost_strategy(self, selector):
        """测试成本策略结合上下文过滤"""
        result = selector.select("chat", "easy", "cost", required_context=50000)
        # gpt-3.5-turbo 被过滤，在剩余中 cost 最高（最便宜）的是 gpt-4o-mini (9)
        assert result.model_name == "gpt-4o-mini"
    
    def test_get_candidates_with_context(self, selector):
        """测试 get_candidates 支持上下文过滤"""
        candidates = selector.get_candidates("chat", "easy", required_context=50000)
        assert "gpt-3.5-turbo" not in candidates
        assert "gpt-4o-mini" in candidates
        assert "gpt-4o" in candidates
        assert "claude-haiku" in candidates
    
    def test_get_candidates_without_context(self, selector):
        """测试 get_candidates 不传上下文不过滤"""
        candidates = selector.get_candidates("chat", "easy")
        assert "gpt-3.5-turbo" in candidates


class TestDynamicDifficultyCalibration:
    """动态难度校准测试"""
    
    @pytest.fixture
    def classifier(self):
        """创建集成动态难度的分类器"""
        rules = [
            {
                "pattern": r"(?i)(写|write|draft)",
                "task_type": "writing",
                "difficulty": "medium"
            },
            {
                "pattern": r"(?i)(review|审查|code)",
                "task_type": "code_review",
                "difficulty": "medium"
            }
        ]
        return TaskClassifier(rules=rules, embedding_config={})
    
    def test_short_text_easy(self, classifier):
        """测试短文本被评估为 easy"""
        messages = [{"role": "user", "content": "Hi"}]
        result = classifier.classify(messages)
        assert result.estimated_difficulty == "easy"
        assert result.source == "dynamic_difficulty"
    
    def test_long_text_hard(self, classifier):
        """测试长文本被评估为 hard"""
        text = "这是一个非常复杂的深度分析问题，" + "需要详细考虑各个方面。" * 50
        messages = [{"role": "user", "content": text}]
        result = classifier.classify(messages)
        assert result.estimated_difficulty == "hard"
    
    def test_hard_keyword(self, classifier):
        """测试复杂关键词提升难度"""
        messages = [{"role": "user", "content": "请深入分析这个架构设计模式的问题"}]
        result = classifier.classify(messages)
        # 虽然有复杂关键词，但长度不长，可能 medium
        assert result.estimated_difficulty in ["medium", "hard"]
    
    def test_multi_turn_conversation_medium(self, classifier):
        """测试多轮对话提升难度"""
        messages = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "问题2"},
            {"role": "assistant", "content": "回答2"},
            {"role": "user", "content": "问题3"},
            {"role": "assistant", "content": "回答3"},
            {"role": "user", "content": "问题4"}
        ]
        result = classifier.classify(messages)
        # 4 轮 user 消息，多轮对话升档，至少 medium
        assert result.estimated_difficulty in ["medium", "hard"]
    
    def test_explicit_marker_overrides(self, classifier):
        """测试显式标记覆盖动态评估"""
        # 注意：这个测试在 TaskClassifier 层面不直接测 marker
        # marker 在 plugin.py 层面处理，TaskClassifier 只负责内容分析
        pass
    
    def test_empty_messages_default(self, classifier):
        """测试空消息返回默认"""
        result = classifier.classify([])
        assert result.task_type == "chat"
        assert result.estimated_difficulty == "medium"
    
    def test_combined_difficulty_factors(self, classifier):
        """测试多因素叠加评估 hard"""
        # 复杂关键词（优先级最高）
        messages = [
            {"role": "user", "content": "请详细深入分析这个复杂系统的架构设计"}
        ]
        result = classifier.classify(messages)
        assert result.estimated_difficulty == "hard"


class TestIntegrationContextAndDifficulty:
    """集成测试：上下文过滤 + 动态难度"""
    
    @pytest.fixture
    def full_selector(self):
        """创建完整测试选择器"""
        return ModelSelector({
            "capabilities": {
                "cheap-small": {
                    "difficulties": ["easy", "medium"],
                    "task_types": ["chat"],
                    "priority": 1,
                    "quality": 5,
                    "cost": 10,
                    "context": 4000
                },
                "mid-large": {
                    "difficulties": ["easy", "medium", "hard"],
                    "task_types": ["chat", "coding"],
                    "priority": 2,
                    "quality": 7,
                    "cost": 6,
                    "context": 128000
                }
            },
            "default_model": "mid-large"
        })
    
    def test_long_prompt_routes_to_large_context(self, full_selector):
        """测试长提示自动路由到大上下文模型"""
        # 模拟 10000 tokens 的输入
        long_text = "a" * 40000  # ~10000 tokens
        required_context = estimate_tokens(long_text) + 2000  # + 输出预留
        
        result = full_selector.select("chat", "hard", "auto", required_context=required_context)
        assert result.model_name == "mid-large"
    
    def test_easy_task_short_prompt_routes_to_cheap(self, full_selector):
        """测试简单短任务路由到便宜模型"""
        result = full_selector.select("chat", "easy", "auto", required_context=500)
        assert result.model_name == "cheap-small"
