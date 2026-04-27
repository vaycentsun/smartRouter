"""V3 Integration Tests

测试完整流程：加载配置 → 选择模型 → 生成 LiteLLM 参数
"""

import pytest
import tempfile
from pathlib import Path

from smart_router.config import Config, ConfigLoader
from smart_router.selector.v3_selector import V3ModelSelector


class TestV3Integration:
    """V3 集成测试"""
    
    @pytest.fixture
    def complete_config_dir(self):
        """创建完整的 V3 配置目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            
            # providers.yaml
            (config_dir / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY
    timeout: 30
    
  anthropic:
    api_base: https://api.anthropic.com
    api_key: os.environ/ANTHROPIC_API_KEY
    timeout: 30
""")
            
            # models.yaml
            (config_dir / "models.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      speed: 8
      cost: 3
      context: 128000
    supported_tasks: [chat, code_review]
    difficulty_support: [easy, medium, hard]
    
  claude-3-opus:
    provider: anthropic
    litellm_model: anthropic/claude-3-opus-20240229
    capabilities:
      quality: 10
      speed: 4
      cost: 2
      context: 200000
    supported_tasks: [code_review]
    difficulty_support: [medium, hard]
""")
            
            # routing.yaml
            (config_dir / "routing.yaml").write_text("""
tasks:
  chat:
    name: "Chat"
    description: "General chat"
    capability_weights:
      quality: 0.5
      speed: 0.3
      cost: 0.2
      
  code_review:
    name: "Code Review"
    description: "Review code"
    capability_weights:
      quality: 0.7
      speed: 0.2
      cost: 0.1

difficulties:
  easy:
    description: "Easy"
    max_tokens: 1000
  medium:
    description: "Medium"
    max_tokens: 4000
  hard:
    description: "Hard"
    max_tokens: 8000

strategies:
  auto:
    description: "Auto"
  quality:
    description: "Quality"

fallback:
  mode: auto
  similarity_threshold: 2
""")
            
            yield config_dir
    
    def test_full_flow(self, complete_config_dir, monkeypatch):
        """测试完整流程"""
        # 设置环境变量
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-test")
        
        # 1. 加载配置
        loader = ConfigLoader(complete_config_dir)
        config = loader.load()
        
        assert isinstance(config, Config)
        assert "gpt-4o" in config.models
        assert "claude-3-opus" in config.models
        
        # 2. 测试模型选择
        selector = V3ModelSelector(config)
        
        # chat 任务选择
        result = selector.select("chat", "medium", "auto")
        assert result.model_name == "gpt-4o"  # 唯一支持 chat 的
        
        # code_review 任务选择
        result = selector.select("code_review", "hard", "quality")
        assert result.model_name == "claude-3-opus"  # quality=10 > 9
        
        # 3. 测试 LiteLLM 参数生成
        params = config.get_litellm_params("gpt-4o")
        assert params["model"] == "openai/gpt-4o"
        assert params["api_key"] == "sk-openai-test"
        assert params["api_base"] == "https://api.openai.com/v1"
        
        params = config.get_litellm_params("claude-3-opus")
        assert params["model"] == "anthropic/claude-3-opus-20240229"
        assert params["api_key"] == "sk-anthropic-test"
        
        # 4. 测试 fallback 推导
        # gpt-4o (quality=9) 和 claude-3-opus (quality=10) 差异为 1 <= 2
        gpt4o_fallback = config.get_fallback_chain("gpt-4o")
        assert "claude-3-opus" in gpt4o_fallback
        
        opus_fallback = config.get_fallback_chain("claude-3-opus")
        assert "gpt-4o" in opus_fallback
    
    def test_end_to_end_model_selection_scenarios(self, complete_config_dir):
        """测试端到端场景"""
        loader = ConfigLoader(complete_config_dir)
        config = loader.load()
        selector = V3ModelSelector(config)
        
        scenarios = [
            # (task, difficulty, strategy, expected)
            ("chat", "easy", "auto", "gpt-4o"),
            ("chat", "hard", "quality", "gpt-4o"),
            # auto 按 capability_weights (quality 0.7 + cost 0.1) 计算:
            # gpt-4o: 9*0.7 + 3*0.1 = 6.6
            # claude-3-opus: 10*0.7 + 2*0.1 = 7.2
            ("code_review", "medium", "auto", "claude-3-opus"),
            ("code_review", "hard", "quality", "claude-3-opus"),
        ]
        
        for task, difficulty, strategy, expected in scenarios:
            result = selector.select(task, difficulty, strategy)
            assert result.model_name == expected, \
                f"Failed for {task}/{difficulty}/{strategy}"
