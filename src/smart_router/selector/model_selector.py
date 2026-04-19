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
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str = "auto"
    ) -> ModelSelectionResult:
        """
        选择模型
        
        Args:
            task_type: 任务类型
            difficulty: 难度 (easy/medium/hard)
            strategy: 策略 (目前只有 auto)
            
        Returns:
            ModelSelectionResult
        """
        # 筛选符合条件的模型
        candidates = []
        
        for model_name, capability in self.capabilities.items():
            # 检查难度支持
            supported_difficulties = capability.get("difficulties", [])
            if difficulty not in supported_difficulties:
                continue
            
            # 检查任务类型支持（如果没指定，则支持所有）
            supported_tasks = capability.get("task_types", [])
            if supported_tasks and task_type not in supported_tasks:
                continue
            
            # 获取优先级
            priority = capability.get("priority", 99)
            
            candidates.append({
                "model_name": model_name,
                "priority": priority,
                "capability": capability
            })
        
        # 如果没有候选，使用默认模型
        if not candidates:
            return ModelSelectionResult(
                model_name=self.default_model,
                task_type=task_type,
                difficulty=difficulty,
                confidence=0.3,
                reason=f"无匹配模型，使用默认 (task={task_type}, difficulty={difficulty})"
            )
        
        # 按优先级排序（数字小的优先）
        candidates.sort(key=lambda x: x["priority"])
        
        # 选择优先级最高的
        selected = candidates[0]
        
        return ModelSelectionResult(
            model_name=selected["model_name"],
            task_type=task_type,
            difficulty=difficulty,
            confidence=0.9 if len(candidates) > 0 else 0.5,
            reason=f"优先级最高 (priority={selected['priority']})"
        )
    
    def get_candidates(
        self,
        task_type: str,
        difficulty: str
    ) -> List[str]:
        """获取所有符合条件的模型（用于 fallback）"""
        candidates = []
        
        for model_name, capability in self.capabilities.items():
            supported_difficulties = capability.get("difficulties", [])
            if difficulty not in supported_difficulties:
                continue
            
            supported_tasks = capability.get("task_types", [])
            if supported_tasks and task_type not in supported_tasks:
                continue
            
            candidates.append(model_name)
        
        return candidates
