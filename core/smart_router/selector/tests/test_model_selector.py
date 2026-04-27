"""model_selector (v2) 测试 — 覆盖遗留选择器核心逻辑"""

import pytest
from smart_router.selector.model_selector import ModelSelector, ModelSelectionResult


class TestModelSelectorInit:
    """初始化测试"""

    def test_init_with_available_models(self):
        """指定可用模型列表时只保留这些模型"""
        pool = {
            "capabilities": {
                "model-a": {
                    "difficulties": ["easy"],
                    "task_types": ["chat"],
                    "priority": 1,
                    "quality": 8,
                    "cost": 5
                },
                "model-b": {
                    "difficulties": ["easy"],
                    "task_types": ["chat"],
                    "priority": 2,
                    "quality": 6,
                    "cost": 8
                }
            },
            "available_models": ["model-a"],
            "default_model": "model-a"
        }
        
        selector = ModelSelector(pool)
        assert "model-a" in selector.capabilities
        assert "model-b" not in selector.capabilities

    def test_init_without_available_models(self):
        """不指定可用模型时保留所有模型"""
        pool = {
            "capabilities": {
                "model-a": {
                    "difficulties": ["easy"],
                    "task_types": ["chat"],
                    "priority": 1
                }
            }
        }
        
        selector = ModelSelector(pool)
        assert "model-a" in selector.capabilities

    def test_init_default_model_fallback(self):
        """默认模型不在可用列表时回退到第一个可用模型"""
        pool = {
            "capabilities": {
                "model-a": {
                    "difficulties": ["easy"],
                    "task_types": ["chat"],
                    "priority": 1
                }
            },
            "default_model": "nonexistent",
            "available_models": ["model-a"]
        }
        
        selector = ModelSelector(pool)
        assert selector.default_model == "model-a"

    def test_init_default_model_not_in_capabilities(self):
        """默认模型不在 capabilities 中时回退到第一个"""
        pool = {
            "capabilities": {
                "model-a": {"difficulties": ["easy"], "task_types": ["chat"], "priority": 1}
            },
            "default_model": "missing"
        }
        
        selector = ModelSelector(pool)
        assert selector.default_model == "model-a"


class TestModelSelectorIsEligible:
    """_is_eligible 测试"""

    @pytest.fixture
    def selector(self):
        pool = {
            "capabilities": {
                "model-a": {
                    "difficulties": ["easy", "medium"],
                    "task_types": ["chat", "writing"],
                    "priority": 1,
                    "quality": 8,
                    "cost": 5,
                    "context": 128000
                }
            }
        }
        return ModelSelector(pool)

    def test_eligible_basic(self, selector):
        """基本条件满足"""
        cap = selector.capabilities["model-a"]
        assert selector._is_eligible(cap, "chat", "easy") is True

    def test_ineligible_difficulty(self, selector):
        """难度不匹配"""
        cap = selector.capabilities["model-a"]
        assert selector._is_eligible(cap, "chat", "hard") is False

    def test_ineligible_task_type(self, selector):
        """任务类型不匹配"""
        cap = selector.capabilities["model-a"]
        assert selector._is_eligible(cap, "coding", "easy") is False

    def test_no_task_types_restrictions(self, selector):
        """没有 task_types 限制时支持所有任务"""
        cap = {"difficulties": ["easy"], "priority": 1}
        assert selector._is_eligible(cap, "any_task", "easy") is True

    def test_context_filter_pass(self, selector):
        """上下文窗口满足需求"""
        cap = selector.capabilities["model-a"]
        assert selector._is_eligible(cap, "chat", "easy", required_context=64000) is True

    def test_context_filter_fail(self, selector):
        """上下文窗口不足"""
        cap = selector.capabilities["model-a"]
        assert selector._is_eligible(cap, "chat", "easy", required_context=256000) is False

    def test_context_zero_no_filter(self, selector):
        """required_context 为 0 时不做上下文过滤"""
        cap = selector.capabilities["model-a"]
        assert selector._is_eligible(cap, "chat", "easy", required_context=0) is True


