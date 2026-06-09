"""Provider 健康检查器

调用 OpenAI 兼容的 /v1/models 接口验证 Provider 连通性，
返回 Provider 真实可用的模型 ID 列表。

使用内存缓存，支持手动刷新。
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import httpx
import yaml

from ..config.schema import Config


@dataclass
class HealthCheckResult:
    """Provider 健康检查结果"""
    status: Literal[
        "healthy",
        "auth_error",
        "rate_limited",
        "network_error",
        "unconfigured",
        "unknown",
    ]
    models: list[str] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)
    error: Optional[str] = None


class ProviderHealthChecker:
    """Provider 健康检查器

    每个 Provider 的检查结果缓存在内存中，
    通过 check(..., force=True) 可以跳过缓存重新检查。
    """

    def __init__(self, config: Config):
        self.config = config
        self._cache: dict[str, HealthCheckResult] = {}

    async def check(self, provider_name: str, force: bool = False) -> HealthCheckResult:
        """检查单个 Provider

        Args:
            provider_name: Provider 名称
            force: 为 True 时跳过缓存，强制重新检查

        Returns:
            HealthCheckResult: 检查结果
        """
        if not force and provider_name in self._cache:
            return self._cache[provider_name]

        result = await self._do_check(provider_name)
        self._cache[provider_name] = result
        return result

    def get_cached(self, provider_name: str) -> Optional[HealthCheckResult]:
        """获取缓存的检查结果（不触发新检查）"""
        return self._cache.get(provider_name)

    def write_discovered_models(
        self, provider_name: str, discovered_models: list[str], config_dir: Path
    ) -> None:
        """将新发现的模型写入对应 Provider 的 YAML 文件

        自动跳过已在其他文件中定义的模型，避免跨文件冲突。

        Args:
            provider_name: Provider 名称
            discovered_models: Provider 返回的模型 ID 列表
            config_dir: 配置目录路径
        """
        if provider_name == "_virtual":
            return

        models_dir = config_dir / "models"
        models_dir.mkdir(exist_ok=True)
        filepath = models_dir / f"{provider_name}.yaml"

        # 扫描所有现有模型文件，收集已定义的模型名（防止跨文件冲突）
        all_existing_ids: set[str] = set()
        if models_dir.exists():
            for other_file in models_dir.glob("*.yaml"):
                with open(other_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                all_existing_ids.update(data.get("models", {}).keys())

        # 读取当前 Provider 文件的现有配置
        existing_models: dict = {}
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            existing_models = data.get("models", {})

        # 添加新发现的模型（保留已有配置，跳过跨文件冲突）
        added_any = False
        for model_id in discovered_models:
            if model_id in existing_models:
                continue
            if model_id in all_existing_ids:
                # 该模型名已在其他文件中定义，跳过以避免配置加载冲突
                continue
            existing_models[model_id] = {
                "provider": provider_name,
                "litellm_model": f"openai/{model_id}",
                "capabilities": {
                    "quality": 5,
                    "cost": 5,
                    "context": 32000,
                },
                "supported_tasks": ["chat"],
                "difficulty_support": ["easy", "medium"],
            }
            all_existing_ids.add(model_id)
            added_any = True

        if not added_any:
            return

        # 写回文件
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {"models": existing_models},
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )

    async def _do_check(self, provider_name: str) -> HealthCheckResult:
        """实际执行 HTTP 检查"""
        # 1. 检查 Provider 是否存在
        if provider_name not in self.config.providers:
            return HealthCheckResult(
                status="unknown",
                error=f"Provider '{provider_name}' 不存在",
            )

        provider = self.config.providers[provider_name]

        # 2. 检查 API Key 是否配置
        if not provider.api_key:
            return HealthCheckResult(
                status="unconfigured",
                error="API Key 未配置",
            )

        # 解析 api_key（支持 os.environ/KEY_NAME 格式）
        api_key = provider.api_key
        if api_key.startswith("os.environ/"):
            import os

            env_var = api_key.replace("os.environ/", "")
            api_key = os.environ.get(env_var, "")
            if not api_key:
                return HealthCheckResult(
                    status="unconfigured",
                    error=f"环境变量 {env_var} 未设置",
                )

        # 3. 调用 /v1/models
        api_base = provider.api_base.rstrip("/")
        # 兼容 api_base 已包含 /v1 的情况（如 https://api.openai.com/v1）
        if api_base.endswith("/v1"):
            url = f"{api_base}/models"
        else:
            url = f"{api_base}/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    model_ids = [m["id"] for m in data.get("data", []) if "id" in m]
                    return HealthCheckResult(
                        status="healthy",
                        models=model_ids,
                    )
                elif resp.status_code in (401, 403):
                    return HealthCheckResult(
                        status="auth_error",
                        error=f"HTTP {resp.status_code}: API Key 无效或权限不足",
                    )
                elif resp.status_code == 429:
                    return HealthCheckResult(
                        status="rate_limited",
                        error=f"HTTP {resp.status_code}: 请求频率超限",
                    )
                else:
                    return HealthCheckResult(
                        status="unknown",
                        error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    )
        except httpx.ConnectError as e:
            return HealthCheckResult(
                status="network_error",
                error=f"网络连接失败: {e}",
            )
        except httpx.TimeoutException as e:
            return HealthCheckResult(
                status="network_error",
                error=f"请求超时: {e}",
            )
        except Exception as e:
            return HealthCheckResult(
                status="unknown",
                error=f"未知错误: {e}",
            )
