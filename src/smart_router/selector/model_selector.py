"""v2 模型选择器 - 基于模型能力声明"""

from typing import Dict, List, Optional, Literal
from dataclasses import dataclass


@dataclass
class ModelSelectionResult:
    """模型选择结果"""
    model_name: str
    task_type: str
    difficulty: str
    confidence: float
    reason: str


class ModelSelector:
    """模型选择器（v2 架构）
    
    核心逻辑：
    1. 根据任务类型和难度，筛选出符合条件的模型
    2. 按优先级排序
    3. 返回优先级最高的模型
    """
    
    def __init__(self, model_pool: Dict):
        """
        Args:
            model_pool: {
                "capabilities": {
                    "model_name": {
                        "difficulties": ["easy", "medium"],
                        "task_types": ["writing", "chat"],
                        "priority": 1
                    }
                },
                "default_model": "gpt-4o"
            }
        """
        self.capabilities = model_pool.get("capabilities", {})
        self.default_model = model_pool.get("default_model", "gpt-4o")
    
    def _is_eligible(
        self,
        capability: Dict,
        task_type: str,
        difficulty: str,
        required_context: int = 0
    ) -> bool:
        """检查模型是否满足筛选条件
        
        Args:
            capability: 模型能力字典
            task_type: 任务类型
            difficulty: 难度
            required_context: 上下文需求
            
        Returns:
            是否满足条件
        """
        # 检查难度支持
        supported_difficulties = capability.get("difficulties", [])
        if difficulty not in supported_difficulties:
            return False
        
        # 检查任务类型支持（如果没指定，则支持所有）
        supported_tasks = capability.get("task_types", [])
        if supported_tasks and task_type not in supported_tasks:
            return False
        
        # 检查上下文窗口支持
        model_context = capability.get("context", 0)
        if required_context > 0 and model_context > 0 and model_context < required_context:
            return False
        
        return True
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str = "auto",
        required_context: int = 0
    ) -> ModelSelectionResult:
        """
        选择模型
        
        Args:
            task_type: 任务类型
            difficulty: 难度 (easy/medium/hard)
            strategy: 策略
                - auto: 默认，基于 priority（quality 越高 priority 越低）
                - quality: 质量优先，选择 quality 最高的模型
                - cost: 成本优先，选择 cost 最高的模型（cost 越高越便宜）
            required_context: 所需的上下文窗口大小（token 数），
                              为 0 时不做上下文过滤
            
        Returns:
            ModelSelectionResult
        """
        # 筛选符合条件的模型
        candidates = []
        context_filtered = []
        
        for model_name, capability in self.capabilities.items():
            if self._is_eligible(capability, task_type, difficulty, required_context):
                candidates.append({
                    "model_name": model_name,
                    "priority": capability.get("priority", 99),
                    "quality": capability.get("quality", 5),
                    "cost": capability.get("cost", 5),
                    "capability": capability
                })
            elif required_context > 0:
                # 仅因上下文不足被过滤的模型（用于回退判断）
                model_context = capability.get("context", 0)
                if model_context > 0 and model_context < required_context:
                    if self._is_eligible(capability, task_type, difficulty, 0):
                        context_filtered.append(model_name)
        
        # 如果没有候选（因上下文过滤导致），回退到默认模型
        if not candidates and context_filtered:
            return ModelSelectionResult(
                model_name=self.default_model,
                task_type=task_type,
                difficulty=difficulty,
                confidence=0.3,
                reason=f"上下文不足：需要 {required_context} tokens，无模型满足，使用默认"
            )
        
        # 如果没有候选（因任务/难度不匹配），使用默认模型
        if not candidates:
            return ModelSelectionResult(
                model_name=self.default_model,
                task_type=task_type,
                difficulty=difficulty,
                confidence=0.3,
                reason=f"无匹配模型，使用默认 (task={task_type}, difficulty={difficulty})"
            )
        
        # 根据策略排序
        if strategy == "quality":
            # 质量优先：quality 越高越好
            candidates.sort(key=lambda x: x["quality"], reverse=True)
            selected = candidates[0]
            reason = f"质量优先策略: quality={selected['quality']}"
        elif strategy == "cost":
            # 成本优先：cost 越高越便宜
            candidates.sort(key=lambda x: x["cost"], reverse=True)
            selected = candidates[0]
            reason = f"成本优先策略: cost={selected['cost']} (越高越便宜)"
        else:
            # auto: 按 priority 排序（数字小的优先）
            candidates.sort(key=lambda x: x["priority"])
            selected = candidates[0]
            reason = f"自动策略: priority={selected['priority']}"
        
        # 添加上下文信息到 reason
        if required_context > 0:
            reason += f", 上下文需求: {required_context}"
        
        return ModelSelectionResult(
            model_name=selected["model_name"],
            task_type=task_type,
            difficulty=difficulty,
            confidence=0.9 if len(candidates) > 0 else 0.5,
            reason=reason
        )
    
    def get_candidates(
        self,
        task_type: str,
        difficulty: str,
        required_context: int = 0
    ) -> List[str]:
        """获取所有符合条件的模型（用于 fallback）
        
        Args:
            task_type: 任务类型
            difficulty: 难度
            required_context: 所需的上下文窗口大小（token 数），为 0 时不过滤
        """
        return [
            model_name
            for model_name, capability in self.capabilities.items()
            if self._is_eligible(capability, task_type, difficulty, required_context)
        ]
