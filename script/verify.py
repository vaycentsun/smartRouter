#!/usr/bin/env python3
"""Smart Router 安装验证脚本 (V3)"""

import sys
from pathlib import Path

# 添加 src 到路径（支持从任意目录运行）
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent / 'src'))

from smart_router.utils.markers import parse_markers, strip_markers
from smart_router.classifier import TaskClassifier
from smart_router.classifier.types import get_default_classification
from smart_router.selector.v3_selector import V3ModelSelector, NoModelAvailableError, UnknownStrategyError
from smart_router.config.loader import ConfigLoader, load_config
from smart_router.config.schema import Config, ProviderConfig, ModelConfig, ModelCapabilities
from smart_router.config.schema import TaskConfig, DifficultyConfig, StrategyConfig, FallbackConfig, RoutingConfig

print('✓ 所有模块导入成功')

result = parse_markers([{'role': 'user', 'content': '[stage:code_review] 审查代码'}])
assert result.stage == 'code_review', f"Expected 'code_review', got '{result.stage}'"
print(f'✓ parse_markers: stage={result.stage}')

text = strip_markers('[stage:writing] 写邮件')
assert text == '写邮件', f"Expected '写邮件', got '{text}'"
print(f'✓ strip_markers: "{text}"')

classifier = TaskClassifier(rules=[], embedding_config={'enabled': False, 'custom_types': []})
result = classifier.classify([{'role': 'user', 'content': '测试'}])
assert result.task_type == 'chat'
print(f'✓ TaskClassifier default: {result.task_type}')

classifier2 = TaskClassifier(
    rules=[{"pattern": "(?i)(review|审查)", "task_type": "code_review", "difficulty": "medium"}],
    embedding_config={'enabled': False, 'custom_types': []}
)
result2 = classifier2.classify([{'role': 'user', 'content': '帮我审查代码'}])
assert result2.task_type == 'code_review'
assert result2.source == 'rule_engine'
print(f'✓ TaskClassifier rule match: {result2.task_type} ({result2.source})')

# V3ModelSelector 接口测试
v3_config = Config(
    providers={"openai": ProviderConfig(api_base="https://api.openai.com/v1", api_key="sk-test")},
    models={
        "gpt-4o": ModelConfig(
            provider="openai",
            litellm_model="openai/gpt-4o",
            capabilities=ModelCapabilities(quality=9, cost=3, context=128000),
            supported_tasks=["code_review", "chat"],
            difficulty_support=["easy", "medium", "hard"]
        ),
        "claude-3-sonnet": ModelConfig(
            provider="openai",
            litellm_model="anthropic/claude-3-sonnet",
            capabilities=ModelCapabilities(quality=8, cost=5, context=200000),
            supported_tasks=["code_review", "chat"],
            difficulty_support=["easy", "medium", "hard"]
        )
    },
    routing=RoutingConfig(
        tasks={
            "chat": TaskConfig(name="Chat", description="General chat", capability_weights={"quality": 0.5, "cost": 0.5}),
            "code_review": TaskConfig(name="Code Review", description="Review code", capability_weights={"quality": 0.7, "cost": 0.3})
        },
        difficulties={
            "easy": DifficultyConfig(description="Easy", max_tokens=2000),
            "medium": DifficultyConfig(description="Medium", max_tokens=8000)
        },
        strategies={
            "auto": StrategyConfig(description="Auto"),
            "quality": StrategyConfig(description="Quality")
        },
        fallback=FallbackConfig()
    )
)
selector = V3ModelSelector(v3_config)
result = selector.select('code_review', 'medium', 'auto')
assert result.model_name == 'gpt-4o'
print(f'✓ V3ModelSelector auto: {result.model_name}')

result_quality = selector.select('code_review', 'medium', 'quality')
print(f'✓ V3ModelSelector quality: {result_quality.model_name}')

# V3 Config 验证 - 检查配置加载器可以正常工作
config_dir = Path.home() / ".smart-router"
if (config_dir / "providers.yaml").exists():
    config = load_config(config_dir)
    print(f'✓ Config V3 loaded: {len(config.models)} models')
else:
    print(f'✓ Config V3 schema ready (no config files yet)')

print('\n✅ 所有验证通过！')
