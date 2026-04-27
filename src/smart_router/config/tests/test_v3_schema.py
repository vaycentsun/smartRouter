"""Tests for V3 Configuration Schema"""

import pytest
from pydantic import ValidationError

from smart_router.config.v3_schema import (
    ProviderConfig, 
    ModelCapabilities, 
    ModelConfig,
    TaskConfig,
    DifficultyConfig,
    StrategyConfig,
    FallbackConfig,
    RoutingConfig,
    ConfigV3
)


class TestProviderConfig:
    """Test ProviderConfig Schema"""
    
    def test_valid_provider_config(self):
        """Test creating valid ProviderConfig"""
        config = ProviderConfig(
            api_base="https://api.openai.com/v1",
            api_key="os.environ/OPENAI_API_KEY"
        )
        
        assert config.api_base == "https://api.openai.com/v1"
        assert config.api_key == "os.environ/OPENAI_API_KEY"
        assert config.timeout == 30  # 默认值
        assert config.default_headers == {}  # 默认值
        assert config.rate_limit is None
    
    def test_provider_with_all_fields(self):
        """Test ProviderConfig with all fields specified"""
        config = ProviderConfig(
            api_base="https://api.anthropic.com",
            api_key="sk-direct-key",
            timeout=60,
            default_headers={"X-Custom": "header"},
            rate_limit=100
        )
        
        assert config.timeout == 60
        assert config.default_headers == {"X-Custom": "header"}
        assert config.rate_limit == 100
    
    def test_direct_api_key(self):
        """Test ProviderConfig with direct API key (not env var)"""
        config = ProviderConfig(
            api_base="https://api.example.com",
            api_key="sk-direct-api-key"
        )
        
        assert config.api_key == "sk-direct-api-key"


class TestModelCapabilities:
    """Test ModelCapabilities Schema"""
    
    def test_valid_capabilities(self):
        caps = ModelCapabilities(
            quality=9,
            cost=3,
            context=128000
        )
        
        assert caps.quality == 9
        assert caps.cost == 3
        assert caps.context == 128000
    
    def test_valid_capabilities_with_new_dimensions(self):
        caps = ModelCapabilities(
            quality=9,
            cost=3,
            context=256000,
            reasoning=10,
            creative=8,
            vision=True,
            long_context=True,
            latest=True
        )
        
        assert caps.quality == 9
        assert caps.reasoning == 10
        assert caps.creative == 8
        assert caps.vision == True
        assert caps.long_context == True
        assert caps.latest == True
    
    def test_default_vision_is_false(self):
        caps = ModelCapabilities(quality=5, cost=5, context=8000)
        assert caps.vision == False
    
    def test_default_long_context_is_false(self):
        caps = ModelCapabilities(quality=5, cost=5, context=8000)
        assert caps.long_context == False
    
    def test_default_latest_is_true(self):
        caps = ModelCapabilities(quality=5, cost=5, context=8000)
        assert caps.latest == True
    
    def test_quality_range_validation(self):
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=0, cost=5, context=1000)
        
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=11, cost=5, context=1000)
    
    def test_cost_range_validation(self):
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, cost=-1, context=1000)
        
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, cost=100, context=1000)
    
    def test_context_must_be_positive(self):
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, cost=5, context=0)
        
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, cost=5, context=-1000)
    
    def test_reasoning_optional(self):
        caps = ModelCapabilities(quality=5, cost=5, context=8000)
        assert caps.reasoning is None
    
    def test_reasoning_range_validation(self):
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, cost=5, context=8000, reasoning=0)
        
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, cost=5, context=8000, reasoning=11)


class TestModelConfig:
    def test_valid_model_config(self):
        config = ModelConfig(
            provider="openai",
            litellm_model="openai/gpt-4o",
            capabilities=ModelCapabilities(
                quality=9, cost=3, context=128000
            ),
            supported_tasks=["chat", "code_review"],
            difficulty_support=["easy", "medium", "hard"]
        )
        
        assert config.provider == "openai"
        assert config.litellm_model == "openai/gpt-4o"
        assert config.capabilities.quality == 9
        assert config.supported_tasks == ["chat", "code_review"]
        assert config.difficulty_support == ["easy", "medium", "hard"]
    
    def test_model_with_new_capabilities(self):
        config = ModelConfig(
            provider="anthropic",
            litellm_model="anthropic/claude-3-opus",
            capabilities=ModelCapabilities(
                quality=10, cost=2, context=200000,
                reasoning=10, creative=10, vision=True, 
                long_context=True, latest=False
            ),
            supported_tasks=["coding", "reasoning"],
            difficulty_support=["medium", "hard", "expert"]
        )
        
        assert config.capabilities.reasoning == 10
        assert config.capabilities.creative == 10
        assert config.capabilities.vision == True
        assert config.capabilities.long_context == True
        assert config.capabilities.latest == False
    
    def test_difficulty_must_be_valid_literal(self):
        with pytest.raises(ValidationError):
            ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o",
                capabilities=ModelCapabilities(
                    quality=9, cost=3, context=128000
                ),
                supported_tasks=["chat"],
                difficulty_support=["easy", "invalid"]
            )
    
    def test_all_difficulty_levels(self):
        config = ModelConfig(
            provider="openai",
            litellm_model="openai/gpt-4o",
            capabilities=ModelCapabilities(
                quality=9, cost=3, context=128000
            ),
            supported_tasks=["chat"],
            difficulty_support=["easy", "medium", "hard", "expert"]
        )
        assert config.difficulty_support == ["easy", "medium", "hard", "expert"]
    
    def test_model_with_single_difficulty(self):
        config = ModelConfig(
            provider="openai",
            litellm_model="openai/gpt-4o-mini",
            capabilities=ModelCapabilities(
                quality=6, cost=9, context=128000
            ),
            supported_tasks=["chat"],
            difficulty_support=["easy"]
        )
        
        assert config.difficulty_support == ["easy"]


