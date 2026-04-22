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
        """Test creating valid ModelCapabilities"""
        caps = ModelCapabilities(
            quality=9,
            speed=8,
            cost=3,
            context=128000
        )
        
        assert caps.quality == 9
        assert caps.speed == 8
        assert caps.cost == 3
        assert caps.context == 128000
    
    def test_quality_range_validation(self):
        """Test quality must be 1-10"""
        # Too low
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=0, speed=5, cost=5, context=1000)
        
        # Too high
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=11, speed=5, cost=5, context=1000)
    
    def test_speed_range_validation(self):
        """Test speed must be 1-10"""
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, speed=0, cost=5, context=1000)
        
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, speed=15, cost=5, context=1000)
    
    def test_cost_range_validation(self):
        """Test cost must be 1-10"""
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, speed=5, cost=-1, context=1000)
        
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, speed=5, cost=100, context=1000)
    
    def test_context_must_be_positive(self):
        """Test context must be positive"""
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, speed=5, cost=5, context=0)
        
        with pytest.raises(ValidationError):
            ModelCapabilities(quality=5, speed=5, cost=5, context=-1000)


class TestModelConfig:
    """Test ModelConfig Schema"""
    
    def test_valid_model_config(self):
        """Test creating valid ModelConfig"""
        config = ModelConfig(
            provider="openai",
            litellm_model="openai/gpt-4o",
            capabilities=ModelCapabilities(
                quality=9, speed=8, cost=3, context=128000
            ),
            supported_tasks=["chat", "code_review"],
            difficulty_support=["easy", "medium", "hard"]
        )
        
        assert config.provider == "openai"
        assert config.litellm_model == "openai/gpt-4o"
        assert config.capabilities.quality == 9
        assert config.supported_tasks == ["chat", "code_review"]
        assert config.difficulty_support == ["easy", "medium", "hard"]
    
    def test_difficulty_must_be_valid_literal(self):
        """Test difficulty must be easy/medium/hard/expert (4 levels)"""
        with pytest.raises(ValidationError):
            ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o",
                capabilities=ModelCapabilities(
                    quality=9, speed=8, cost=3, context=128000
                ),
                supported_tasks=["chat"],
                difficulty_support=["easy", "invalid"]  # Invalid
            )
    
    def test_all_difficulty_levels(self):
        """Test all 4 valid difficulty levels"""
        config = ModelConfig(
            provider="openai",
            litellm_model="openai/gpt-4o",
            capabilities=ModelCapabilities(
                quality=9, speed=8, cost=3, context=128000
            ),
            supported_tasks=["chat"],
            difficulty_support=["easy", "medium", "hard", "expert"]
        )
        assert config.difficulty_support == ["easy", "medium", "hard", "expert"]
    
    def test_model_with_single_difficulty(self):
        """Test model supporting only one difficulty"""
        config = ModelConfig(
            provider="openai",
            litellm_model="openai/gpt-4o-mini",
            capabilities=ModelCapabilities(
                quality=6, speed=9, cost=9, context=128000
            ),
            supported_tasks=["chat"],
            difficulty_support=["easy"]  # Only easy
        )
        
        assert config.difficulty_support == ["easy"]


