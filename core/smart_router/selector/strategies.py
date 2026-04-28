"""Selector Strategies - Compatibility module

统一导出 V3 模型选择器，v2 ModelSelector 已废弃。
"""

from .v3_selector import V3ModelSelector, SelectionResult, NoModelAvailableError, UnknownStrategyError

# 向后兼容别名（废弃）
ModelSelector = V3ModelSelector
ModelSelectionResult = SelectionResult

__all__ = [
    "V3ModelSelector",
    "SelectionResult",
    "NoModelAvailableError",
    "UnknownStrategyError",
    # 兼容别名
    "ModelSelector",
    "ModelSelectionResult",
]
