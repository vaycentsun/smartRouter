from typing import List, Dict, Optional, Any

from litellm.router import Router

from ..utils.markers import parse_markers, strip_markers, MarkerResult
from ..utils.token_counter import estimate_messages_tokens
from ..classifier import TaskClassifier
from ..classifier.types import ClassificationResult, get_default_classification
from ..selector.v3_selector import V3ModelSelector
from ..config.schema import Config, ModelConfig


class SmartRouter(Router):
    """
    智能路由插件。
    
    继承 LiteLLM 的 Router，重写 get_available_deployment 方法，
    在请求到达 LiteLLM 原生路由前注入智能模型选择逻辑。
    
    使用 V3ModelSelector 进行模型选择，支持：
    - auto: 基于任务权重自动选择
    - quality: 质量优先
    - cost: 成本优先（带质量门槛）
    - balanced: 平衡模式
    """
    
    def __init__(self, config: Config, *args, **kwargs):
        self.sr_config = config
        # 存储最后选中的模型，用于响应头
        self.last_selected_model: Optional[str] = None
        
        # 从 V3 配置构建分类规则（向后兼容）
        classification_rules = [
            {
                "pattern": f"(?i)({task_config.name.lower().replace('_', '|')})",
                "task_type": task_id,
                "difficulty": "medium"
            }
            for task_id, task_config in config.routing.tasks.items()
        ]
        
        # 从 V3 配置构建 task_configs（包含 keywords 和 examples）
        task_configs = {
            task_id: {
                "keywords": list(getattr(task_config, "keywords", [])),
                "examples": list(getattr(task_config, "examples", [])),
                "description": task_config.description
            }
            for task_id, task_config in config.routing.tasks.items()
        }
        
        embedding_config = {
            "enabled": True,
            "threshold": 0.6,
            "default_task": "chat"
        }
        
        self.classifier = TaskClassifier(
            rules=classification_rules,
            embedding_config=embedding_config,
            task_configs=task_configs
        )
        
        # 获取可用模型列表（API Key 已配置的模型）
        available_models = config.get_available_models()
        
        # 使用 V3 选择器
        self.selector = V3ModelSelector(config=config, available_models=available_models)
        
        # 构建 LiteLLM 模型列表（只包含可用模型）
        litellm_model_list = []
        for model_name in available_models:
            litellm_params = config.get_litellm_params(model_name)
            litellm_model_list.append({
                "model_name": model_name,
                "litellm_params": litellm_params
            })
        
        # 构建 LiteLLM fallbacks（只包含可用模型的 fallback 链）
        fallbacks = []
        for model_name in available_models:
            chain = config.get_fallback_chain(model_name)
            if chain:
                fallbacks.append({model_name: chain})
        
        super().__init__(
            model_list=litellm_model_list,
            fallbacks=fallbacks if fallbacks else None,
            *args,
            **kwargs
        )
    
    def select_model(
        self,
        model_hint: str,
        messages: Optional[List[Dict]] = None,
        strategy: str = "auto"
    ) -> Any:
        """
        统一路由决策入口。
        
        解析 model_hint 中的 stage: 和 strategy- 前缀，
        结合 messages 中的 markers，完成分类和模型选择。
        
        Args:
            model_hint: 原始请求中的模型名（如 "auto", "stage:code_review", "strategy-quality"）
            messages: OpenAI 格式的消息列表
            strategy: 路由策略（auto/quality/cost）
        
        Returns:
            SelectionResult: 包含选中的模型名及决策原因
        """
        if messages is None:
            messages = []
        
        markers = parse_markers(messages)
        
        # 从 model_hint 解析 stage
        if model_hint.startswith("stage:"):
            task_type = model_hint.replace("stage:", "")
            difficulty = markers.difficulty or "medium"
            classification = ClassificationResult(
                task_type=task_type,
                estimated_difficulty=difficulty,
                confidence=1.0,
                source="stage_marker"
            )
        else:
            classification = self._get_classification(markers, messages)
        
        # 从 model_hint 解析 strategy
        if model_hint.startswith("strategy-"):
            strategy = model_hint.replace("strategy-", "")
        
        # 估算所需上下文窗口（输入 token + 按难度分级的输出预留）
        estimated_input = estimate_messages_tokens(messages)
        if estimated_input > 0:
            output_tokens = self.selector.get_required_context(classification.estimated_difficulty)
            required_context = estimated_input + output_tokens
        else:
            required_context = 0
        
        result = self.selector.select(
            task_type=classification.task_type,
            difficulty=classification.estimated_difficulty,
            strategy=strategy,
            required_context=required_context
        )
        
        # 存储选中的模型名用于响应头
        self.last_selected_model = result.model_name
        
        return result
    
    async def get_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict]] = None,
        request_kwargs: Optional[Dict] = None,
    ) -> Any:
        """
        重写路由决策：
        1. 判断是否需要智能路由
        2. 调用 select_model 完成统一决策
        3. 调用父类完成实际路由
        """
        if model not in ("auto", "smart-router", "default"):
            if not model.startswith("stage:"):
                return await super().get_available_deployment(
                    model=model, messages=messages, request_kwargs=request_kwargs
                )
        
        result = self.select_model(model, messages)
        
        return await super().get_available_deployment(
            model=result.model_name, messages=messages, request_kwargs=request_kwargs
        )
    
    def _get_classification(
        self,
        markers: MarkerResult,
        messages: List[Dict]
    ) -> ClassificationResult:
        """根据标记或分类器获取分类结果"""
        if markers.stage is None:
            return self.classifier.classify(messages)
        
        difficulty = markers.difficulty or "medium"
        return ClassificationResult(
            task_type=markers.stage,
            estimated_difficulty=difficulty,
            confidence=1.0,
            source="stage_marker"
        )
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """获取模型的 fallback 链"""
        return self.sr_config.get_fallback_chain(model_name)