class TestTaskConfig:
    """Test TaskConfig Schema"""
    
    def test_valid_task_config(self):
        """Test creating valid TaskConfig"""
        config = TaskConfig(
            name="Code Review",
            description="Review code quality",
            capability_weights={
                "quality": 0.6,
                "speed": 0.2,
                "cost": 0.2
            }
        )
        
        assert config.name == "Code Review"
        assert config.capability_weights["quality"] == 0.6
    
    def test_weights_must_sum_to_approximately_1(self):
        """Test capability_weights should sum to ~1.0"""
        # Valid - sums to 1.0
        TaskConfig(
            name="Test",
            description="Test",
            capability_weights={"quality": 0.5, "speed": 0.3, "cost": 0.2}
        )
        
        # Invalid - sums to 1.5
        with pytest.raises(ValidationError):
            TaskConfig(
                name="Test",
                description="Test",
                capability_weights={"quality": 1.0, "speed": 0.3, "cost": 0.2}
            )


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
    """Test FallbackConfig Schema"""
    
    def test_default_fallback_config(self):
        """Test FallbackConfig defaults"""
        config = FallbackConfig()
        
        assert config.mode == "auto"
        assert config.similarity_threshold == 2
    
    def test_custom_threshold(self):
        """Test FallbackConfig with custom threshold"""
        config = FallbackConfig(similarity_threshold=3)
        assert config.similarity_threshold == 3
    
    def test_threshold_range_validation(self):
        """Test similarity_threshold must be 1-5"""
        with pytest.raises(ValidationError):
            FallbackConfig(similarity_threshold=0)
        
        with pytest.raises(ValidationError):
            FallbackConfig(similarity_threshold=10)


class TestRoutingConfig:
    """Test RoutingConfig Schema"""
    
    def test_valid_routing_config(self):
        """Test creating valid RoutingConfig"""
        config = RoutingConfig(
            tasks={
                "chat": TaskConfig(
                    name="Chat",
                    description="General chat",
                    capability_weights={"quality": 0.4, "speed": 0.4, "cost": 0.2}
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


class TestConfigV3:
    """Test ConfigV3 (Aggregate Root)"""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample valid ConfigV3"""
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
                        quality=9, speed=8, cost=3, context=128000
                    ),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium", "hard"]
                ),
                "claude-3-opus": ModelConfig(
                    provider="anthropic",
                    litellm_model="anthropic/claude-3-opus-20240229",
                    capabilities=ModelCapabilities(
                        quality=10, speed=4, cost=2, context=200000
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
                        capability_weights={"quality": 0.5, "speed": 0.3, "cost": 0.2}
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
        """Test creating valid ConfigV3"""
        assert "openai" in sample_config.providers
        assert "gpt-4o" in sample_config.models
        assert "chat" in sample_config.routing.tasks
    
    def test_provider_reference_validation(self):
        """Test that model providers must exist in providers dict"""
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
                        provider="nonexistent",  # Invalid provider
                        litellm_model="openai/gpt-4o",
                        capabilities=ModelCapabilities(
                            quality=9, speed=8, cost=3, context=128000
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
        """Test automatic fallback chain derivation (only available models)"""
        # 设置环境变量使模型可用
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-test")
        
        # gpt-4o (quality=9) and claude-3-opus (quality=10) differ by 1 <= 2
        # They should be in each other's fallback chain
        
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        assert "claude-3-opus" in gpt4o_chain
        
        opus_chain = sample_config.get_fallback_chain("claude-3-opus")
        assert "gpt-4o" in opus_chain
    
    def test_fallback_chain_filters_unavailable(self, sample_config):
        """Test that fallback chain excludes unavailable models (no API key set)"""
        # 不设置环境变量，所有模型都不可用
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        assert gpt4o_chain == []  # claude-3-opus 不可用，不应出现在 fallback 链中
        
        opus_chain = sample_config.get_fallback_chain("claude-3-opus")
        assert opus_chain == []
    
    def test_litellm_params_generation(self, sample_config, monkeypatch):
        """Test LiteLLM params generation"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        
        params = sample_config.get_litellm_params("gpt-4o")
        
        assert params["model"] == "openai/gpt-4o"
        assert params["api_key"] == "sk-openai-test"
        assert params["api_base"] == "https://api.openai.com/v1"
        assert params["timeout"] == 30
    
    def test_litellm_params_with_direct_key(self, sample_config):
        """Test LiteLLM params with direct API key (not env var)"""
        # Update provider to use direct key
        sample_config.providers["openai"].api_key = "sk-direct-key"
        
        params = sample_config.get_litellm_params("gpt-4o")
        assert params["api_key"] == "sk-direct-key"
