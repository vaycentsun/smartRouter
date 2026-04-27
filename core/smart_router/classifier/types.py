"""Classifier Types"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    """分类结果"""
    task_type: str
    estimated_difficulty: str
    confidence: float
    source: str


def get_default_classification() -> ClassificationResult:
    """获取默认分类结果"""
    return ClassificationResult(
        task_type="chat",
        estimated_difficulty="medium",
        confidence=0.0,
        source="default"
    )
