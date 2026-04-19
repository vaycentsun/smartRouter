import pytest
from pathlib import Path
import tempfile
import yaml

from smart_router.config.loader import load_config
from smart_router.config.schema import Config
from smart_router.utils.markers import parse_markers
from smart_router.classifier import TaskClassifier
from smart_router.selector.strategies import ModelSelector


@pytest.fixture
def test_config():
    """创建测试用的最小配置"""
    return Config(
        server={"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
        model_list=[
            {"model_name": "gpt-4o-mini", "litellm_params": {"model": "openai/gpt-4o-mini", "api_key": "os.environ/TEST_KEY"}},
            {"model_name": "gpt-4o", "litellm_params": {"model": "openai/gpt-4o", "api_key": "os.environ/TEST_KEY"}},
        ],
        smart_router={
            "default_strategy": "auto",
            "stage_routing": {
                "chat": {"easy": ["gpt-4o-mini"], "medium": ["gpt-4o"], "hard": ["gpt-4o"]},
                "code_review": {"easy": ["gpt-4o-mini"], "medium": ["gpt-4o"], "hard": ["gpt-4o"]},
            },
            "classification_rules": [
                {"pattern": "(?i)(review|审查)", "task_type": "code_review", "difficulty": "medium"}
            ],
            "embedding_match": {"enabled": True, "custom_types": []},
            "fallback_chain": {"gpt-4o-mini": ["gpt-4o"]},
            "timeout": {"default": 30, "hard_tasks": 60},
            "max_fallback_retries": 2
        }
    )


def test_stage_marker_routing(test_config):
    """测试阶段标记能正确路由"""
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
    """测试从 YAML 文件加载配置"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "server": {"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
            "model_list": [
                {"model_name": "test-model", "litellm_params": {"model": "openai/test"}}
            ],
            "smart_router": {
                "default_strategy": "auto",
                "stage_routing": {},
                "classification_rules": [],
                "embedding_match": {"enabled": False},
                "fallback_chain": {},
                "timeout": {"default": 30, "hard_tasks": 60},
                "max_fallback_retries": 2
            }
        }, f)
        f.flush()
        
        config = load_config(Path(f.name))
        assert config.server.port == 4000
        assert len(config.model_list) == 1


def test_full_routing_flow(test_config):
    """测试完整路由流程"""
    messages = [{"role": "user", "content": "[stage:code_review] [difficulty:hard] 审查代码"}]
    
    # 1. 解析标记
    markers = parse_markers(messages)
    assert markers.stage == "code_review"
    assert markers.difficulty == "hard"
    
    # 2. 如果有 stage 标记，直接使用（这是 plugin.py 中的逻辑）
    if markers.stage:
        from smart_router.classifier.types import ClassificationResult
        result = ClassificationResult(
            task_type=markers.stage,
            estimated_difficulty=markers.difficulty or "medium",
            confidence=1.0,
            source="stage_marker"
        )
    else:
        classifier = TaskClassifier(
            rules=[r.model_dump() for r in test_config.smart_router.classification_rules],
            embedding_config=test_config.smart_router.embedding_match.model_dump()
        )
        result = classifier.classify(messages)
    
    assert result.source == "stage_marker"
    assert result.task_type == "code_review"
    assert result.estimated_difficulty == "hard"
    
    selector = ModelSelector(
        routing_rules={k: v.model_dump() for k, v in test_config.smart_router.stage_routing.items()},
        fallback_chain=test_config.smart_router.fallback_chain
    )
    
    available = [m.model_name for m in test_config.model_list]
    selected = selector.select(
        task_type=result.task_type,
        difficulty=result.estimated_difficulty,
        strategy="auto",
        model_list=available
    )
    
    assert selected == "gpt-4o"


def test_auto_classification_flow():
    """测试自动分类流程（无标记）"""
    messages = [{"role": "user", "content": "帮我审查这段 Python 代码"}]
    
    classifier = TaskClassifier(
        rules=[{"pattern": "(?i)(review|审查)", "task_type": "code_review", "difficulty": "medium"}],
        embedding_config={"enabled": True, "custom_types": []}
    )
    
    result = classifier.classify(messages)
    assert result.source == "rule_engine"
    assert result.task_type == "code_review"


def test_validate_config_errors():
    """测试配置验证错误检测"""
    config = Config(
        server={"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
        model_list=[],
        smart_router={
            "default_strategy": "auto",
            "stage_routing": {},
            "classification_rules": [],
            "embedding_match": {"enabled": False},
            "fallback_chain": {},
            "timeout": {"default": 30, "hard_tasks": 60},
            "max_fallback_retries": 2
        }
    )
    
    from smart_router.config.loader import validate_config
    errors = validate_config(config)
    
    assert len(errors) > 0
    assert any("model_list 为空" in err for err in errors)
