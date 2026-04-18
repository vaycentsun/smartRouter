from typing import List, Dict, Optional, Any

from litellm.router import Router

from .utils.markers import parse_markers, strip_markers, MarkerResult
from .classifier import TaskClassifier
from .classifier.types import ClassificationResult, get_default_classification
from .selector.strategies import ModelSelector
from .config.schema import Config


class SmartRouter(Router):
    """
    智能路由插件。
    
    继承 LiteLLM 的 Router，重写 get_available_deployment 方法，
    在请求到达 LiteLLM 原生路由前注入智能模型选择逻辑。
    """
    
    def __init__(self, config: Config, *args, **kwargs):
        self.sr_config = config
        # 存储最后选中的模型，用于响应头
        self.last_selected_model: Optional[str] = None
        
        self.classifier = TaskClassifier(
            rules=[r.model_dump() for r in config.smart_router.classification_rules],
            embedding_config=config.smart_router.embedding_match.model_dump()
        )
        self.selector = ModelSelector(
            routing_rules={
                k: v.model_dump() for k, v in config.smart_router.stage_routing.items()
            },
            fallback_chain=config.smart_router.fallback_chain
        )
        
        litellm_model_list = [m.model_dump() for m in config.model_list]
        
        super().__init__(
            model_list=litellm_model_list,
            *args,
            **kwargs
        )
    
    async def get_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict]] = None,
        request_kwargs: Optional[Dict] = None,
    ) -> Any:
        """
        重写路由决策：
        1. 解析阶段标记
        2. 无标记则分类任务
        3. 根据策略选择模型
        4. 调用父类完成实际路由
        """
        if model not in ("auto", "smart-router", "default"):
            if not model.startswith("stage:"):
                return await super().get_available_deployment(
                    model=model, messages=messages, request_kwargs=request_kwargs
                )
        
        if messages is None:
            messages = []
        
        markers = parse_markers(messages)
        
        classification = self._get_classification(markers, messages)
        
        available_models = [m.model_name for m in self.sr_config.model_list]
        selected = self.selector.select(
            task_type=classification.task_type,
            difficulty=classification.estimated_difficulty,
            strategy=self.sr_config.smart_router.default_strategy,
            model_list=available_models
        )
        
        # 存储选中的模型用于响应头
        self.last_selected_model = selected
        
        return await super().get_available_deployment(
            model=selected, messages=messages, request_kwargs=request_kwargs
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
        return self.selector.get_fallback_chain(model_name)
