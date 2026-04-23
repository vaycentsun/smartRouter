"""集成测试 - V3 架构"""

import pytest
from pathlib import Path
import tempfile
import yaml

from smart_router.config.loader import ConfigLoader
from smart_router.config.schema import (
    Config, ProviderConfig, ModelConfig, ModelCapabilities,
    TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig, RoutingConfig
)
from smart_router.utils.markers import parse_markers
from smart_router.classifier.task_classifier import TaskTypeClassifier
from smart_router.classifier.difficulty_classifier import DifficultyClassifier
from smart_router.selector.v3_selector import V3ModelSelector


@pytest.fixture
def test_config():
    """创建测试用的 V3 配置"""
    return Config(
        providers={
            "openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test"),
            "anthropic": ProviderConfig(api_base="https://api.anthropic.com", api_key="sk-test")
        },
        models={
            "gpt-4o-mini": ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o-mini",
                capabilities=ModelCapabilities(quality=6, cost=9, context=128000),
                supported_tasks=["chat"],
                difficulty_support=["easy"]
            ),
            "gpt-4o": ModelConfig(
                provider="openai",
                litellm_model="openai/gpt-4o",
                capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
                supported_tasks=["chat", "writing", "code_review"],
                difficulty_support=["easy", "medium", "hard"]
            ),
            "claude-3-opus": ModelConfig(
                provider="anthropic",
                litellm_model="anthropic/claude-3-opus",
                capabilities=ModelCapabilities(quality=10, cost=2, context=200000),
                supported_tasks=["writing", "code_review"],
                difficulty_support=["medium", "hard"]
            )
        },
        routing=RoutingConfig(
            tasks={
                "chat": TaskConfig(name="Chat", description="General chat", capability_weights={"quality": 0.4, "cost": 0.6}),
                "writing": TaskConfig(name="Writing", description="Write articles", capability_weights={"quality": 0.6, "cost": 0.4}),
                "code_review": TaskConfig(name="Code Review", description="Review code", capability_weights={"quality": 0.7, "cost": 0.3})
            },
            difficulties={
                "easy": DifficultyConfig(description="Easy", max_tokens=2000),
                "medium": DifficultyConfig(description="Medium", max_tokens=8000),
                "hard": DifficultyConfig(description="Hard", max_tokens=16000)
            },
            strategies={
                "auto": StrategyConfig(description="Auto"),
                "quality": StrategyConfig(description="Quality")
            },
            fallback=FallbackConfig(similarity_threshold=2)
        )
    )


def test_stage_marker_parsing():
    """测试阶段标记解析"""
    messages = [{"role": "user", "content": "[stage:chat] 你好"}]
    markers = parse_markers(messages)
    assert markers.stage == "chat"
    assert markers.difficulty is None


def test_stage_with_difficulty_marker():
    """测试阶段和难度标记"""
    messages = [{"role": "user", "content": "[stage:code_review] [difficulty:hard] 审查代码"}]
    markers = parse_markers(messages)
    assert markers.stage == "code_review"
    assert markers.difficulty == "hard"


def test_config_load_from_yaml():
    """测试从 YAML 文件加载 V3 配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        
        (config_dir / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: sk-test
""")
        (config_dir / "models.yaml").write_text("""
models:
  test-model:
    provider: openai
    litellm_model: openai/test
    capabilities:
      quality: 5
      cost: 5
      context: 1000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
        (config_dir / "routing.yaml").write_text("""
tasks:
  chat:
    name: "Chat"
    description: "Test"
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
        
        loader = ConfigLoader(config_dir)
        config = loader.load()
        assert "test-model" in config.models


def test_full_routing_flow_with_markers(test_config):
    """测试带标记的完整路由流程"""
    messages = [{"role": "user", "content": "[stage:writing] [difficulty:hard] 写论文"}]
    
    # 1. 解析标记
    markers = parse_markers(messages)
    assert markers.stage == "writing"
    assert markers.difficulty == "hard"
    
    # 2. 使用 V3 选择器
    selector = V3ModelSelector(test_config)
    result = selector.select(task_type=markers.stage, difficulty=markers.difficulty, strategy="auto")
    
    # hard writing 应该选 claude-3-opus（唯一支持 hard + writing）
    assert result.model_name == "claude-3-opus"


def test_auto_classification_flow(test_config):
    """测试自动分类流程（无标记）"""
    # 短文本应该 easy chat
    messages = [{"role": "user", "content": "你好"}]
    
    # 1. 任务分类
    task_types_config = {
        "chat": {"keywords": ["你好", "hello"]},
        "writing": {"keywords": ["写", "write"]}
    }
    task_classifier = TaskTypeClassifier(task_types_config)
    task_result = task_classifier.classify(messages)
    
    assert task_result.task_type == "chat"
    
    # 2. 难度评估
    difficulty_classifier = DifficultyClassifier([
        {"condition": "length < 30", "difficulty": "easy", "priority": 1},
        {"condition": "length > 200", "difficulty": "hard", "priority": 1}
    ])
    difficulty_result = difficulty_classifier.classify("你好", task_type=task_result.task_type)
    
    assert difficulty_result.difficulty == "easy"
    
    # 3. 模型选择（V3）
    selector = V3ModelSelector(test_config)
    selection_result = selector.select(
        task_type=task_result.task_type,
        difficulty=difficulty_result.difficulty,
        strategy="auto"
    )
    
    # easy chat 应该选 gpt-4o-mini（成本更低，且支持 easy+chat）
    assert selection_result.model_name == "gpt-4o-mini"


def test_fallback_chain(test_config):
    """测试 fallback 链推导"""
    # gpt-4o (quality=9) 和 claude-3-opus (quality=10) 差异为 1 <= 2
    gpt4o_chain = test_config.get_fallback_chain("gpt-4o")
    assert "claude-3-opus" in gpt4o_chain


def test_difficulty_rules_priority():
    """测试难度规则优先级"""
    classifier = DifficultyClassifier([
        {"condition": "keyword:简单", "difficulty": "easy", "priority": 1},
        {"condition": "length > 100", "difficulty": "hard", "priority": 2}
    ])
    
    result = classifier.classify("简单" + "x" * 200)
    assert result.difficulty == "easy"
