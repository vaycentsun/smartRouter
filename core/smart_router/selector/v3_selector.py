"""V3 Model Selector - Formula-based selection

基于全局线性评分公式（FormulaEvaluator）动态计算最佳模型。
所有策略统一使用 formula 权重计算得分，strategy 参数已废弃。
"""

import warnings
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ..config.schema import Config
from ..exceptions import NoModelAvailableError
from .formula_evaluator import FormulaEvaluator


@dataclass
class SelectionResult:
    model_name: str
    task_type: str
    difficulty: str
    strategy: str
    score: float
    reason: str
    ranked_models: List[str] = field(default_factory=list)


class V3ModelSelector:
    
    def __init__(self, config: Config, available_models: Optional[List[str]] = None):
        self.config = config
        self.available_models = available_models
        self.evaluator = FormulaEvaluator(config.routing.formula)
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str = "auto",
        required_context: int = 0,
        requires_vision: bool = False
    ) -> SelectionResult:
        """选择最佳模型
        
        Args:
            task_type: 任务类型
            difficulty: 难度（easy/medium/hard/expert）
            strategy: 策略（已废弃，保留仅用于兼容）
            required_context: 所需的上下文窗口大小（token 数），为 0 时不做上下文过滤
            requires_vision: 是否需要视觉能力
            
        Returns:
            SelectionResult
        """
        candidates = self._filter_candidates(task_type, difficulty, required_context, requires_vision)
        
        if not candidates:
            raise NoModelAvailableError(
                f"No model supports {task_type}/{difficulty}"
            )
        
        # Deprecated warning for non-auto strategies
        if strategy != "auto":
            warnings.warn(
                f"strategy='{strategy}' is deprecated. Use routing.formula weights instead.",
                DeprecationWarning,
                stacklevel=2
            )
        
        # 统一使用公式评分
        scored = []
        for name, model in candidates:
            score = self.evaluator.evaluate(model.capabilities)
            scored.append((name, score, model))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        best_name, best_score, best_model = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="auto",
            score=best_score,
            reason=f"Formula score: {best_score:.2f}"
        )
    
    def select_ranked(
        self,
        task_type: str,
        difficulty: str,
        required_context: int = 0,
        requires_vision: bool = False
    ) -> List[Tuple[str, float]]:
        """返回按公式得分降序排列的候选模型列表
        
        用于自建重试逻辑，按策略排序依次尝试 fallback。
        
        Args:
            task_type: 任务类型
            difficulty: 难度等级
            required_context: 所需的上下文窗口大小（token 数）
            requires_vision: 是否需要视觉能力
            
        Returns:
            [(model_name, score), ...] 按得分降序排列
        """
        candidates = self._filter_candidates(task_type, difficulty, required_context, requires_vision)
        
        scored = []
        for name, model in candidates:
            score = self.evaluator.evaluate(model.capabilities)
            scored.append((name, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _filter_candidates(
        self,
        task_type: str,
        difficulty: str,
        required_context: int = 0,
        requires_vision: bool = False
    ) -> List[Tuple[str, object]]:
        """过滤符合条件的模型
        
        Args:
            task_type: 任务类型
            difficulty: 难度等级
            required_context: 所需的上下文窗口大小（token 数），为 0 时不做上下文过滤
            requires_vision: 是否需要视觉能力
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
            
            # 检查视觉能力
            if requires_vision and not getattr(model.capabilities, 'vision', False):
                continue

            # 检查模型是否被禁用
            if not getattr(model, 'enabled', True):
                continue

            candidates.append((name, model))
        
        return candidates
    
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
