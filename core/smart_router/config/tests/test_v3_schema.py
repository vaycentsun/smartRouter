"""Tests for V3 Configuration Schema"""

import pytest
from pydantic import ValidationError

from smart_router.config import (
    ProviderConfig, 
    ModelCapabilities, 
    ModelConfig,
    TaskConfig,
    DifficultyConfig,
    StrategyConfig,
    FallbackConfig,
    RoutingConfig,
    Config,
    ConfigV3
)

class TestConfig:
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
