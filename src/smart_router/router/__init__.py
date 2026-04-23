"""Smart Router 路由核心层

继承 LiteLLM Router，注入智能模型选择逻辑。
"""

from .plugin import SmartRouter

__all__ = ["SmartRouter"]
