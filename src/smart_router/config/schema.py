"""Smart Router Configuration Schema - v2 Only"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    port: int = 4000
    host: str = "127.0.0.1"
    master_key: str = Field(default="sk-smart-router-local")


class LiteLLMModelConfig(BaseModel):
    model_name: str
    litellm_params: Dict


class TaskTypeConfig(BaseModel):
    """任务类型配置"""
    keywords: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class DifficultyRule(BaseModel):
    """难度评估规则"""
    condition: str = ""
    difficulty: str = "medium"
    description: Optional[str] = None
    applies_to: Optional[List[str]] = None
    priority: int = 1


class ModelCapability(BaseModel):
    """模型能力声明"""
    difficulties: List[str] = Field(default_factory=list)
    task_types: List[str] = Field(default_factory=list)
    priority: int = 1
    description: Optional[str] = None


class ModelPoolConfig(BaseModel):
    """模型池配置"""
    capabilities: Dict[str, ModelCapability] = Field(default_factory=dict)
    default_model: str = "gpt-4o"


class FallbackTimeoutConfig(BaseModel):
    default: int = 30
    hard_tasks: int = 60


class SmartRouterConfig(BaseModel):
    """Smart Router 配置 (v2 Only)"""
    
    # 任务类型定义
    task_types: Dict[str, TaskTypeConfig] = Field(default_factory=dict)
    
    # 难度评估规则
    difficulty_rules: List[DifficultyRule] = Field(default_factory=list)
    
    # 模型能力声明
    model_pool: ModelPoolConfig = Field(default_factory=ModelPoolConfig)
    
    # Fallback 链
    fallback_chain: Dict[str, List[str]] = Field(default_factory=dict)
    
    # 超时设置
    timeout: FallbackTimeoutConfig = Field(default_factory=FallbackTimeoutConfig)
    max_fallback_retries: int = 2
    
    def get_model_for_task(self, task_type: str, difficulty: str) -> Optional[str]:
        """根据任务类型和难度获取模型"""
        candidates = []
        
        for model_name, capability in self.model_pool.capabilities.items():
            # 检查是否支持该难度
            if difficulty not in capability.difficulties:
                continue
            
            # 检查是否支持该任务类型（如果没指定，则支持所有）
            if capability.task_types and task_type not in capability.task_types:
                continue
            
            # 获取优先级
            priority = capability.priority
            
            candidates.append((model_name, priority))
        
        if not candidates:
            return self.model_pool.default_model
        
        # 按优先级排序，返回优先级最高的
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]


class Config(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    model_list: List[LiteLLMModelConfig] = Field(default_factory=list)
    smart_router: SmartRouterConfig = Field(default_factory=SmartRouterConfig)
