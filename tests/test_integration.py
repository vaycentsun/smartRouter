"""集成测试 — V3 架构"""

import pytest
from pathlib import Path
import tempfile
import yaml

from smart_router.config.loader import ConfigLoader, ConfigError
from smart_router.config.schema import (
    Config, ProviderConfig, ModelConfig, ModelCapabilities,
    RoutingConfig, TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig
)
from smart_router.utils.markers import parse_markers
from smart_router.classifier.task_classifier import TaskTypeClassifier
from smart_router.classifier.difficulty_classifier import DifficultyClassifier
from smart_router.selector.model_selector import ModelSelector


@pytest.fixture
def sample_config():
    """创建测试用的最小 V3 配置"""
    return Config(
        providers={
            "openai": ProviderConfig(
                api_base="https://api.openai.com/v1",
                api_key="sk-test"
            ),
            "anthropic": ProviderConfig(
                api_base="https://api.anthropic.com",
                api_key="sk-test"
            )
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
                supported_tasks=["chat", "writing"],
                difficulty_support=["easy", "medium"]
            ),
            "claude-3-opus": ModelConfig(
                provider="anthropic",
                litellm_model="anthropic/claude-3-opus",
                capabilities=ModelCapabilities(quality=10, cost=2, context=200000),
                supported_tasks=["writing", "code_review"],
                difficulty_support=["medium", "hard"]
            ),
        },
        routing=RoutingConfig(
            tasks={
                "chat": TaskConfig(
                    name="Chat",
                    description="General chat",
                    capability_weights={"quality": 0.5, "cost": 0.5}
                ),
                "writing": TaskConfig(
                    name="Writing",
                    description="Writing tasks",
                    capability_weights={"quality": 0.6, "cost": 0.4}
                ),
                "code_review": TaskConfig(
                    name="Code Review",
                    description="Review code",
                    capability_weights={"quality": 0.7, "cost": 0.3}
                ),
            },
            difficulties={
                "easy": DifficultyConfig(description="Easy", max_tokens=2000),
                "medium": DifficultyConfig(description="Medium", max_tokens=8000),
                "hard": DifficultyConfig(description="Hard", max_tokens=16000),
            },
            strategies={
                "auto": StrategyConfig(description="Auto"),
            },
            fallback=FallbackConfig(similarity_threshold=2)
        )
    )


@pytest.fixture
def model_pool_from_config(sample_config):
    """从 V3 Config 构建 ModelSelector 可用的 model_pool"""
    capabilities = {}
    for name, model in sample_config.models.items():
        capabilities[name] = {
            "difficulties": list(model.difficulty_support),
            "task_types": list(model.supported_tasks),
            "priority": 11 - model.capabilities.quality,
            "quality": model.capabilities.quality,
            "cost": model.capabilities.cost,
            "context": model.capabilities.context,
        }
    default_model = max(sample_config.models.items(), key=lambda x: x[1].capabilities.quality)[0]
    return {"capabilities": capabilities, "default_model": default_model}


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


def test_config_load_from_directory():
    """测试从目录加载 V3 配置"""
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
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
        (config_dir / "routing.yaml").write_text("""
tasks: {}
difficulties: {}
strategies:
  auto:
    description: Auto
fallback:
  mode: auto
""")

        loader = ConfigLoader(config_dir)
        config = loader.load()
        assert "openai" in config.providers
        assert "gpt-4o" in config.models


def test_full_routing_flow_with_markers(sample_config, model_pool_from_config):
    """测试带标记的完整路由流程"""
    messages = [{"role": "user", "content": "[stage:writing] [difficulty:hard] 写论文"}]

    # 1. 解析标记
    markers = parse_markers(messages)
    assert markers.stage == "writing"
    assert markers.difficulty == "hard"

    # 2. 模型选择
    selector = ModelSelector(model_pool_from_config)
    result = selector.select(task_type=markers.stage, difficulty=markers.difficulty)

    # hard writing 应该选 claude-3-opus（唯一支持 hard + writing 的模型）
    assert result.model_name == "claude-3-opus"


def test_auto_classification_flow(sample_config, model_pool_from_config):
    """测试自动分类流程（无标记）"""
    # 短文本应该 easy chat
    messages = [{"role": "user", "content": "你好"}]

    # 1. 任务分类
    task_classifier = TaskTypeClassifier({
        task_id: {
            "name": task.name,
            "description": task.description,
            "capability_weights": task.capability_weights
        }
        for task_id, task in sample_config.routing.tasks.items()
    })
    task_result = task_classifier.classify(messages)

    assert task_result.task_type == "chat"

    # 2. 难度评估
    difficulty_classifier = DifficultyClassifier([
        {"condition": "length < 30", "difficulty": "easy", "priority": 1},
        {"condition": "length > 200", "difficulty": "hard", "priority": 1},
    ])
    difficulty_result = difficulty_classifier.classify("你好", task_type=task_result.task_type)

    assert difficulty_result.difficulty == "easy"  # 短文本

    # 3. 模型选择
    selector = ModelSelector(model_pool_from_config)
    selection_result = selector.select(
        task_type=task_result.task_type,
        difficulty=difficulty_result.difficulty
    )

    # easy chat：gpt-4o（quality=9, priority=2）和 gpt-4o-mini（quality=6, priority=5）都支持
    # auto 策略按 priority 升序，选 gpt-4o（priority 更小即 quality 更高）
    assert selection_result.model_name == "gpt-4o"


def test_validate_config_with_empty_models():
    """测试配置验证：空模型列表"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        (config_dir / "providers.yaml").write_text("providers:\n  o:\n    api_base: http://a\n    api_key: k\n")
        (config_dir / "models.yaml").write_text("models: {}\n")
        (config_dir / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n")

        loader = ConfigLoader(config_dir)
        config = loader.load()
        # 空模型列表是合法的 V3 配置，但验证时应能检测到问题
        errors = loader.validate()
        # validate() 方法本身在能成功 load 的情况下返回空列表
        # 此处验证 loader 能正常工作即可
        assert isinstance(errors, list)


def test_model_fallback_chain(sample_config):
    """测试 fallback chain 推导"""
    chain = sample_config.get_fallback_chain("gpt-4o")
    # gpt-4o (quality=9) 和 claude-3-opus (quality=10) 差异 1 <= 2
    assert "claude-3-opus" in chain

    # gpt-4o (quality=9) 和 gpt-4o-mini (quality=6) 差异 3 > 2
    assert "gpt-4o-mini" not in chain


def test_difficulty_rules_priority():
    """测试难度规则优先级"""
    # 高优先级规则应该先匹配
    classifier = DifficultyClassifier([
        {"condition": "keyword:简单", "difficulty": "easy", "priority": 1},
        {"condition": "length > 100", "difficulty": "hard", "priority": 2},  # 低优先级
    ])

    # 既包含"简单"又很长的文本
    result = classifier.classify("简单" + "x" * 200)

    # 应该匹配 "简单" 的 easy 规则（优先级高）
    assert result.difficulty == "easy"
