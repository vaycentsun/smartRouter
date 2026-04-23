"""V3 Model Selector - Capability-based selection"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

from ..config.v3_schema import ConfigV3


@dataclass
class SelectionResult:
    model_name: str
    task_type: str
    difficulty: str
    strategy: str
    score: float
    reason: str


class V3ModelSelector:
    SUPPORTED_STRATEGIES = {
        "auto", "quality", "cost", 
        "reasoning", "creative", "vision", "long_context", "latest",
        "balanced"
    }
    
    def __init__(self, config: ConfigV3, available_models: Optional[List[str]] = None):
        self.config = config
        self.available_models = available_models
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str = "auto",
        required_context: int = 0
    ) -> SelectionResult:
        candidates = self._filter_candidates(task_type, difficulty, required_context)
        
        if not candidates:
            raise NoModelAvailableError(
                f"No model supports {task_type}/{difficulty}"
            )
        
        if strategy == "auto":
            return self._select_by_auto(candidates, task_type, difficulty)
        elif strategy == "quality":
            return self._select_by_capability(candidates, "quality", task_type, difficulty)
        elif strategy == "cost":
            return self._select_by_capability(candidates, "cost", task_type, difficulty)
        elif strategy == "reasoning":
            return self._select_by_capability(candidates, "reasoning", task_type, difficulty)
        elif strategy == "creative":
            return self._select_by_capability(candidates, "creative", task_type, difficulty)
        elif strategy == "vision":
            return self._select_by_vision(candidates, task_type, difficulty)
        elif strategy == "long_context":
            return self._select_by_long_context(candidates, task_type, difficulty)
        elif strategy == "latest":
            return self._select_by_capability(candidates, "latest", task_type, difficulty)
        elif strategy == "balanced":
            return self._select_by_balanced(candidates, task_type, difficulty)
        else:
            raise UnknownStrategyError(f"Unknown strategy: {strategy}")
    
    def _filter_candidates(
        self,
        task_type: str,
        difficulty: str,
        required_context: int = 0
    ) -> List[Tuple[str, dict]]:
        candidates = []
        
        for name, model in self.config.models.items():
            if self.available_models is not None and name not in self.available_models:
                continue
            
            if task_type not in model.supported_tasks:
                continue
            
            if difficulty not in model.difficulty_support:
                continue
            
            # 上下文窗口过滤
            if required_context > 0 and model.capabilities.context < required_context:
                continue
            
            candidates.append((name, model))
        
        return candidates
    
    def _select_by_auto(
        self,
        candidates: List[Tuple[str, dict]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        task_config = self.config.routing.tasks.get(task_type)
        
        if task_config is None:
            weights = {"quality": 0.5, "cost": 0.5}
        else:
            weights = task_config.capability_weights
        
        scored = []
        for name, model in candidates:
            caps = model.capabilities
            score = (
                caps.quality * weights.get("quality", 0.5) +
                caps.cost * weights.get("cost", 0.5)
            )
            scored.append((name, score, model))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_score, best_model = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="auto",
            score=best_score,
            reason=f"Highest weighted score: {best_score:.2f}"
        )
    
    def _select_by_capability(
        self,
        candidates: List[Tuple[str, dict]],
        capability: str,
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        scored = []
        for name, model in candidates:
            value = getattr(model.capabilities, capability, None)
            if value is not None:
                scored.append((name, value))
        
        if not scored:
            return self._select_by_auto(candidates, task_type, difficulty)
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_value = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy=capability,
            score=float(best_value),
            reason=f"Highest {capability}: {best_value}"
        )
    
    def _select_by_vision(
        self,
        candidates: List[Tuple[str, dict]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        vision_candidates = [(n, m) for n, m in candidates if m.capabilities.vision]
        
        if not vision_candidates:
            return self._select_by_auto(candidates, task_type, difficulty)
        
        scored = [(n, m.capabilities.quality) for n, m in vision_candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_quality = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="vision",
            score=float(best_quality),
            reason=f"Vision-capable model with highest quality: {best_quality}"
        )
    
    def _select_by_long_context(
        self,
        candidates: List[Tuple[str, dict]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        long_context_candidates = [(n, m) for n, m in candidates 
                                   if m.capabilities.long_context or m.capabilities.context >= 128000]
        
        if not long_context_candidates:
            return self._select_by_context_window(candidates, task_type, difficulty)
        
        scored = [(n, m.capabilities.context) for n, m in long_context_candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_context = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="long_context",
            score=float(best_context),
            reason=f"Long context model with {best_context} tokens"
        )
    
    def _select_by_context_window(
        self,
        candidates: List[Tuple[str, dict]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        scored = [(n, m.capabilities.context) for n, m in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_context = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="long_context",
            score=float(best_context),
            reason=f"Largest context window: {best_context} tokens"
        )
    
    def _select_by_balanced(
        self,
        candidates: List[Tuple[str, dict]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        scored = []
        for name, model in candidates:
            caps = model.capabilities
            score = (caps.quality * 0.5 + caps.cost * 0.5)
            scored.append((name, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_score = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="balanced",
            score=best_score,
            reason=f"Balanced quality/cost score: {best_score:.2f}"
        )
    
    def get_available_models(
        self,
        task_type: str,
        difficulty: str,
        required_context: int = 0
    ) -> List[str]:
        """获取所有符合条件的模型（用于 fallback）"""
        candidates = self._filter_candidates(task_type, difficulty, required_context)
        return [name for name, _ in candidates]
    
    def get_candidates(
        self,
        task_type: str,
        difficulty: str,
        required_context: int = 0
    ) -> List[str]:
        """获取所有符合条件的模型（兼容 v2 接口别名）"""
        return self.get_available_models(task_type, difficulty, required_context)


class NoModelAvailableError(Exception):
    """没有可用模型"""
    pass


class UnknownStrategyError(Exception):
    """未知策略"""
    pass
