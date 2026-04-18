from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    task_type: str
    estimated_difficulty: str
    confidence: float
    source: str  # "stage_marker" | "rule_engine" | "embedding" | "default"


def get_default_classification() -> ClassificationResult:
    """当分类器完全失败时的降级结果"""
    return ClassificationResult(
        task_type="chat",
        estimated_difficulty="medium",
        confidence=0.0,
        source="default"
    )
