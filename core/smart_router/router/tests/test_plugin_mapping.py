"""Tests for SmartRouter model mapping support"""

from unittest.mock import patch

import pytest

from smart_router.config.schema import (
    Config,
    DifficultyConfig,
    FallbackConfig,
    ModelCapabilities,
    ModelConfig,
    ProviderConfig,
    RoutingConfig,
    StrategyConfig,
    TaskConfig,
)
from smart_router.router.plugin import SmartRouter


@pytest.fixture
def sample_config():
    """创建用于测试 SmartRouter 的 Config"""
    return Config(
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
                supported_tasks=["chat", "coding"],
                difficulty_support=["easy", "medium", "hard"]
            ),
        },
        routing=RoutingConfig(
            tasks={
                "chat": TaskConfig(
                    name="Chat",
                    description="General chat",
                    capability_weights={"quality": 0.6, "cost": 0.4}
                ),
            },
            difficulties={
                "easy": DifficultyConfig(description="Easy", max_tokens=2000),
            },
            strategies={
                "auto": StrategyConfig(description="Auto"),
            },
            fallback=FallbackConfig()
        )
    )


class TestSmartRouterModelMapping:
    """测试 SmartRouter 的模型映射功能"""

    def test_no_mapping_config_model_list_only_original_models(self, sample_config, tmp_path):
        """场景1: 无映射配置时，model_list 只包含原有模型"""
        with patch('smart_router.router.plugin.Router.__init__', return_value=None) as mock_super:
            router = SmartRouter(config=sample_config, config_dir=tmp_path)

            call_kwargs = mock_super.call_args.kwargs
            model_list = call_kwargs.get("model_list", [])
            model_names = [m["model_name"] for m in model_list]

            assert "gpt-4o" in model_names
            assert len(model_names) == 1

    def test_mapping_enabled_adds_virtual_models(self, sample_config, tmp_path):
        """场景2: 有映射配置且全局开关开启时，model_list 包含映射目标虚拟模型"""
        mapping_yaml = tmp_path / "model_mappings.yaml"
        mapping_yaml.write_text("""
enabled: true
mappings:
  - id: map_gpt4_to_claude
    enabled: true
    from_model: gpt-4o
    to_provider: anthropic
    to_model: claude-3-5-sonnet
    to_litellm_provider: anthropic
    to_base_url: https://api.anthropic.com/v1
    to_api_key: sk-anthropic-key
""")

        with patch('smart_router.router.plugin.Router.__init__', return_value=None) as mock_super:
            router = SmartRouter(config=sample_config, config_dir=tmp_path)

            call_kwargs = mock_super.call_args.kwargs
            model_list = call_kwargs.get("model_list", [])
            model_names = [m["model_name"] for m in model_list]

            assert "gpt-4o" in model_names
            assert "claude-3-5-sonnet" in model_names
            assert len(model_names) == 2

            # 验证虚拟模型的 litellm_params
            claude_entry = next(m for m in model_list if m["model_name"] == "claude-3-5-sonnet")
            assert claude_entry["litellm_params"]["model"] == "anthropic/claude-3-5-sonnet"
            assert claude_entry["litellm_params"]["api_base"] == "https://api.anthropic.com/v1"
            assert claude_entry["litellm_params"]["api_key"] == "sk-anthropic-key"
            assert claude_entry["litellm_params"]["timeout"] == 30

    def test_mapping_rule_disabled_not_in_model_list(self, sample_config, tmp_path):
        """场景3: 映射规则 enabled=false 时，不生成虚拟模型"""
        mapping_yaml = tmp_path / "model_mappings.yaml"
        mapping_yaml.write_text("""
enabled: true
mappings:
  - id: map_gpt4_to_claude
    enabled: false
    from_model: gpt-4o
    to_provider: anthropic
    to_model: claude-3-5-sonnet
    to_litellm_provider: anthropic
    to_base_url: https://api.anthropic.com/v1
    to_api_key: sk-anthropic-key
""")

        with patch('smart_router.router.plugin.Router.__init__', return_value=None) as mock_super:
            router = SmartRouter(config=sample_config, config_dir=tmp_path)

            call_kwargs = mock_super.call_args.kwargs
            model_list = call_kwargs.get("model_list", [])
            model_names = [m["model_name"] for m in model_list]

            assert "gpt-4o" in model_names
            assert "claude-3-5-sonnet" not in model_names
            assert len(model_names) == 1

    def test_reload_config_updates_model_mappings(self, sample_config, tmp_path):
        """场景4: reload_config 后，新的映射配置生效"""
        mapping_yaml = tmp_path / "model_mappings.yaml"
        mapping_yaml.write_text("""
enabled: true
mappings:
  - id: map_gpt4_to_claude
    enabled: true
    from_model: gpt-4o
    to_provider: anthropic
    to_model: claude-3-5-sonnet
    to_litellm_provider: anthropic
    to_base_url: https://api.anthropic.com/v1
    to_api_key: sk-anthropic-key
""")

        with patch('smart_router.router.plugin.Router.__init__', return_value=None) as mock_super:
            router = SmartRouter(config=sample_config, config_dir=tmp_path)
            # 从 super().__init__ 调用参数中获取初始 model_list
            call_kwargs = mock_super.call_args.kwargs
            initial_model_list = call_kwargs.get("model_list", [])
            router.model_list = list(initial_model_list)  # 手动设置

        # 验证初始状态包含映射模型
        initial_names = [m["model_name"] for m in router.model_list]
        assert "claude-3-5-sonnet" in initial_names

        # 更新映射配置：移除映射模型，添加新的
        mapping_yaml.write_text("""
enabled: true
mappings:
  - id: map_gpt4_to_gemini
    enabled: true
    from_model: gpt-4o
    to_provider: google
    to_model: gemini-pro
    to_litellm_provider: gemini
    to_base_url: https://generativelanguage.googleapis.com/v1
    to_api_key: sk-gemini-key
""")

        router.reload_config(sample_config)

        # 验证 reload 后新的映射生效
        new_names = [m["model_name"] for m in router.model_list]
        assert "claude-3-5-sonnet" not in new_names
        assert "gemini-pro" in new_names

    def test_mapping_api_key_resolves_env_var(self, sample_config, tmp_path, monkeypatch):
        """场景5: 映射目标的 api_key 正确解析环境变量"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "resolved-from-env")

        mapping_yaml = tmp_path / "model_mappings.yaml"
        mapping_yaml.write_text("""
