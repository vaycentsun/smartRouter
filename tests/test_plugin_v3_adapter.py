"""Tests for SmartRouterV3Adapter — 覆盖 fallback 配置注入"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from smart_router.router.plugin_v3_adapter import SmartRouterV3Adapter


@pytest.fixture
def v3_config_dir():
    """创建完整的 V3 配置目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        
        # providers.yaml
        (config_dir / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: sk-test
    timeout: 30
""")
        
        # models.yaml
        (config_dir / "models.yaml").write_text("""
models:
  model-a:
    provider: openai
    litellm_model: openai/model-a
    capabilities:
      quality: 9
      speed: 8
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
    
  model-b:
    provider: openai
    litellm_model: openai/model-b
    capabilities:
      quality: 8
      speed: 7
      cost: 5
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
        
        # routing.yaml
        (config_dir / "routing.yaml").write_text("""
tasks:
  chat:
    name: "Chat"
    description: "General chat"
    capability_weights:
      quality: 0.5
      cost: 0.5

difficulties:
  easy:
    description: "Easy"
    max_tokens: 1000

strategies:
  auto:
    description: "Auto"

fallback:
  mode: auto
  similarity_threshold: 2
""")
        
        yield config_dir


class TestSmartRouterV3AdapterFallbacks:
    """测试 V3 Adapter 的 LiteLLM fallback 配置注入"""

    def test_fallbacks_passed_to_litellm_router(self, v3_config_dir):
        """SmartRouterV3Adapter 应将 Config 的 fallback 链转为 LiteLLM fallbacks 格式并传入 Router"""
        with patch('smart_router.router.plugin_v3_adapter.Router.__init__', return_value=None) as mock_super:
            SmartRouterV3Adapter(config_dir=v3_config_dir)
            
            call_kwargs = mock_super.call_args.kwargs
            assert "fallbacks" in call_kwargs, "fallbacks 参数应传入 Router.__init__"
            
            fallbacks = call_kwargs["fallbacks"]
            assert isinstance(fallbacks, list), "fallbacks 应为列表"
            assert len(fallbacks) > 0, "fallbacks 不应为空（存在 quality 差异 <=2 的模型）"
            
            # 验证格式: [{"model-a": ["model-b"]}]
            model_a_entry = next((f for f in fallbacks if "model-a" in f), None)
            assert model_a_entry is not None, "model-a 的 fallback 条目应存在"
            assert "model-b" in model_a_entry["model-a"], "model-a 的 fallback 链应包含 model-b"
