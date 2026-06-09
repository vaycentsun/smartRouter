"""ConfigLoader 测试"""


import pytest

from smart_router.config.loader import ConfigError, ConfigLoader


class TestConfigLoaderModelsDir:
    """测试 models/ 目录加载"""

    def test_load_models_from_directory(self, tmp_path):
        """从 models/ 目录加载多个 YAML 文件"""
        # 创建 providers.yaml
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
""")
        # 创建 routing.yaml
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        # 创建 models/ 目录和文件
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 10
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        assert "gpt-4o" in config.models
        assert "auto" in config.models
        assert config.models["gpt-4o"].provider == "openai"
        assert config.models["auto"].provider == "_virtual"

    def test_models_key_conflict(self, tmp_path):
        """同名模型出现在多个文件中时报错"""
        # 创建基础文件
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4:
    provider: openai
    litellm_model: openai/gpt-4
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        (models_dir / "anthropic.yaml").write_text("""
models:
  gpt-4:
    provider: anthropic
    litellm_model: anthropic/claude-3
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "gpt-4" in str(exc_info.value)
        assert "冲突" in str(exc_info.value)

    def test_deprecated_models_yaml(self, tmp_path):
        """models/ 不存在但 models.yaml 存在时提示废弃"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")
        (tmp_path / "models.yaml").write_text("models: {}\n")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "已废弃" in str(exc_info.value)
        assert "models/ 目录" in str(exc_info.value)

    def test_missing_models_directory(self, tmp_path):
        """models/ 和 models.yaml 都不存在时提示缺失"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "models" in str(exc_info.value)

    def test_validate_with_models_dir(self, tmp_path):
        """validate() 正确检查 models/ 目录存在"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openai.yaml").write_text("models: {}\n")

        loader = ConfigLoader(tmp_path)
        errors = loader.validate()
        assert errors == []

    def test_validate_missing_models_dir(self, tmp_path):
        """validate() 检测到 models/ 缺失"""
        (tmp_path / "providers.yaml").write_text("providers:\n  openai:\n    api_base: https://api.openai.com\n    api_key: sk-test\n    timeout: 30\n")
        (tmp_path / "routing.yaml").write_text("tasks: {}\ndifficulties: {}\nstrategies: {}\nfallback:\n  mode: auto\n  similarity_threshold: 2\n  provider_isolation: false\n  max_attempts: 3\n\n")

        loader = ConfigLoader(tmp_path)
        errors = loader.validate()
        assert any("models/" in e for e in errors)

    def test_auto_inject_virtual_provider(self, tmp_path):
        """providers.yaml 缺失 _virtual 时自动注入，兼容旧配置"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 10
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        assert "_virtual" in config.providers
        assert config.providers["_virtual"].api_base == ""
        assert config.providers["_virtual"].api_key == ""
        assert config.models["auto"].provider == "_virtual"

    def test_virtual_model_with_zero_capabilities_fails(self, tmp_path):
        """虚拟模型 quality/cost 为 0 时应导致验证失败"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/virtual-model
    capabilities:
      quality: 0
      cost: 0
      context: 2560000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        with pytest.raises(ConfigError) as exc_info:
            loader.load()
        assert "validation" in str(exc_info.value).lower()

    def test_preserve_existing_virtual_provider(self, tmp_path):
        """providers.yaml 已包含 _virtual 时不覆盖用户配置"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  _virtual:
    api_base: "http://custom"
    api_key: "custom-key"
    timeout: 60
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "_virtual.yaml").write_text("""
models:
  auto:
    provider: _virtual
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 10
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        assert config.providers["_virtual"].api_base == "http://custom"
        assert config.providers["_virtual"].api_key == "custom-key"
        assert config.providers["_virtual"].timeout == 60


class TestConfigLoaderSaveModel:
    """测试 save_model() 方法"""

    def _create_config_dir(self, tmp_path):
        """创建最小可用的配置目录结构"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
        return tmp_path

    def test_save_model_enabled_false(self, tmp_path):
        """保存 enabled=False 到 YAML 文件"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        loader.save_model("openai", "gpt-4o", False)

        config = loader.load()
        assert config.models["gpt-4o"].enabled is False

        # 验证 YAML 文件内容
        yaml_content = (tmp_path / "models" / "openai.yaml").read_text()
        assert "enabled: false" in yaml_content

    def test_save_model_enabled_true(self, tmp_path):
        """保存 enabled=True 到 YAML 文件"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        loader.save_model("openai", "gpt-4o", True)

        config = loader.load()
        assert config.models["gpt-4o"].enabled is True

    def test_save_model_not_found_raises(self, tmp_path):
        """模型不存在时抛出 ConfigError"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        with pytest.raises(ConfigError, match="Model 'unknown' not found"):
            loader.save_model("openai", "unknown", False)

    def test_save_model_file_not_found_raises(self, tmp_path):
        """YAML 文件不存在时抛出 ConfigError"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        with pytest.raises(ConfigError, match="Configuration file not found"):
            loader.save_model("nonexistent", "gpt-4o", False)

    def test_save_model_validation_failure_restores_backup(self, tmp_path):
        """保存后验证失败应恢复备份"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        # 先正常保存一次，创建备份
        loader.save_model("openai", "gpt-4o", False)

        # 验证第一次保存后的文件内容
        yaml_content_before = (tmp_path / "models" / "openai.yaml").read_text()
        assert "enabled: false" in yaml_content_before

        # 故意破坏 providers.yaml 使验证失败
        original_providers = (tmp_path / "providers.yaml").read_text()
        (tmp_path / "providers.yaml").write_text("providers: {}")

        with pytest.raises(ConfigError, match="Config validation failed after save"):
            loader.save_model("openai", "gpt-4o", True)

        # 验证 models/openai.yaml 被恢复为之前的 enabled=false
        yaml_content_after = (tmp_path / "models" / "openai.yaml").read_text()
        assert "enabled: false" in yaml_content_after
        assert "enabled: true" not in yaml_content_after

        # 恢复 providers.yaml 以便能正常加载验证
        (tmp_path / "providers.yaml").write_text(original_providers)
        config = loader.load()
        assert config.models["gpt-4o"].enabled is False


class TestConfigLoaderSaveProviderEnabled:
    """测试 save_provider_enabled() 方法"""

    def _create_config_dir(self, tmp_path):
        """创建最小可用的配置目录结构"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
    enabled: true
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
        return tmp_path

    def test_save_provider_enabled_false(self, tmp_path):
        """保存 enabled=False 到 providers.yaml"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        loader.save_provider_enabled("openai", False)

        config = loader.load()
        assert config.providers["openai"].enabled is False

        # 验证 YAML 文件内容
        yaml_content = (tmp_path / "providers.yaml").read_text()
        assert "enabled: false" in yaml_content

    def test_save_provider_enabled_true(self, tmp_path):
        """保存 enabled=True 到 providers.yaml"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        # 先设为 false
        loader.save_provider_enabled("openai", False)
        # 再设回 true
        loader.save_provider_enabled("openai", True)

        config = loader.load()
        assert config.providers["openai"].enabled is True

        # 验证 YAML 文件内容
        yaml_content = (tmp_path / "providers.yaml").read_text()
        assert "enabled: true" in yaml_content

    def test_save_provider_not_found_raises(self, tmp_path):
        """Provider 不存在时抛出 ConfigError"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        with pytest.raises(ConfigError, match="Provider 'unknown' not found"):
            loader.save_provider_enabled("unknown", False)

    def test_save_provider_file_not_found_raises(self, tmp_path):
        """providers.yaml 不存在时抛出 ConfigError"""
        self._create_config_dir(tmp_path)
        (tmp_path / "providers.yaml").unlink()
        loader = ConfigLoader(tmp_path)

        with pytest.raises(ConfigError, match="Configuration file not found"):
            loader.save_provider_enabled("openai", False)

    def test_save_provider_validation_failure_restores_backup(self, tmp_path):
        """保存后验证失败应恢复备份"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        # 先正常保存一次，创建备份
        loader.save_provider_enabled("openai", False)

        # 验证第一次保存后的文件内容
        yaml_content_before = (tmp_path / "providers.yaml").read_text()
        assert "enabled: false" in yaml_content_before

        # 故意破坏 models/openai.yaml 使验证失败（引用不存在的 provider）
        original_models = (tmp_path / "models" / "openai.yaml").read_text()
        (tmp_path / "models" / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: unknown_provider
""")

        with pytest.raises(ConfigError, match="Config validation failed after save"):
            loader.save_provider_enabled("openai", True)

        # 验证 providers.yaml 被恢复为之前的 enabled=false
        yaml_content_after = (tmp_path / "providers.yaml").read_text()
        assert "enabled: false" in yaml_content_after
        assert "enabled: true" not in yaml_content_after

        # 恢复 models/openai.yaml 以便能正常加载验证
        (tmp_path / "models" / "openai.yaml").write_text(original_models)
        config = loader.load()
        assert config.providers["openai"].enabled is False


class TestConfigLoaderCreateProvider:
    """测试 create_provider() 方法"""

    def _create_config_dir(self, tmp_path):
        """创建最小可用的配置目录结构"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
        return tmp_path

    def test_create_provider_success(self, tmp_path):
        """正常创建 provider，验证 providers.yaml 内容和 loader.load() 可读取"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        loader.create_provider("anthropic", "https://api.anthropic.com", "sk-anthropic")

        # 验证通过 load() 能读取到新 provider
        config = loader.load()
        assert "anthropic" in config.providers
        assert config.providers["anthropic"].api_base == "https://api.anthropic.com"
        assert config.providers["anthropic"].api_key == "sk-anthropic"
        assert config.providers["anthropic"].timeout == 30

        # 验证 YAML 文件内容
        yaml_content = (tmp_path / "providers.yaml").read_text()
        assert "anthropic:" in yaml_content
        assert "api_base: https://api.anthropic.com" in yaml_content
        assert "api_key: sk-anthropic" in yaml_content

    def test_create_provider_duplicate_name_raises(self, tmp_path):
        """name 已存在时抛出 ConfigError，原配置不变"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        original_content = (tmp_path / "providers.yaml").read_text()

        with pytest.raises(ConfigError, match="Provider 'openai' already exists"):
            loader.create_provider("openai", "https://new.com", "sk-new")

        # 验证原配置未被修改
        assert (tmp_path / "providers.yaml").read_text() == original_content

    def test_create_provider_invalid_name_raises(self, tmp_path):
        """name 含空格等非法字符时抛出 ConfigError"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        original_content = (tmp_path / "providers.yaml").read_text()

        with pytest.raises(ConfigError, match="Invalid provider name"):
            loader.create_provider("invalid name", "https://api.com", "sk-test")

        # 验证原配置未被修改
        assert (tmp_path / "providers.yaml").read_text() == original_content

    def test_create_provider_validation_failure_restores_backup(self, tmp_path):
        """创建后若 validate 失败，验证备份回滚生效"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        # 先正常创建一次 provider，确保备份文件存在
        loader.create_provider("anthropic", "https://api.anthropic.com", "sk-anthropic")

        # 验证第一次创建后的文件内容
        yaml_content_before = (tmp_path / "providers.yaml").read_text()
        assert "anthropic:" in yaml_content_before

        # 故意破坏 routing.yaml 使验证失败（删除 fallback 等必填项）
        original_routing = (tmp_path / "routing.yaml").read_text()
        (tmp_path / "routing.yaml").write_text("tasks: {}\n")

        with pytest.raises(ConfigError, match="Config validation failed after save"):
            loader.create_provider("google", "https://api.google.com", "sk-google")

        # 验证 providers.yaml 被恢复为之前的状态（只包含 anthropic，不包含 google）
        yaml_content_after = (tmp_path / "providers.yaml").read_text()
        assert "anthropic:" in yaml_content_after
        assert "google:" not in yaml_content_after

        # 恢复 routing.yaml 以便能正常加载验证
        (tmp_path / "routing.yaml").write_text(original_routing)
        config = loader.load()
        assert "anthropic" in config.providers
        assert "google" not in config.providers


class TestConfigLoaderAddModel:
    """测试 add_model() 方法"""

    def _create_config_dir(self, tmp_path):
        """创建包含多个 provider 和已有 model 的配置目录"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
  anthropic:
    api_base: https://api.anthropic.com
    api_key: sk-anthropic
    timeout: 30
  _virtual:
    api_base: ""
    api_key: ""
    timeout: 30
""")
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.5
      cost: 0.5
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
fallback:
  mode: auto
  similarity_threshold: 2
  provider_isolation: false
  max_attempts: 3
""")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "openai.yaml").write_text("""
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9
      cost: 3
      context: 128000
    supported_tasks: [chat]
    difficulty_support: [easy]
""")
        return tmp_path

    def test_add_model_to_existing_file(self, tmp_path):
        """正常添加 model 到已有文件，验证文件内容正确且 loader.load() 可读取"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        loader.add_model(
            "openai", "gpt-4-turbo", "openai/gpt-4-turbo",
            quality=9, cost=4, context=128000,
            supported_tasks=["chat"], enabled=True
        )

        # 验证 YAML 文件内容
        yaml_content = (tmp_path / "models" / "openai.yaml").read_text()
        assert "gpt-4-turbo:" in yaml_content
        assert "litellm_model: openai/gpt-4-turbo" in yaml_content
        assert "enabled: true" in yaml_content

        # 验证 load() 可读取
        config = loader.load()
        assert "gpt-4-turbo" in config.models
        assert config.models["gpt-4-turbo"].provider == "openai"
        assert config.models["gpt-4-turbo"].capabilities.quality == 9
        assert config.models["gpt-4-turbo"].enabled is True

    def test_add_model_creates_new_file(self, tmp_path):
        """添加 model 到不存在的文件时自动创建"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        loader.add_model(
            "anthropic", "claude-3", "anthropic/claude-3",
            quality=9, cost=5, context=200000,
            supported_tasks=["chat"], enabled=True
        )

        # 验证新文件被创建
        new_file = tmp_path / "models" / "anthropic.yaml"
        assert new_file.exists()
        yaml_content = new_file.read_text()
        assert "claude-3:" in yaml_content
        assert "provider: anthropic" in yaml_content

        # 验证 load() 可读取
        config = loader.load()
        assert "claude-3" in config.models
        assert config.models["claude-3"].provider == "anthropic"

    def test_add_model_duplicate_name_raises(self, tmp_path):
        """model name 全局已存在时抛出 ConfigError，且不改写文件"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        original_content = (tmp_path / "models" / "openai.yaml").read_text()

        # 尝试添加到同一 provider
        with pytest.raises(ConfigError, match="Model 'gpt-4o' already exists"):
            loader.add_model(
                "openai", "gpt-4o", "openai/gpt-4o-new",
                quality=9, cost=3, context=128000,
                supported_tasks=["chat"], enabled=True
            )

        # 尝试添加到另一 provider
        with pytest.raises(ConfigError, match="Model 'gpt-4o' already exists"):
            loader.add_model(
                "anthropic", "gpt-4o", "anthropic/claude-3",
                quality=9, cost=5, context=200000,
                supported_tasks=["chat"], enabled=True
            )

        # 验证原文件未被修改
        assert (tmp_path / "models" / "openai.yaml").read_text() == original_content
        # 验证 anthropic.yaml 未被创建
        assert not (tmp_path / "models" / "anthropic.yaml").exists()

    def test_add_model_provider_not_found_raises(self, tmp_path):
        """provider 不存在时抛出 ConfigError，且不创建文件"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        with pytest.raises(ConfigError, match="Provider 'nonexistent' not found"):
            loader.add_model(
                "nonexistent", "model-x", "openai/model-x",
                quality=5, cost=5, context=1000,
                supported_tasks=["chat"], enabled=True
            )

        assert not (tmp_path / "models" / "nonexistent.yaml").exists()

    def test_add_model_invalid_name_raises(self, tmp_path):
        """name 含非法字符时抛出 ConfigError，且不改写文件"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        original_content = (tmp_path / "models" / "openai.yaml").read_text()

        with pytest.raises(ConfigError, match="Invalid model name"):
            loader.add_model(
                "openai", "bad name!", "openai/bad",
                quality=5, cost=5, context=1000,
                supported_tasks=["chat"], enabled=True
            )

        assert (tmp_path / "models" / "openai.yaml").read_text() == original_content

    def test_add_model_validation_failure_restores_backup(self, tmp_path):
        """写入后若整体配置验证失败，验证备份回滚生效"""
        self._create_config_dir(tmp_path)
        loader = ConfigLoader(tmp_path)

        original_content = (tmp_path / "models" / "openai.yaml").read_text()

        # quality=0 违反 schema (ge=1)，写入后 validate() 会失败
        with pytest.raises(ConfigError, match="Config validation failed after save"):
            loader.add_model(
                "openai", "gpt-4-turbo", "openai/gpt-4-turbo",
                quality=0, cost=4, context=128000,
                supported_tasks=["chat"], enabled=True
            )

        # 验证原文件被恢复，未残留新模型
        restored_content = (tmp_path / "models" / "openai.yaml").read_text()
        assert restored_content == original_content
        assert "gpt-4-turbo" not in restored_content
