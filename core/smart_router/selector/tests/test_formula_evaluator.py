"""Tests for FormulaEvaluator — 线性评分公式计算器"""

import pytest

from smart_router.selector.formula_evaluator import FormulaEvaluator
from smart_router.config.schema import FormulaConfig, ModelCapabilities


class TestFormulaEvaluatorSingleDimension:
    """测试单维度权重计算"""

    def test_single_dimension_weight(self):
        """单维度权重计算正确（quality=10, weight=0.5 → 5.0）"""
        evaluator = FormulaEvaluator(FormulaConfig(weights={"quality": 0.5}))
        caps = ModelCapabilities(quality=10, cost=5, context=128000)
        score = evaluator.evaluate(caps)
        assert score == pytest.approx(5.0)


class TestFormulaEvaluatorMultiDimension:
    """测试多维度权重计算"""

    def test_multi_dimension_weights(self):
        """多维度权重计算正确（quality=10*0.5 + cost=5*0.5 = 7.5）"""
        evaluator = FormulaEvaluator(
            FormulaConfig(weights={"quality": 0.5, "cost": 0.5})
        )
        caps = ModelCapabilities(quality=10, cost=5, context=128000)
        score = evaluator.evaluate(caps)
        assert score == pytest.approx(7.5)


class TestFormulaEvaluatorMissingDimensions:
    """测试缺失维度处理"""

    def test_missing_dimension_treated_as_zero(self):
        """缺失维度（reasoning=None）时视为 0"""
        evaluator = FormulaEvaluator(
            FormulaConfig(weights={"quality": 0.5, "reasoning": 0.5})
        )
        caps = ModelCapabilities(quality=10, cost=5, context=128000, reasoning=None)
        score = evaluator.evaluate(caps)
        assert score == pytest.approx(5.0)


class TestFormulaEvaluatorEvaluateAll:
    """测试批量计算"""

    def test_evaluate_all(self):
        """evaluate_all 批量计算正确"""
        evaluator = FormulaEvaluator(
            FormulaConfig(weights={"quality": 0.5, "cost": 0.5})
        )
        models = {
            "model-a": ModelCapabilities(quality=10, cost=5, context=128000),
            "model-b": ModelCapabilities(quality=6, cost=9, context=128000),
        }
        scores = evaluator.evaluate_all(models)
        assert scores["model-a"] == pytest.approx(7.5)
        assert scores["model-b"] == pytest.approx(7.5)


class TestFormulaEvaluatorZeroWeight:
    """测试权重为 0 的维度"""

    def test_zero_weight_dimension_ignored(self):
        """权重为 0 的维度不影响总分"""
        evaluator = FormulaEvaluator(
            FormulaConfig(weights={"quality": 1.0, "cost": 0.0})
        )
        caps = ModelCapabilities(quality=8, cost=5, context=128000)
        score = evaluator.evaluate(caps)
        assert score == pytest.approx(8.0)
