"""集成测试 - v2 架构"""

import pytest
from pathlib import Path
import tempfile
import yaml

from smart_router.config.loader import load_config, validate_config
from smart_router.config.schema import Config
from smart_router.utils.markers import parse_markers
from smart_router.classifier.task_classifier import TaskTypeClassifier
from smart_router.classifier.difficulty_classifier import DifficultyClassifier
from smart_router.selector.model_selector import ModelSelector


@pytest.fixture
def test_config():
    """创建测试用的最小 v2 配置"""
    return Config(
        server={"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
        model_list=[
            {"model_name": "gpt-4o-mini", "litellm_params": {"model": "openai/gpt-4o-mini", "api_key": "test"}},
            {"model_name": "gpt-4o", "litellm_params": {"model": "openai/gpt-4o", "api_key": "test"}},
            {"model_name": "claude-3-opus", "litellm_params": {"model": "anthropic/claude-3-opus", "api_key": "test"}},
        ],
        smart_router={
            "task_types": {
                "chat": {"keywords": ["你好", "hello"]},
                "writing": {"keywords": ["写", "write"]},
                "code_review": {"keywords": ["review", "审查"]},
            },
            "difficulty_rules": [
                {"condition": "length < 30", "difficulty": "easy", "priority": 1},
                {"condition": "length > 200", "difficulty": "hard", "priority": 1},
            ],
            "model_pool": {
                "capabilities": {
                    "gpt-4o-mini": {"difficulties": ["easy"], "task_types": ["chat"], "priority": 1},
                    "gpt-4o": {"difficulties": ["medium"], "task_types": ["chat", "writing"], "priority": 1},
                    "claude-3-opus": {"difficulties": ["hard"], "task_types": ["writing", "code_review"], "priority": 1},
                },
                "default_model": "gpt-4o"
            },
            "fallback_chain": {"gpt-4o-mini": ["gpt-4o"]},
            "timeout": {"default": 30, "hard_tasks": 60},
            "max_fallback_retries": 2
        }
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
    """测试从 YAML 文件加载 v2 配置"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "server": {"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
            "model_list": [
                {"model_name": "test-model", "litellm_params": {"model": "openai/test", "api_key": "test"}}
            ],
            "smart_router": {
                "task_types": {"chat": {"keywords": ["你好"]}},
                "difficulty_rules": [],
                "model_pool": {
                    "capabilities": {},
                    "default_model": "test-model"
                },
                "fallback_chain": {},
                "timeout": {"default": 30, "hard_tasks": 60},
                "max_fallback_retries": 2
            }
        }, f)
        f.flush()
        
        config = load_config(Path(f.name))
        assert config.server.port == 4000
        assert len(config.model_list) == 1


def test_full_routing_flow_with_markers(test_config):
    """测试带标记的完整路由流程"""
    messages = [{"role": "user", "content": "[stage:writing] [difficulty:hard] 写论文"}]
    
    # 1. 解析标记
    markers = parse_markers(messages)
    assert markers.stage == "writing"
    assert markers.difficulty == "hard"
    
    # 2. 使用标记直接选择
    task_type = markers.stage
    difficulty = markers.difficulty
    
    # 3. 模型选择
    selector = ModelSelector(test_config.smart_router.model_pool.model_dump())
    result = selector.select(task_type=task_type, difficulty=difficulty)
    
    # hard writing 应该选 claude-3-opus
    assert result.model_name == "claude-3-opus"


def test_auto_classification_flow(test_config):
    """测试自动分类流程（无标记）"""
    # 短文本应该 easy chat
    messages = [{"role": "user", "content": "你好"}]
    
    # 1. 任务分类
    task_classifier = TaskTypeClassifier({
        k: v.model_dump() if hasattr(v, 'model_dump') else v
        for k, v in test_config.smart_router.task_types.items()
    })
    task_result = task_classifier.classify(messages)
    
    assert task_result.task_type == "chat"
    
    # 2. 难度评估
    difficulty_classifier = DifficultyClassifier([
        r.model_dump() if hasattr(r, 'model_dump') else r
        for r in test_config.smart_router.difficulty_rules
    ])
    difficulty_result = difficulty_classifier.classify("你好", task_type=task_result.task_type)
    
    assert difficulty_result.difficulty == "easy"  # 短文本
    
    # 3. 模型选择
    selector = ModelSelector(test_config.smart_router.model_pool.model_dump())
    selection_result = selector.select(
        task_type=task_result.task_type,
        difficulty=difficulty_result.difficulty
    )
    
    # easy chat 应该选 gpt-4o-mini
    assert selection_result.model_name == "gpt-4o-mini"


def test_validate_config_errors():
    """测试配置验证错误检测"""
    config = Config(
        server={"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
        model_list=[],  # 空模型列表
        smart_router={
            "task_types": {},
            "difficulty_rules": [],
            "model_pool": {
                "capabilities": {},
                "default_model": "non-existent-model"  # 不存在的默认模型
            },
            "fallback_chain": {},
            "timeout": {"default": 30, "hard_tasks": 60},
            "max_fallback_retries": 2
        }
    )
    
    errors = validate_config(config)
    
    assert len(errors) > 0
    assert any("model_list 为空" in err for err in errors)
    assert any("默认模型" in err for err in errors)


def test_model_fallback_chain_validation(test_config):
    """测试 fallback chain 验证"""
    # 修改配置，添加无效的 fallback
    test_config.smart_router.fallback_chain = {
        "gpt-4o-mini": ["non-existent-model"]  # 不存在的模型
    }
    
    errors = validate_config(test_config)
    
    assert len(errors) > 0
    assert any("non-existent-model" in err for err in errors)


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
