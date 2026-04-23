"""strategies 模块测试 — 覆盖兼容别名导入"""

import pytest


class TestStrategiesCompatibility:
    """验证 strategies 兼容模块正确重导出 V3 选择器"""

    def test_import_v3_selector_classes(self):
        """应能正确导入 V3 核心类"""
        from smart_router.selector.strategies import (
            V3ModelSelector,
            SelectionResult,
            NoModelAvailableError,
            UnknownStrategyError,
        )
        
        assert V3ModelSelector is not None
        assert SelectionResult is not None
        assert NoModelAvailableError is not None
        assert UnknownStrategyError is not None

    def test_import_alias_classes(self):
        """应能正确导入兼容别名"""
        from smart_router.selector.strategies import (
            ModelSelector,
            ModelSelectionResult,
        )
        
        assert ModelSelector is not None
        assert ModelSelectionResult is not None

    def test_alias_is_same_as_original(self):
        """兼容别名应与原始类指向同一对象"""
        from smart_router.selector.strategies import (
            ModelSelector,
            V3ModelSelector,
            ModelSelectionResult,
            SelectionResult,
        )
        
        assert ModelSelector is V3ModelSelector
        assert ModelSelectionResult is SelectionResult

    def test_all_exports_present(self):
        """__all__ 列表应包含所有导出项"""
        from smart_router.selector import strategies
        
        expected = [
            "V3ModelSelector",
            "SelectionResult",
            "NoModelAvailableError",
            "UnknownStrategyError",
            "ModelSelector",
            "ModelSelectionResult",
        ]
        
        for name in expected:
            assert name in strategies.__all__, f"{name} 应在 __all__ 中"

    def test_module_docstring(self):
        """模块应包含说明性文档字符串"""
        from smart_router.selector import strategies
        
        assert strategies.__doc__ is not None
        assert "兼容" in strategies.__doc__ or "Compatibility" in strategies.__doc__