class TestModelSelectorSelect:
    """select 方法测试"""

    @pytest.fixture
    def selector(self):
        pool = {
            "capabilities": {
                "model-a": {
                    "difficulties": ["easy", "medium", "hard"],
                    "task_types": ["chat", "writing"],
                    "priority": 1,
                    "quality": 9,
                    "cost": 3,
                    "context": 128000
                },
                "model-b": {
                    "difficulties": ["easy", "medium"],
                    "task_types": ["chat"],
                    "priority": 2,
                    "quality": 6,
                    "cost": 9,
                    "context": 128000
                }
            },
            "default_model": "model-a"
        }
        return ModelSelector(pool)

    def test_select_auto_strategy(self, selector):
        """auto 策略按 priority 排序"""
        result = selector.select("chat", "easy", strategy="auto")
        assert result.model_name == "model-a"
        assert "priority" in result.reason

    def test_select_quality_strategy(self, selector):
        """quality 策略选择最高 quality"""
        result = selector.select("chat", "easy", strategy="quality")
        assert result.model_name == "model-a"
        assert "质量优先" in result.reason

    def test_select_cost_strategy(self, selector):
        """cost 策略选择最高 cost（最便宜）"""
        result = selector.select("chat", "easy", strategy="cost")
        assert result.model_name == "model-b"
        assert "成本优先" in result.reason

    def test_select_with_context_filter_fallback(self, selector):
        """上下文过滤导致无候选时回退到默认模型"""
        result = selector.select("chat", "easy", strategy="auto", required_context=256000)
        assert result.model_name == "model-a"  # 默认模型
        assert "上下文不足" in result.reason
        assert result.confidence == 0.3

    def test_select_no_candidates_task_mismatch(self, selector):
        """任务不匹配导致无候选时使用默认模型"""
        result = selector.select("coding", "easy", strategy="auto")
        assert result.model_name == "model-a"
        assert "无匹配模型" in result.reason

    def test_select_with_required_context(self, selector):
        """带上下文需求的成功选择"""
        result = selector.select("chat", "easy", strategy="auto", required_context=64000)
        assert result.model_name == "model-a"
        assert "上下文需求" in result.reason

    def test_select_returns_result_type(self, selector):
        """返回 ModelSelectionResult 类型"""
        result = selector.select("chat", "easy")
        assert isinstance(result, ModelSelectionResult)
        assert result.task_type == "chat"
        assert result.difficulty == "easy"

    def test_select_confidence_high(self, selector):
        """有候选时置信度为 0.9"""
        result = selector.select("chat", "easy")
        assert result.confidence == 0.9


class TestModelSelectorGetCandidates:
    """get_candidates 方法测试"""

    @pytest.fixture
    def selector(self):
        pool = {
            "capabilities": {
                "model-a": {
                    "difficulties": ["easy", "hard"],
                    "task_types": ["chat"],
                    "priority": 1,
                    "context": 128000
                },
                "model-b": {
                    "difficulties": ["easy"],
                    "task_types": ["chat"],
                    "priority": 2,
                    "context": 64000
                }
            }
        }
        return ModelSelector(pool)

    def test_get_candidates_basic(self, selector):
        """基本候选获取"""
        candidates = selector.get_candidates("chat", "easy")
        assert "model-a" in candidates
        assert "model-b" in candidates

    def test_get_candidates_difficulty_filter(self, selector):
        """难度过滤"""
        candidates = selector.get_candidates("chat", "hard")
        assert "model-a" in candidates
        assert "model-b" not in candidates

    def test_get_candidates_context_filter(self, selector):
        """上下文过滤"""
        candidates = selector.get_candidates("chat", "easy", required_context=100000)
        assert "model-a" in candidates
        assert "model-b" not in candidates

    def test_get_candidates_no_match(self, selector):
        """无匹配候选"""
        candidates = selector.get_candidates("coding", "easy")
        assert candidates == []