class TestTaskConfig:
    def test_valid_task_config(self):
        config = TaskConfig(
            name="Code Review",
            description="Review code quality",
            capability_weights={
                "quality": 0.6,
                "cost": 0.4
            }
        )
        
        assert config.name == "Code Review"
        assert config.capability_weights["quality"] == 0.6
    
    def test_weights_must_sum_to_approximately_1(self):
        TaskConfig(
            name="Test",
            description="Test",
            capability_weights={"quality": 0.5, "cost": 0.5}
        )
        
        with pytest.raises(ValidationError):
            TaskConfig(
                name="Test",
                description="Test",
                capability_weights={"quality": 1.0, "cost": 0.5}
            )
    
    def test_default_weights(self):
        config = TaskConfig(
            name="Writing",
            description="Content writing",
            capability_weights={"quality": 0.6, "cost": 0.4}
        )
        assert config.capability_weights["quality"] == 0.6
        assert config.capability_weights["cost"] == 0.4


class TestDifficultyConfig:
    """Test DifficultyConfig Schema"""
    
    def test_valid_difficulty_config(self):
        """Test creating valid DifficultyConfig"""
        config = DifficultyConfig(
            description="Simple tasks",
            max_tokens=2000
        )
        
        assert config.description == "Simple tasks"
        assert config.max_tokens == 2000


class TestStrategyConfig:
    """Test StrategyConfig Schema"""
    
    def test_valid_strategy_config(self):
        """Test creating valid StrategyConfig"""
        config = StrategyConfig(
            description="Quality priority"
        )
        
        assert config.description == "Quality priority"


class TestFallbackConfig:
    def test_default_fallback_config(self):
        config = FallbackConfig()
        
        assert config.mode == "auto"
        assert config.similarity_threshold == 2
    
    def test_intelligent_mode(self):
        config = FallbackConfig(mode="intelligent", provider_isolation=True)
        assert config.mode == "intelligent"
        assert config.provider_isolation == True
    
    def test_provider_isolation_default_false(self):
        config = FallbackConfig()
        assert config.provider_isolation == False
    
    def test_max_attempts_default(self):
        config = FallbackConfig()
        assert config.max_attempts == 3
    
    def test_custom_threshold(self):
        config = FallbackConfig(similarity_threshold=3)
        assert config.similarity_threshold == 3
    
    def test_threshold_range_validation(self):
        with pytest.raises(ValidationError):
            FallbackConfig(similarity_threshold=0)
        
        with pytest.raises(ValidationError):
            FallbackConfig(similarity_threshold=10)


class TestRoutingConfig:
    def test_valid_routing_config(self):
        config = RoutingConfig(
            tasks={
                "chat": TaskConfig(
                    name="Chat",
                    description="General chat",
                    capability_weights={"quality": 0.4, "cost": 0.6}
                )
            },
            difficulties={
                "easy": DifficultyConfig(description="Easy", max_tokens=1000)
            },
            strategies={
                "auto": StrategyConfig(description="Auto select")
            },
            fallback=FallbackConfig()
        )
        
        assert "chat" in config.tasks
        assert "easy" in config.difficulties
        assert "auto" in config.strategies
        assert config.fallback.mode == "auto"
    
    def test_routing_with_intelligent_fallback(self):
        config = RoutingConfig(
            tasks={},
            difficulties={},
            strategies={},
            fallback=FallbackConfig(
                mode="intelligent",
                provider_isolation=True,
                max_attempts=5
            )
        )
        
        assert config.fallback.mode == "intelligent"
        assert config.fallback.provider_isolation == True
        assert config.fallback.max_attempts == 5


