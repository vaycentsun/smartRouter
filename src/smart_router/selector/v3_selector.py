"""V3 Model Selector - Capability-based selection

基于模型能力声明和任务权重动态计算最佳模型。

策略说明：
- auto: 使用任务配置的 capability_weights 计算加权得分
- quality: 选择 quality 最高的模型
- cost: 选择 cost 最高的模型（ cheapest ），但过滤 quality < threshold 的模型
- balanced: quality 和 cost 权重各 0.5
- reasoning/creative/vision/long_context/latest: 按对应维度选择
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..config.schema import Config
from ..exceptions import NoModelAvailableError, UnknownStrategyError


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
    
    
    def __init__(self, config: Config, available_models: Optional[List[str]] = None):
        self.config = config
        self.available_models = available_models
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str = "auto",
        required_context: int = 0
    ) -> SelectionResult:
        """选择最佳模型
        
        Args:
            task_type: 任务类型
            difficulty: 难度（easy/medium/hard/expert）
            strategy: 策略（auto/quality/cost/balanced/reasoning/creative/vision/long_context/latest）
            required_context: 所需的上下文窗口大小（token 数），为 0 时不做上下文过滤
            
        Returns:
            SelectionResult
        """
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
            return self._select_by_cost(candidates, task_type, difficulty)
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
    ) -> List[Tuple[str, object]]:
        """过滤符合条件的模型
        
        Args:
            task_type: 任务类型
            difficulty: 难度等级
            required_context: 所需的上下文窗口大小（token 数），为 0 时不做上下文过滤
        """
        candidates = []
        
        for name, model in self.config.models.items():
            if self.available_models is not None and name not in self.available_models:
                continue
            
            if task_type not in model.supported_tasks:
                continue
            
            if difficulty not in model.difficulty_support:
                continue
            
            # 检查上下文窗口支持
            if required_context > 0 and model.capabilities.context < required_context:
                continue
            
            candidates.append((name, model))
        
        return candidates
    
    def _select_by_auto(
        self,
        candidates: List[Tuple[str, object]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        """auto 策略：综合评分（基于任务权重）"""
        task_config = self.config.routing.tasks.get(task_type)
        
        if task_config is None:
            weights = {"quality": 0.5, "cost": 0.5}
        else:
            weights = task_config.capability_weights
        
        scored = []
        for name, model in candidates:
            caps = model.capabilities
            score = 0.0
            weight_sum = 0.0
            
            if "quality" in weights:
                score += caps.quality * weights["quality"]
                weight_sum += weights["quality"]
            if "cost" in weights:
                score += caps.cost * weights["cost"]
                weight_sum += weights["cost"]
            if "reasoning" in weights and caps.reasoning is not None:
                score += caps.reasoning * weights["reasoning"]
                weight_sum += weights["reasoning"]
            if "creative" in weights and caps.creative is not None:
                score += caps.creative * weights["creative"]
                weight_sum += weights["creative"]
            
            # 如果权重总和不等于 1，进行归一化
            if weight_sum > 0 and weight_sum != 1.0:
                score = score / weight_sum
            
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
        candidates: List[Tuple[str, object]],
        capability: str,
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        """单维度排序策略"""
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
    
    def _select_by_cost(
        self,
        candidates: List[Tuple[str, object]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        """cost 策略：选择最便宜的模型，但过滤掉低质量模型
        
        质量门槛从 routing.cost_quality_threshold 读取（默认 5）。
        如果过滤后没有候选，回退到不过滤（避免无模型可用）。
        """
        threshold = self.config.routing.cost_quality_threshold
        filtered = [
            (name, model)
            for name, model in candidates
            if model.capabilities.quality >= threshold
        ]
        
        # 如果过滤后没有候选，回退到原始列表
        if not filtered:
            filtered = candidates
        
        # 按 cost 降序排列（cost 越高 = 越便宜）
        scored = [(name, model.capabilities.cost) for name, model in filtered]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_value = scored[0]
        
        was_filtered = len(filtered) < len(candidates)
        filter_note = " (after quality filter)" if was_filtered else ""
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="cost",
            score=float(best_value),
            reason=f"Highest cost (cheapest){filter_note}: {best_value}"
        )
    
    def _select_by_vision(
        self,
        candidates: List[Tuple[str, object]],
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
        candidates: List[Tuple[str, object]],
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
        candidates: List[Tuple[str, object]],
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
        candidates: List[Tuple[str, object]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        """balanced 策略：quality 和 cost 各 0.5"""
        scored = []
        for name, model in candidates:
            caps = model.capabilities
            score = caps.quality * 0.5 + caps.cost * 0.5
            scored.append((name, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        best_name, best_score = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="balanced",
            score=best_score,
            reason=f"Highest balanced score (quality*0.5 + cost*0.5): {best_score:.2f}"
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
    
    def get_required_context(self, difficulty: str) -> int:
        """根据难度获取推荐的上下文窗口大小
        
        使用 routing.difficulties 配置中的 max_tokens。
        如果难度未定义，回退到默认值 4000。
        
        Args:
            difficulty: 难度等级
            
        Returns:
            推荐的上下文 token 数
        """
        diff_config = self.config.routing.difficulties.get(difficulty)
        if diff_config is not None:
            return diff_config.max_tokens
        return 4000  # 默认回退值



