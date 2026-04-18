from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    port: int = 4000
    host: str = "127.0.0.1"
    master_key: str = Field(default="sk-smart-router-local")


class LiteLLMModelConfig(BaseModel):
    model_name: str
    litellm_params: Dict


class StageRoutingConfig(BaseModel):
    easy: List[str]
    medium: List[str]
    hard: List[str]


class ClassificationRule(BaseModel):
    pattern: str
    task_type: str
    difficulty: str


class CustomTypeEmbedding(BaseModel):
    name: str
    examples: List[str]


class EmbeddingMatchConfig(BaseModel):
    enabled: bool = True
    custom_types: List[CustomTypeEmbedding] = Field(default_factory=list)


class FallbackTimeoutConfig(BaseModel):
    default: int = 30
    hard_tasks: int = 60


class SmartRouterConfig(BaseModel):
    default_strategy: str = Field(default="auto", pattern="^(auto|speed|cost|quality)$")
    stage_routing: Dict[str, StageRoutingConfig] = Field(default_factory=dict)
    classification_rules: List[ClassificationRule] = Field(default_factory=list)
    embedding_match: EmbeddingMatchConfig = Field(default_factory=EmbeddingMatchConfig)
    fallback_chain: Dict[str, List[str]] = Field(default_factory=dict)
    timeout: FallbackTimeoutConfig = Field(default_factory=FallbackTimeoutConfig)
    max_fallback_retries: int = 2


class Config(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    model_list: List[LiteLLMModelConfig] = Field(default_factory=list)
    smart_router: SmartRouterConfig = Field(default_factory=SmartRouterConfig)
