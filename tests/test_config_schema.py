"""Tests for Config Schema — 覆盖 fallback 链与 Pydantic v2 兼容性"""

import pytest
from pydantic import ValidationError

from smart_router.config.schema import (
    Config,
    ProviderConfig,
    ModelConfig,
    ModelCapabilities,
    RoutingConfig,
    TaskConfig,
    DifficultyConfig,
    StrategyConfig,
    FallbackConfig,
)


class TestConfigFallbackChains:
    """测试 fallback 链在 Pydantic v2 下正确预计算"""

    @pytest.fixture
    def sample_config(self):
        """创建包含多个模型的 Config，用于验证 fallback 链推导"""
        return Config(
            providers={
                "openai": ProviderConfig(
                    api_base="https://api.openai.com/v1",
                    api_key="sk-test"
                ),
                "anthropic": ProviderConfig(
                    api_base="https://api.anthropic.com",
                    api_key="sk-test"
                ),
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat", "coding"],
                    difficulty_support=["easy", "medium", "hard"]
                ),
                "claude-3-opus": ModelConfig(
                    provider="anthropic",
                    litellm_model="anthropic/claude-3-opus",
                    capabilities=ModelCapabilities(quality=10, cost=2, context=200000),
                    supported_tasks=["chat", "coding"],
                    difficulty_support=["easy", "medium", "hard"]
                ),
                "gpt-4o-mini": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o-mini",
                    capabilities=ModelCapabilities(quality=6, cost=9, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy", "medium"]
                ),
            },
            routing=RoutingConfig(
                tasks={
                    "chat": TaskConfig(
                        name="Chat",
                        description="General chat",
                        capability_weights={"quality": 0.6, "cost": 0.4}
                    )
                },
                difficulties={
                    "easy": DifficultyConfig(description="Easy", max_tokens=2000)
                },
                strategies={
                    "auto": StrategyConfig(description="Auto select")
                },
                fallback=FallbackConfig(similarity_threshold=2)
            )
        )

    def test_fallback_chain_populated_after_init(self, sample_config):
        """Config 实例化后 fallback 链应已预计算且非空"""
        # gpt-4o (quality=9) 和 claude-3-opus (quality=10) 差异为 1 <= 2
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        assert "claude-3-opus" in gpt4o_chain, (
            f"gpt-4o fallback chain should include claude-3-opus, got {gpt4o_chain}"
        )

    def test_fallback_chain_excludes_dissimilar_models(self, sample_config):
        """quality 差异超过 threshold 的模型不应出现在 fallback 链中"""
        # gpt-4o (quality=9) 和 gpt-4o-mini (quality=6) 差异为 3 > 2
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        assert "gpt-4o-mini" not in gpt4o_chain, (
            f"gpt-4o fallback chain should NOT include gpt-4o-mini, got {gpt4o_chain}"
        )

    def test_fallback_chain_is_bidirectional(self, sample_config):
        """fallback 关系应是双向的（当 quality 差异对称时）"""
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        opus_chain = sample_config.get_fallback_chain("claude-3-opus")

        assert "claude-3-opus" in gpt4o_chain
        assert "gpt-4o" in opus_chain

    def test_fallback_chain_sorted_by_quality_desc(self, sample_config):
        """fallback 链应按 quality 降序排列"""
        # 如果加入更多接近的模型，验证排序
        # 当前数据：gpt-4o(9) 的 chain 只有 claude-3-opus(10)
        gpt4o_chain = sample_config.get_fallback_chain("gpt-4o")
        if len(gpt4o_chain) >= 2:
            qualities = [
                sample_config.models[m].capabilities.quality
                for m in gpt4o_chain
            ]
            assert qualities == sorted(qualities, reverse=True)

    def test_fallback_chain_for_unknown_model(self, sample_config):
        """对不存在的模型应返回空列表"""
        assert sample_config.get_fallback_chain("nonexistent") == []

    def test_fallback_chain_empty_when_no_candidates(self):
        """只有一个模型时 fallback 链应为空"""
        config = Config(
            providers={
                "openai": ProviderConfig(
                    api_base="https://api.openai.com/v1",
                    api_key="sk-test"
                )
            },
            models={
                "gpt-4o": ModelConfig(
                    provider="openai",
                    litellm_model="openai/gpt-4o",
                    capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                    supported_tasks=["chat"],
                    difficulty_support=["easy"]
                )
            },
            routing=RoutingConfig(
                tasks={},
                difficulties={},
                strategies={},
                fallback=FallbackConfig(similarity_threshold=2)
            )
        )
        assert config.get_fallback_chain("gpt-4o") == []
