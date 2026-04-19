#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加 src 到路径（支持从任意目录运行）
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR.parent / 'src'))

from smart_router.utils.markers import parse_markers, strip_markers
from smart_router.classifier import TaskClassifier
from smart_router.classifier.types import get_default_classification
from smart_router.selector.strategies import ModelSelector
from smart_router.config.schema import Config

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

# ModelSelector V2 接口测试
selector = ModelSelector(model_pool={
    "capabilities": {
        "gpt-4o": {
            "difficulties": ["easy", "medium", "hard"],
            "task_types": ["code_review", "chat"],
            "priority": 1
        },
        "claude-3-sonnet": {
            "difficulties": ["easy", "medium", "hard"],
            "task_types": ["code_review", "chat"],
            "priority": 2
        }
    },
    "default_model": "gpt-4o"
})
result = selector.select('code_review', 'medium', 'auto')
assert result.model_name == 'gpt-4o'
print(f'✓ ModelSelector auto: {result.model_name}')

result_quality = selector.select('code_review', 'medium', 'quality')
# V2 ModelSelector 的策略实现可能不同，我们只验证能正常运行
print(f'✓ ModelSelector quality: {result_quality.model_name}')

config = Config()
assert config.server.port == 4000
print(f'✓ Config default: port={config.server.port}')

print('\n✅ 所有验证通过！')
