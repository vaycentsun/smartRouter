import pytest
from unittest.mock import MagicMock, patch

from smart_router.utils.health_checker import HealthCheckResult, ProviderHealthChecker
from smart_router.config.schema import Config, ProviderConfig


@pytest.fixture
def sample_config():
    """返回包含两个 provider 的 Config"""
    return Config(
            providers={
                "openai": ProviderConfig(
                    api_base="https://api.openai.com/v1",
                    api_key="sk-test-key",
                    timeout=30,
                ),
                "aliyun": ProviderConfig(
                    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    api_key="os.environ/DASHSCOPE_API_KEY",
                    timeout=30,
                ),
            },
            models={},
            routing={
                "tasks": {},
                "difficulties": {},
                "strategies": {},
                "fallback": {
                    "mode": "auto",
                    "similarity_threshold": 2,
                    "provider_isolation": False,
                    "max_attempts": 3,
                },
                "cost_quality_threshold": 5,
            },
        )


class TestProviderHealthChecker:
    """ProviderHealthChecker 单元测试"""

    @pytest.fixture
    def checker(self, sample_config):
        return ProviderHealthChecker(sample_config)

    @pytest.mark.asyncio
    async def test_check_unknown_provider(self, checker):
        """不存在的 provider 返回 unknown"""
        result = await checker.check("nonexistent")
        assert result.status == "unknown"
        assert "不存在" in result.error

    @pytest.mark.asyncio
    async def test_check_unconfigured_empty_key(self, checker, sample_config):
        """api_key 为空返回 unconfigured"""
        sample_config.providers["openai"].api_key = ""
        result = await checker.check("openai")
        assert result.status == "unconfigured"
        assert "未配置" in result.error

    @pytest.mark.asyncio
    async def test_check_unconfigured_env_missing(self, checker):
        """环境变量未设置返回 unconfigured"""
        with patch.dict("os.environ", {}, clear=True):
            result = await checker.check("aliyun")
        assert result.status == "unconfigured"
        assert "DASHSCOPE_API_KEY" in result.error

    @pytest.mark.asyncio
    async def test_check_healthy(self, checker):
        """HTTP 200 返回 healthy 和模型列表"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4o", "object": "model"},
                {"id": "gpt-4o-mini", "object": "model"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
            result = await checker.check("openai")

        assert result.status == "healthy"
        assert result.models == ["gpt-4o", "gpt-4o-mini"]
        assert result.error is None
        # 验证 URL 正确：api_base 已包含 /v1，不应重复
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/models"

    @pytest.mark.asyncio
    async def test_check_healthy_url_without_v1_suffix(self, checker):
        """api_base 不包含 /v1 时正确追加 /v1/models"""
        # 修改 anthropic 的 api_key 使检查通过
        checker.config.providers["aliyun"].api_key = "sk-test"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "claude-3"}]}

        with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
            result = await checker.check("aliyun")

        assert result.status == "healthy"
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://dashscope.aliyuncs.com/compatible-mode/v1/models"

    @pytest.mark.asyncio
    async def test_check_auth_error_401(self, checker):
        """HTTP 401 返回 auth_error"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await checker.check("openai")

        assert result.status == "auth_error"
        assert "401" in result.error

    @pytest.mark.asyncio
    async def test_check_auth_error_403(self, checker):
        """HTTP 403 返回 auth_error"""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await checker.check("openai")

        assert result.status == "auth_error"
        assert "403" in result.error

    @pytest.mark.asyncio
    async def test_check_rate_limited(self, checker):
        """HTTP 429 返回 rate_limited"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            result = await checker.check("openai")

        assert result.status == "rate_limited"
        assert "429" in result.error

    @pytest.mark.asyncio
    async def test_check_network_error(self, checker):
        """连接失败返回 network_error"""
        import httpx

        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
            result = await checker.check("openai")

        assert result.status == "network_error"
        assert "网络连接失败" in result.error

    @pytest.mark.asyncio
    async def test_check_timeout(self, checker):
        """超时返回 network_error"""
        import httpx

        with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
            result = await checker.check("openai")

        assert result.status == "network_error"
        assert "超时" in result.error

    @pytest.mark.asyncio
    async def test_check_unknown_error(self, checker):
        """其他异常返回 unknown"""
        with patch("httpx.AsyncClient.get", side_effect=ValueError("Unexpected")):
            result = await checker.check("openai")

        assert result.status == "unknown"
        assert "未知错误" in result.error

    @pytest.mark.asyncio
    async def test_cache_hit(self, checker):
        """缓存命中时不重新请求"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "gpt-4o"}]}

        with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
            # 第一次调用
            result1 = await checker.check("openai")
            assert result1.status == "healthy"
            assert mock_get.call_count == 1

            # 第二次调用（应走缓存）
            result2 = await checker.check("openai")
            assert result2.status == "healthy"
            assert mock_get.call_count == 1  # 没有新增请求

    @pytest.mark.asyncio
    async def test_force_refresh(self, checker):
        """force=True 时跳过缓存"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "gpt-4o"}]}

        with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
            await checker.check("openai")
            assert mock_get.call_count == 1

            await checker.check("openai", force=True)
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_cached(self, checker):
        """get_cached 只读缓存，不触发请求"""
        # 缓存为空
        assert checker.get_cached("openai") is None

        # 写入缓存
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "gpt-4o"}]}

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            await checker.check("openai")

        # 读取缓存
        cached = checker.get_cached("openai")
        assert cached is not None
        assert cached.status == "healthy"


class TestWriteDiscoveredModels:
    """测试自动写入发现的新模型"""

    @pytest.fixture
    def checker(self, sample_config):
        return ProviderHealthChecker(sample_config)

    def test_write_new_models(self, checker, tmp_path):
        """新模型写入不存在的文件"""
        models_dir = tmp_path / "models"
        checker.write_discovered_models("openai", ["gpt-4o", "gpt-3.5"], tmp_path)

        filepath = models_dir / "openai.yaml"
        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "gpt-4o:" in content
        assert "gpt-3.5:" in content
        assert "openai/gpt-4o" in content
        assert "quality: 5" in content

    def test_preserve_existing_models(self, checker, tmp_path):
        """已有模型保留，新模型追加"""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        filepath = models_dir / "openai.yaml"
        filepath.write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [coding]
    difficulty_support: [easy]
""", encoding="utf-8")

        checker.write_discovered_models("openai", ["gpt-4o", "gpt-3.5"], tmp_path)

        content = filepath.read_text(encoding="utf-8")
        # 已有模型保留原配置
        assert "quality: 9" in content
        assert "coding" in content
        # 新模型使用默认值
        assert "gpt-3.5:" in content

    def test_skip_virtual_provider(self, checker, tmp_path):
        """虚拟 provider 不写入"""
        checker.write_discovered_models("_virtual", ["auto"], tmp_path)

        filepath = tmp_path / "models" / "_virtual.yaml"
        assert not filepath.exists()

    def test_no_new_models(self, checker, tmp_path):
        """全部已有模型，无新模型，文件不变"""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        filepath = models_dir / "openai.yaml"
        original_content = """
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [coding]
    difficulty_support: [easy]
"""
        filepath.write_text(original_content, encoding="utf-8")

        checker.write_discovered_models("openai", ["gpt-4o"], tmp_path)

        content = filepath.read_text(encoding="utf-8")
        assert "quality: 9" in content
        assert "gpt-3.5" not in content

    def test_skip_cross_file_conflict(self, checker, tmp_path):
        """已存在于其他文件中的模型不重复写入，避免配置加载冲突"""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # 在 openai.yaml 中定义 gpt-4o
        openai_file = models_dir / "openai.yaml"
        openai_file.write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [coding]
    difficulty_support: [easy]
""", encoding="utf-8")

        # 尝试向 aliyun.yaml 写入相同的模型名（跨文件冲突）
        checker.write_discovered_models("aliyun", ["gpt-4o", "qwen-max"], tmp_path)

        aliyun_file = models_dir / "aliyun.yaml"
        content = aliyun_file.read_text(encoding="utf-8")
        # gpt-4o 已存在于 openai.yaml，不应被写入 aliyun.yaml
        assert "gpt-4o:" not in content
        # qwen-max 是新模型，应被写入
        assert "qwen-max:" in content
