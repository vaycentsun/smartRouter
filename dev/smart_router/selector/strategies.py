from typing import List, Dict, Optional


class ModelSelector:
    """模型选择器：根据策略从候选模型中选择目标"""
    
    def __init__(self, routing_rules: Dict[str, Dict], fallback_chain: Dict[str, List[str]]):
        """
        routing_rules: {stage_name: {difficulty: [model_names]}}
        fallback_chain: {model_name: [fallback_models]}
        """
        self.routing_rules = routing_rules
        self.fallback_chain = fallback_chain
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str,
        model_list: List[str]
    ) -> str:
        """
        根据策略选择模型。
        
        Args:
            task_type: 任务类型（如 code_review）
            difficulty: 难度（easy/medium/hard）
            strategy: auto/speed/cost/quality
            model_list: 可用的模型名称列表
        
        Returns:
            选中的 model_name
        """
        # 获取该任务类型+难度的候选模型列表
        candidates = self._get_candidates(task_type, difficulty)
        
        # 过滤掉不在 model_list 中的模型
        candidates = [c for c in candidates if c in model_list]
        
        if not candidates:
            # 无候选时，使用 model_list 中的第一个作为兜底
            return model_list[0] if model_list else "gpt-4o"
        
        if strategy == "auto":
            return candidates[0]  # 第一个为 auto 策略的推荐
        elif strategy == "speed":
            return self._select_by_speed(candidates)
        elif strategy == "cost":
            return self._select_by_cost(candidates)
        elif strategy == "quality":
            return self._select_by_quality(candidates)
        else:
            return candidates[0]
    
    def _get_candidates(self, task_type: str, difficulty: str) -> List[str]:
        """从路由规则中获取候选模型"""
        stage_rules = self.routing_rules.get(task_type, {})
        candidates = stage_rules.get(difficulty, [])
        
        # 如果该难度无配置，尝试降级到 medium，再降级到 easy
        if not candidates and difficulty == "hard":
            candidates = stage_rules.get("medium", [])
        if not candidates and difficulty in ("hard", "medium"):
            candidates = stage_rules.get("easy", [])
        
        return candidates
    
    def _select_by_speed(self, candidates: List[str]) -> str:
        """速度优先：选择列表中靠前的小模型"""
        return candidates[0] if candidates else ""
    
    def _select_by_cost(self, candidates: List[str]) -> str:
        """成本优先：选择列表中靠前的小模型"""
        return candidates[0] if candidates else ""
    
    def _select_by_quality(self, candidates: List[str]) -> str:
        """质量优先：选择列表中最后一个（最强模型）"""
        return candidates[-1] if candidates else ""
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """获取指定模型的 fallback 链"""
        return self.fallback_chain.get(model_name, [])


# 模型成本与速度的粗略排序（用于策略细化，可选扩展）
# 格式: model_name -> (speed_score, cost_score, quality_score)
# 分数越高越好
MODEL_PROFILES = {
    "gpt-4o-mini":    {"speed": 9, "cost": 9, "quality": 5},
    "gpt-4o":         {"speed": 7, "cost": 6, "quality": 8},
    "claude-3-sonnet":{"speed": 6, "cost": 5, "quality": 8},
    "qwen-turbo":     {"speed": 9, "cost": 9, "quality": 5},
    "qwen-max":       {"speed": 6, "cost": 6, "quality": 8},
    "kimi-k2":        {"speed": 7, "cost": 6, "quality": 8},
    "glm-5":          {"speed": 6, "cost": 6, "quality": 8},
    "minimax-m2":     {"speed": 8, "cost": 8, "quality": 6},
}
