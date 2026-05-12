"""Tests for FormulaConfig — 评分公式配置的 Pydantic 验证"""

import pytest
from pydantic import ValidationError

from smart_router.config.schema import FormulaConfig, RoutingConfig, TaskConfig, FallbackConfig


class TestFormulaConfigDefaults:
    """测试 FormulaConfig 默认值"""

    def test_default_weights_instantiation(self):
        """默认权重实例化成功（成本优先）"""
        formula = FormulaConfig()
        assert formula.weights == {"quality": 0.1, "cost": 0.9}


class TestFormulaConfigCustomWeights:
    """测试 FormulaConfig 自定义权重"""

    def test_custom_valid_weights_pass(self):
        """自定义有效权重通过验证"""
        formula = FormulaConfig(weights={"quality": 0.7, "cost": 0.3})
        assert formula.weights["quality"] == 0.7
        assert formula.weights["cost"] == 0.3


class TestFormulaConfigValidation:
    """测试 FormulaConfig 校验规则"""

    def test_unknown_dimensions_raises(self):
        """未知维度抛出 ValueError"""
        with pytest.raises(ValidationError) as exc_info:
            FormulaConfig(weights={"quality": 0.5, "speed": 0.5})
        assert "Unknown dimensions" in str(exc_info.value)

    def test_reasoning_dimension_rejected(self):
        """reasoning 维度已废弃，应抛出 ValueError"""
        with pytest.raises(ValidationError) as exc_info:
            FormulaConfig(weights={"quality": 0.5, "cost": 0.3, "reasoning": 0.2})
        assert "Unknown dimensions" in str(exc_info.value)

    def test_creative_dimension_rejected(self):
        """creative 维度已废弃，应抛出 ValueError"""
        with pytest.raises(ValidationError) as exc_info:
            FormulaConfig(weights={"quality": 0.5, "cost": 0.3, "creative": 0.2})
        assert "Unknown dimensions" in str(exc_info.value)

    def test_context_dimension_rejected(self):
        """context 维度已废弃，应抛出 ValueError"""
        with pytest.raises(ValidationError) as exc_info:
            FormulaConfig(weights={"quality": 0.5, "cost": 0.3, "context": 0.2})
        assert "Unknown dimensions" in str(exc_info.value)

    def test_all_zero_weights_raises(self):
        """全零权重抛出 ValueError"""
        with pytest.raises(ValidationError) as exc_info:
            FormulaConfig(weights={"quality": 0.0, "cost": 0.0})
        assert "At least one weight must be non-zero" in str(exc_info.value)

    def test_negative_weight_raises(self):
        """权重 < 0 抛出 ValueError"""
        with pytest.raises(ValidationError) as exc_info:
            FormulaConfig(weights={"quality": -0.1, "cost": 0.5})
        assert "must be between 0.0 and 1.0" in str(exc_info.value)

    def test_weight_greater_than_one_raises(self):
        """权重 > 1 抛出 ValueError"""
        with pytest.raises(ValidationError) as exc_info:
            FormulaConfig(weights={"quality": 1.1, "cost": 0.5})
        assert "must be between 0.0 and 1.0" in str(exc_info.value)


class TestRoutingConfigWithFormula:
    """测试 RoutingConfig 集成 formula 字段"""

    def test_routing_config_contains_formula_field(self):
        """RoutingConfig 包含 formula 字段可正常实例化"""
        routing = RoutingConfig(
            tasks={},
            difficulties={},
            strategies={},
            fallback=FallbackConfig()
        )
        assert routing.formula is not None
        assert isinstance(routing.formula, FormulaConfig)
        assert routing.formula.weights == {"quality": 0.1, "cost": 0.9}

    def test_routing_config_with_custom_formula(self):
        """RoutingConfig 可传入自定义 formula"""
        routing = RoutingConfig(
            tasks={},
            difficulties={},
            strategies={},
            formula=FormulaConfig(weights={"quality": 0.7, "cost": 0.3}),
            fallback=FallbackConfig()
        )
        assert routing.formula.weights == {"quality": 0.7, "cost": 0.3}