enabled: true
mappings:
  - id: map_gpt4_to_claude
    enabled: true
    from_model: gpt-4o
    to_provider: anthropic
    to_model: claude-3-5-sonnet
    to_litellm_provider: anthropic
    to_base_url: https://api.anthropic.com/v1
    to_api_key: os.environ/ANTHROPIC_API_KEY
""")

        with patch('smart_router.router.plugin.Router.__init__', return_value=None) as mock_super:
            router = SmartRouter(config=sample_config, config_dir=tmp_path)

            call_kwargs = mock_super.call_args.kwargs
            model_list = call_kwargs.get("model_list", [])
            claude_entry = next(m for m in model_list if m["model_name"] == "claude-3-5-sonnet")
            assert claude_entry["litellm_params"]["api_key"] == "resolved-from-env"

    def test_mapping_global_disabled_no_virtual_models(self, sample_config, tmp_path):
        """全局开关关闭时，即使有规则也不生成虚拟模型"""
        mapping_yaml = tmp_path / "model_mappings.yaml"
        mapping_yaml.write_text("""
enabled: false
mappings:
  - id: map_gpt4_to_claude
    enabled: true
    from_model: gpt-4o
    to_provider: anthropic
    to_model: claude-3-5-sonnet
    to_litellm_provider: anthropic
    to_base_url: https://api.anthropic.com/v1
    to_api_key: sk-anthropic-key
""")

        with patch('smart_router.router.plugin.Router.__init__', return_value=None) as mock_super:
            router = SmartRouter(config=sample_config, config_dir=tmp_path)

            call_kwargs = mock_super.call_args.kwargs
            model_list = call_kwargs.get("model_list", [])
            model_names = [m["model_name"] for m in model_list]

            assert "claude-3-5-sonnet" not in model_names
            assert len(model_names) == 1