class TestConfigV3:
    @pytest.fixture
    def sample_config(self):
        return ConfigV3(
            providers={
                "openai": ProviderConfig(
                    api_base="https://api.openai.com/v1",
                    api_key="os.environ/OPENAI_API_KEY"
                ),
                "anthropic": ProviderConfig(
                    api_base="https://api.anthropic.com",
                    api_key="os.environ/ANTHROPIC_API_KEY"
                )
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(
                        quality=9, cost=3, context=128000,
                        reasoning=9, creative=8, vision=True,
                        long_context=True, latest=True
                    ),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium", "hard"]
                ),
                "claude-3-opus": ModelConfig(
                    provider="anthropic",
                    litellm_model="anthropic/claude-3-opus-20240229",
                    capabilities=ModelCapabilities(
                        quality=10, cost=2, context=200000,
                        reasoning=10, creative=10, vision=True,
                        long_context=True, latest=False
                    ),
                    supported_tasks=["chat"],
                    difficulty_support=["medium", "hard"]
                )
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.5, "cost": 0.5}
                    )
                },
                difficulties={
                    "easy": DifficultyConfig(description="Easy", max_tokens=1000)
                },
                strategies={
                    "auto": StrategyConfig(description="Auto select")
                },
                fallback=FallbackConfig(similarity_threshold=2)
            )
        )
    
    def test_valid_config_v3(self, sample_config):
        assert "openai" in sample_config.providers
        assert "gpt-4o" in sample_config.models
        assert "chat" in sample_config.routing.tasks
    
    def test_provider_reference_validation(self):
        with pytest.raises(ValidationError) as exc_info:
            ConfigV3(
                providers={
                    "openai": ProviderConfig(
                        api_base="https://api.openai.com/v1",
                        api_key="sk-test"
                    )
                },
                models={
                    "gpt-4o": ModelConfig(
                        provider="nonexistent",
                        litellm_model="openai/gpt-4o",
                        capabilities=ModelCapabilities(
                            quality=9, cost=3, context=128000
                        ),
                        supported_tasks=["chat"],
                        difficulty_support=["easy"]
                    )
                },
                routing=RoutingConfig(
                    tasks={},
                    difficulties={},
                    strategies={},
                    fallback=FallbackConfig()
                )
            )
        
        assert "unknown provider" in str(exc_info.value).lower()
    
    def test_fallback_chain_derivation(self, sample_config, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-test")
        
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        assert "claude-3-opus" in gpt4o_chain
        
        opus_chain = sample_config.get_fallback_chain("claude-3-opus")
        assert "gpt-4o" in opus_chain
    
    def test_fallback_chain_filters_unavailable(self, sample_config):
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        assert gpt4o_chain == []
    
    def test_litellm_params_generation(self, sample_config, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        
        params = sample_config.get_litellm_params("gpt-4o")
        
        assert params["model"] == "openai/gpt-4o"
        assert params["api_key"] == "sk-openai-test"
        assert params["api_base"] == "https://api.openai.com/v1"
        assert params["timeout"] == 30
    
    def test_litellm_params_with_direct_key(self, sample_config):
        sample_config.providers["openai"].api_key = "sk-direct-key"
        
        params = sample_config.get_litellm_params("gpt-4o")
        assert params["api_key"] == "sk-direct-key"
    
    def test_get_provider_fallback_chain(self, sample_config, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-test")
        
        chain = sample_config.get_provider_fallback_chain("gpt-4o")
        assert "claude-3-opus" in chain
    
    def test_get_provider_fallback_chain_different_provider_priority(self, sample_config, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-test")
        
        chain = sample_config.get_provider_fallback_chain("gpt-4o")
        first_provider = sample_config.models[chain[0]].provider
        assert first_provider == "anthropic"

    def test_get_provider_fallback_chain_unknown_model(self, sample_config):
        """不存在的模型名返回空列表"""
        chain = sample_config.get_provider_fallback_chain("nonexistent-model")
        assert chain == []

    def test_is_provider_available_unknown_provider(self, sample_config):
        """不存在的 provider 返回 False"""
        assert sample_config.is_provider_available("nonexistent-provider") is False

    def test_is_provider_available_env_var_not_set(self, sample_config):
        """环境变量未设置时返回 False"""
        sample_config.providers["openai"].api_key = "os.environ/UNSET_VAR_12345"
        assert sample_config.is_provider_available("openai") is False

    def test_is_model_available_unknown_model(self, sample_config):
        """不存在的模型返回 False"""
        assert sample_config.is_model_available("nonexistent-model") is False

    def test_get_litellm_params_env_not_set(self, sample_config):
        """环境变量未设置时 api_key 为空字符串"""
        sample_config.providers["openai"].api_key = "os.environ/UNSET_VAR_12345"
        params = sample_config.get_litellm_params("gpt-4o")
        assert params["api_key"] == ""
