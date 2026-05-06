from typing import Dict
from ..config.schema import FormulaConfig, ModelCapabilities


class FormulaEvaluator:
    VALID_DIMENSIONS = {"quality", "cost", "reasoning", "creative", "context"}
    
    def __init__(self, formula: FormulaConfig):
        self.formula = formula
    
    def evaluate(self, caps: ModelCapabilities) -> float:
        score = 0.0
        for dim, weight in self.formula.weights.items():
            value = getattr(caps, dim, None)
            if value is not None:
                score += value * weight
        return score
    
    def evaluate_all(self, models: Dict[str, ModelCapabilities]) -> Dict[str, float]:
        return {name: self.evaluate(caps) for name, caps in models.items()}
