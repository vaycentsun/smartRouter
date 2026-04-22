"""V3 Model Selector - Capability-based selection"""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

from ..config.v3_schema import ConfigV3


@dataclass
class SelectionResult:
    """模型选择结果"""
    model_name: str
    task_type: str
    difficulty: str
    strategy: str
    score: float
    reason: str


class V3ModelSelector:
    """V3 模型选择器
    
    基于模型能力声明和任务权重动态计算最佳模型
    """
    
    def __init__(self, config: ConfigV3, available_models: Optional[List[str]] = None):
        self.config = config
        self.available_models = available_models  # 可用模型白名单
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str = "auto"
    ) -> SelectionResult:
        """选择最佳模型
        
        Args:
            task_type: 任务类型
            difficulty: 难度（easy/medium/hard）
            strategy: 策略（auto/quality/speed/cost）
            
        Returns:
            SelectionResult
        """
        # Step 1: 过滤候选模型
        candidates = self._filter_candidates(task_type, difficulty)
        
        if not candidates:
            raise NoModelAvailableError(
                f"No model supports {task_type}/{difficulty}"
            )
        
        # Step 2 & 3: 策略评分与排序
        if strategy == "auto":
            return self._select_by_auto(candidates, task_type, difficulty)
        elif strategy == "quality":
            return self._select_by_capability(candidates, "quality", task_type, difficulty)
        elif strategy == "speed":
            return self._select_by_capability(candidates, "speed", task_type, difficulty)
        elif strategy == "cost":
            return self._select_by_capability(candidates, "cost", task_type, difficulty)
        else:
            raise UnknownStrategyError(f"Unknown strategy: {strategy}")
    
    def _filter_candidates(
        self,
        task_type: str,
        difficulty: str
    ) -> List[Tuple[str, dict]]:
        """过滤符合条件的模型"""
        candidates = []
        
        for name, model in self.config.models.items():
            # 如果指定了可用模型列表，跳过不可用的
            if self.available_models is not None and name not in self.available_models:
                continue
            
            # 检查任务类型支持
            if task_type not in model.supported_tasks:
                continue
            
            # 检查难度支持
            if difficulty not in model.difficulty_support:
                continue
            
            candidates.append((name, model))
        
        return candidates
    
    def _select_by_auto(
        self,
        candidates: List[Tuple[str, dict]],
        task_type: str,
        difficulty: str
    ) -> SelectionResult:
        """auto 策略：综合评分"""
        task_config = self.config.routing.tasks.get(task_type)
        
        if task_config is None:
            # 如果任务未定义，使用默认权重
            weights = {"quality": 0.33, "speed": 0.33, "cost": 0.34}
        else:
            weights = task_config.capability_weights
        
        scored = []
        for name, model in candidates:
            caps = model.capabilities
            score = (
                caps.quality * weights.get("quality", 0.33) +
                caps.speed * weights.get("speed", 0.33) +
                caps.cost * weights.get("cost", 0.34)
            )
            scored.append((name, score, model))
        
        # 按得分降序排列
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
        """quality/speed/cost 策略：单维度排序"""
        scored = []
        for name, model in candidates:
            value = getattr(model.capabilities, capability)
            scored.append((name, value))
        
        # 降序排列
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
    
    def get_available_models(
        self,
        task_type: str,
        difficulty: str
    ) -> List[str]:
        """获取所有符合条件的模型（用于 fallback）"""
        candidates = self._filter_candidates(task_type, difficulty)
        return [name for name, _ in candidates]


class NoModelAvailableError(Exception):
    """没有可用模型"""
    pass


class UnknownStrategyError(Exception):
    """未知策略"""
    pass
