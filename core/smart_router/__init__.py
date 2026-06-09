import os

# 禁用 LiteLLM 远程模型成本映射获取，避免网络超时导致 CLI 响应缓慢
# 用户可通过环境变量 LITELLM_LOCAL_MODEL_COST_MAP=false 恢复远程获取
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

try:
    from importlib.metadata import version
    __version__ = version("smartrouter")
except ImportError:
    __version__ = "1.1.0"
