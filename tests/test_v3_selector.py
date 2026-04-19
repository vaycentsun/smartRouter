"""Tests for V3 Model Selector"""

import pytest
from smart_router.selector.v3_selector import V3ModelSelector, NoModelAvailableError, UnknownStrategyError
from smart_router.config.v3_schema import ConfigV3


class TestV3ModelSelector:
    """Test V3 Model Selector"""
    
    @pytest.fixture
    def sample_config(self):
        """创建测试配置"""
        return ConfigV3(
            providers={
                "openai": {"api_base": "...", "api_key": "..."}
            },
            models={
                "gpt-4o": {
                    "provider": "openai",
                    "litellm_model": "openai/gpt-4o",
                    "capabilities": {"quality": 9, "speed": 8, "cost": 3, "context": 128000},
                    "supported_tasks": ["chat", "code_review"],
                    "difficulty_support": ["easy", "medium", "hard"]
                },
                "gpt-4o-mini": {
                    "provider": "openai",
                    "litellm_model": "openai/gpt-4o-mini",
                    "capabilities": {"quality": 6, "speed": 9, "cost": 9, "context": 128000},
                    "supported_tasks": ["chat"],
                    "difficulty_support": ["easy", "medium"]
                }
            },
            routing={
                "tasks": {
                    "chat": {
                        "name": "Chat",
                        "description": "General chat",
                        "capability_weights": {"quality": 0.5, "speed": 0.3, "cost": 0.2}
                    },
                    "code_review": {
                        "name": "Code Review",
                        "description": "Review code",
                        "capability_weights": {"quality": 0.7, "speed": 0.2, "cost": 0.1}
                    }
                },
                "difficulties": {
                    "easy": {"description": "Easy", "max_tokens": 1000},
                    "medium": {"description": "Medium", "max_tokens": 4000},
                    "hard": {"description": "Hard", "max_tokens": 8000}
                },
                "strategies": {
                    "auto": {"description": "Auto"},
                    "quality": {"description": "Quality"}
                },
                "fallback": {"mode": "auto", "similarity_threshold": 2}
            }
        )
    
    def test_auto_strategy(self, sample_config):
        """Test auto strategy selects best weighted model"""
        selector = V3ModelSelector(sample_config)
        
        # For chat: quality=0.5, speed=0.3, cost=0.2
        # gpt-4o: 9*0.5 + 8*0.3 + 3*0.2 = 4.5 + 2.4 + 0.6 = 7.5
        # gpt-4o-mini: 6*0.5 + 9*0.3 + 9*0.2 = 3.0 + 2.7 + 1.8 = 7.5
        result = selector.select("chat", "easy", "auto")
        
        assert result.strategy == "auto"
        assert result.score > 0
        assert result.model_name in ["gpt-4o", "gpt-4o-mini"]
    
    def test_quality_strategy(self, sample_config):
        """Test quality strategy selects highest quality"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "quality")
        
        assert result.model_name == "gpt-4o"  # quality=9 > 6
        assert result.strategy == "quality"
    
    def test_cost_strategy(self, sample_config):
        """Test cost strategy selects highest cost score (cheapest)"""
        selector = V3ModelSelector(sample_config)
        
        result = selector.select("chat", "easy", "cost")
        
        assert result.model_name == "gpt-4o-mini"  # cost=9 > 3
    
    def test_difficulty_filtering(self, sample_config):
        """Test difficulty filtering"""
        selector = V3ModelSelector(sample_config)
        
        # gpt-4o-mini doesn't support hard
        result = selector.select("chat", "hard", "auto")
        assert result.model_name == "gpt-4o"
    
    def test_task_type_filtering(self, sample_config):
        """Test task type filtering"""
        selector = V3ModelSelector(sample_config)
        
        # gpt-4o-mini doesn't support code_review
        result = selector.select("code_review", "medium", "auto")
        assert result.model_name == "gpt-4o"
    
    def test_no_model_available(self, sample_config):
        """Test error when no model supports task/difficulty"""
        selector = V3ModelSelector(sample_config)
        
        # Try non-existent task
        with pytest.raises(NoModelAvailableError):
            selector.select("unknown_task", "easy", "auto")
    
    def test_unknown_strategy(self, sample_config):
        """Test error on unknown strategy"""
        selector = V3ModelSelector(sample_config)
        
        with pytest.raises(UnknownStrategyError):
            selector.select("chat", "easy", "unknown_strategy")
    
    def test_get_available_models(self, sample_config):
        """Test get_available_models helper"""
        selector = V3ModelSelector(sample_config)
        
        models = selector.get_available_models("chat", "easy")
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        
        # For hard difficulty, only gpt-4o supports
        models = selector.get_available_models("chat", "hard")
        assert "gpt-4o" in models
        assert "gpt-4o-mini" not in models
