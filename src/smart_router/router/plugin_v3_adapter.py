"""V3 Plugin Adapter

将 V3 配置适配到现有 SmartRouter 插件架构
"""

from typing import List, Dict, Optional, Any
from pathlib import Path

from litellm.router import Router

from ..config.v3_loader import ConfigV3Loader
from ..config.v3_schema import ConfigV3
from ..selector.v3_selector import V3ModelSelector
from ..utils.markers import parse_markers


class SmartRouterV3Adapter(Router):
    """Smart Router V3 适配器
    
    继承 LiteLLM Router，使用 V3 三层解耦配置架构进行智能模型选择
    """
    
    def __init__(self, config_dir: Path, *args, **kwargs):
        """初始化 V3 Adapter
        
        Args:
            config_dir: V3 配置目录（包含 providers.yaml, models.yaml, routing.yaml）
        """
        self.config_dir = Path(config_dir)
        self.config: ConfigV3 = ConfigV3Loader(self.config_dir).load()
        
        # 获取可用模型（API Key 已配置的模型）
        self.available_models = self.config.get_available_models()
        
        # 选择器只考虑可用模型
        self.selector = V3ModelSelector(self.config, available_models=self.available_models)
        
        # 存储最后选中的模型，用于响应头
        self.last_selected_model: Optional[str] = None
        
        # 转换 V3 可用模型列表为 LiteLLM 格式
        litellm_model_list = self._build_litellm_model_list()
        
        # 构建 LiteLLM fallbacks（只包含可用模型的 fallback 链）
        fallbacks = []
        for model_name in self.available_models:
            chain = self.config.get_fallback_chain(model_name)
            if chain:
                fallbacks.append({model_name: chain})
        
        super().__init__(
            model_list=litellm_model_list,
            fallbacks=fallbacks if fallbacks else None,
            *args,
            **kwargs
        )
    
    def _build_litellm_model_list(self) -> List[Dict]:
        """将 V3 可用模型列表转换为 LiteLLM 格式"""
        litellm_list = []
        
        for name in self.available_models:
            params = self.config.get_litellm_params(name)
            litellm_list.append({
                "model_name": name,
                "litellm_params": params
            })
        
        return litellm_list
    
    async def get_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict]] = None,
        request_kwargs: Optional[Dict] = None,
    ) -> Any:
        """重写路由决策
        
        1. 如果不是智能路由请求，直接调用父类
        2. 解析阶段标记
        3. 根据策略选择模型
        4. 调用父类完成实际路由
        """
        # 如果不是智能路由请求，直接调用父类
        if model not in ("auto", "smart-router", "default"):
            if not model.startswith("stage:"):
                return await super().get_available_deployment(
                    model=model,
                    messages=messages,
                    request_kwargs=request_kwargs
                )
        
        if messages is None:
            messages = []
        
        # 解析阶段标记
        markers = parse_markers(messages)
        
        # 确定任务类型和难度
        if markers.stage:
            task_type = markers.stage
            difficulty = markers.difficulty or "medium"
        else:
            # 默认使用 chat 任务
            task_type = "chat"
            difficulty = "medium"
        
        # 使用 V3 Selector 选择模型
        selection = self.selector.select(
            task_type=task_type,
            difficulty=difficulty,
            strategy="auto"
        )
        
        selected_model = selection.model_name
        
        # 存储选中的模型用于响应头
        self.last_selected_model = selected_model
        
        return await super().get_available_deployment(
            model=selected_model,
            messages=messages,
            request_kwargs=request_kwargs
        )
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """获取模型的 fallback 链"""
        return self.config.get_fallback_chain(model_name)
