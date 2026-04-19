"""V3 Configuration Schema - Three-layer decoupled architecture

三层解耦架构：
- Provider 层: 服务商连接信息（API Key、Base URL）
- Model 层: 模型能力声明（quality、speed、cost、支持的任务/难度）
- Routing 层: 任务定义与路由策略
"""

import os
from typing import Dict, Optional, List, Literal
from pydantic import BaseModel, Field, model_validator, PrivateAttr


class ProviderConfig(BaseModel):
    """服务商连接配置
    
    职责：管理 API Key、Base URL、超时等连接信息
    """
    api_base: str
    api_key: str                      # "os.environ/KEY_NAME" 或直接 key
    timeout: int = 30
    default_headers: Dict[str, str] = Field(default_factory=dict)
    rate_limit: Optional[int] = None  # 每分钟请求数限制


class ModelCapabilities(BaseModel):
    """模型能力评分 (1-10)"""
    quality: int = Field(ge=1, le=10, description="质量评分，10=最高质量")
    speed: int = Field(ge=1, le=10, description="响应速度，10=最快")
    cost: int = Field(ge=1, le=10, description="成本效率，10=最便宜")
    context: int = Field(gt=0, description="上下文窗口大小")


class ModelConfig(BaseModel):
    """模型配置
    
    职责：声明模型的能力属性和支持的任务/难度
    """
    provider: str                     # 引用 providers.yaml 中的名称
    litellm_model: str                # LiteLLM 格式，如 "openai/gpt-4o"
    capabilities: ModelCapabilities
    supported_tasks: List[str]
    difficulty_support: List[Literal["easy", "medium", "hard"]]


class TaskConfig(BaseModel):
    """任务类型配置"""
    name: str
    description: str
    capability_weights: Dict[str, float]  # quality/speed/cost 权重
    
    @model_validator(mode='after')
    def check_weights_sum(self):
        """验证权重总和约为 1.0"""
        total = sum(self.capability_weights.values())
        if not 0.99 <= total <= 1.01:  # 允许浮点误差
            raise ValueError(f"capability_weights must sum to 1.0, got {total}")
        return self


class DifficultyConfig(BaseModel):
    """难度等级配置"""
    description: str
    max_tokens: int


class StrategyConfig(BaseModel):
    """路由策略配置"""
    description: str
    # auto/quality/speed/cost 策略的具体逻辑由代码实现


class FallbackConfig(BaseModel):
    """Fallback 自动推导配置"""
    mode: Literal["auto"] = "auto"
    similarity_threshold: int = Field(default=2, ge=1, le=5, 
                                      description="quality 差异阈值")


class RoutingConfig(BaseModel):
    """路由层根配置"""
    tasks: Dict[str, TaskConfig]
    difficulties: Dict[str, DifficultyConfig]
    strategies: Dict[str, StrategyConfig]
    fallback: FallbackConfig


class ConfigV3(BaseModel):
    """V3 配置聚合根
    
    三层解耦架构：
    - providers: 服务商连接信息
    - models: 模型能力声明
    - routing: 任务定义与路由策略
    """
    providers: Dict[str, ProviderConfig]
    models: Dict[str, ModelConfig]
    routing: RoutingConfig
    
    # 运行时派生数据
    _fallback_chains: Dict[str, List[str]] = PrivateAttr(default_factory=dict)
    
    @model_validator(mode="after")
    def validate_references(self):
        """验证 models 引用的 provider 都存在"""
        for name, model in self.models.items():
            if model.provider not in self.providers:
                raise ValueError(
                    f"Model '{name}' references unknown provider '{model.provider}'"
                )
        return self
    
    def model_post_init(self, __context):
        """预计算 fallback 链"""
        self._fallback_chains = self._derive_fallback_chains()
    
    def _derive_fallback_chains(self) -> Dict[str, List[str]]:
        """基于 quality 相似度自动推导 fallback 链
        
        规则：
        1. 对于每个模型，找到 quality 差异 <= threshold 的其他模型
        2. 按 quality 降序排列
        3. 排除自身
        
        示例：
        - gpt-4o (quality=9) 和 claude-3-opus (quality=10) 差异为 1 <= 2
        - 它们应该互为 fallback
        """
        chains = {}
        threshold = self.routing.fallback.similarity_threshold
        
        for name, model in self.models.items():
            candidates = []
            model_quality = model.capabilities.quality
            
            for other_name, other in self.models.items():
                if other_name == name:
                    continue
                
                quality_diff = abs(other.capabilities.quality - model_quality)
                if quality_diff <= threshold:
                    candidates.append((other_name, other.capabilities.quality))
            
            # 按 quality 降序排列
            candidates.sort(key=lambda x: x[1], reverse=True)
            chains[name] = [n for n, _ in candidates]
        
        return chains
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """获取模型的 fallback 链"""
        return self._fallback_chains.get(model_name, [])
    
    def get_litellm_params(self, model_name: str) -> dict:
        """运行时组装 LiteLLM 参数"""
        model = self.models[model_name]
        provider = self.providers[model.provider]
        
        # 解析 api_key（支持 os.environ/KEY_NAME 格式）
        api_key = provider.api_key
        if api_key.startswith("os.environ/"):
            env_var = api_key.replace("os.environ/", "")
            api_key = os.environ.get(env_var, "")
        
        return {
            "model": model.litellm_model,
            "api_key": api_key,
            "api_base": provider.api_base,
            "timeout": provider.timeout,
        }
