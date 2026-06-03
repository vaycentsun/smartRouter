"""Model Mapping 配置模型

职责：定义请求模型到目标模型的映射规则。
用于将用户请求的 model 名称替换为目标服务商的实际模型名，
并同时切换对应的 provider、base_url 和 api_key。
"""

import re
from typing import List

from pydantic import BaseModel, Field, model_validator


class ModelMappingRule(BaseModel):
    """单条模型映射规则

    将匹配到的请求模型名映射到目标模型，支持独立开关控制。
    """

    id: str = Field(description="规则唯一标识")
    enabled: bool = Field(default=True, description="规则独立开关")
    from_model: str = Field(description="匹配的请求模型名（精确匹配）")
    to_provider: str = Field(description="目标 provider 标识（仅用于展示和日志）")
    to_model: str = Field(description="目标模型名，将替换请求体中的 model 字段")
    to_litellm_provider: str = Field(
        default="openai", description="LiteLLM provider 前缀"
    )
    to_base_url: str = Field(description="目标服务商 API Base URL")
    to_api_key: str = Field(description="目标 API Key，支持 os.environ/KEY_NAME 格式")

    @model_validator(mode="after")
    def validate_fields(self):
        # 校验 id 只能包含字母、数字、下划线和连字符
        if not re.match(r"^[a-zA-Z0-9_\-]+$", self.id):
            raise ValueError(
                f"Invalid id '{self.id}': only alphanumeric, underscore and hyphen are allowed"
            )
        # 校验 base_url 必须以 http:// 或 https:// 开头
        if not self.to_base_url.startswith(("http://", "https://")):
            raise ValueError("to_base_url must start with http:// or https://")
        return self


class ModelMappingConfig(BaseModel):
    """模型映射全局配置

    包含全局总开关和映射规则列表，负责校验规则 id 的唯一性。
    """

    enabled: bool = Field(default=False, description="映射功能全局总开关")
    mappings: List[ModelMappingRule] = Field(
        default_factory=list, description="映射规则列表"
    )

    @model_validator(mode="after")
    def validate_unique(self):
        # 校验所有规则的 id 必须唯一
        ids = [r.id for r in self.mappings]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate mapping rule ids found")
        return self
