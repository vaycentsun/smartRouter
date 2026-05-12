"""ConfigLoader 旧配置迁移测试"""

import pytest
from pathlib import Path

from smart_router.config.loader import ConfigLoader, ConfigError
from smart_router.config.schema import Config


class TestMigrateLegacyWeights:
    """测试 capability_weights 迁移为全局 formula"""

    def test_migrate_old_config_with_capability_weights(self, tmp_path):
        """有 capability_weights 的旧配置正确迁移为 formula"""
        # 创建 providers.yaml
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        # 创建 routing.yaml（旧配置：只有 capability_weights，没有 formula）
        (tmp_path / "routing.yaml").write_text("""
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
    capability_weights:
      quality: 0.6
      cost: 0.4
  code:
    name: "编程"
    description: "代码生成"
    capability_weights:
      quality: 0.7
      cost: 0.3
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
    supported_tasks: [chat, code]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        # 验证 formula 被正确迁移
        assert "formula" in config.routing.model_dump()
        assert config.routing.formula.weights == {"quality": 0.65, "cost": 0.35}

    def test_new_config_with_formula_not_overwritten(self, tmp_path):
        """已有 formula 的配置不被覆盖"""
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
      quality: 0.6
      cost: 0.4
  code:
    name: "编程"
    description: "代码生成"
difficulties:
  easy:
    description: "简单"
    max_tokens: 2000
strategies:
  auto:
    description: "自动"
formula:
  weights:
    quality: 0.8
    cost: 0.2
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
    supported_tasks: [chat, code]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        # 验证已有 formula 不被覆盖
        assert config.routing.formula.weights == {"quality": 0.8, "cost": 0.2}

    def test_no_capability_weights_no_error(self, tmp_path):
        """无 capability_weights 时不报错（使用 FormulaConfig 默认值）"""
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
  code:
    name: "编程"
    description: "代码生成"
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
    supported_tasks: [chat, code]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        # 验证使用默认值
        assert config.routing.formula.weights == {"quality": 0.5, "cost": 0.5}

    def test_multiple_tasks_average_weights(self, tmp_path):
        """多任务的 capability_weights 按维度正确取平均"""
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
      quality: 0.2
      cost: 0.8
  code:
    name: "编程"
    description: "代码生成"
    capability_weights:
      quality: 0.4
      cost: 0.6
  creative:
    name: "创意"
    description: "创意写作"
    capability_weights:
      quality: 0.6
      cost: 0.4
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
    supported_tasks: [chat, code, creative]
    difficulty_support: [easy]
""")

        loader = ConfigLoader(tmp_path)
        config = loader.load()

        # 验证按维度算术平均：(0.2+0.4+0.6)/3=0.4, (0.8+0.6+0.4)/3=0.6
        assert config.routing.formula.weights == {
            "quality": 0.4,
            "cost": 0.6,
        }

    def test_migrated_data_passes_pydantic_validation(self, tmp_path):
        """迁移后的数据可通过 Pydantic 验证"""
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

        loader = ConfigLoader(tmp_path)
        # 直接调用迁移方法验证
        routing_data = loader._load_yaml("routing.yaml")
        migrated = loader._migrate_legacy_weights(routing_data)

        # 验证迁移后的数据能通过 Pydantic 验证
        config = Config(
            providers={"openai": {"api_base": "https://api.openai.com", "api_key": "sk-test", "timeout": 30}},
            models={},
            routing=migrated,
        )
        assert config.routing.formula.weights == {"quality": 0.5, "cost": 0.5}


class TestSaveRouting:
    """测试 save_routing 方法"""

    def test_save_routing_writes_correct_content(self, tmp_path):
        """保存后文件内容正确"""
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

        loader = ConfigLoader(tmp_path)
        routing_raw = {
            "tasks": {
                "code": {
                    "name": "编程",
                    "description": "代码生成",
                }
            },
            "difficulties": {
                "easy": {
                    "description": "简单",
                    "max_tokens": 2000,
                }
            },
            "strategies": {
                "auto": {
                    "description": "自动",
                }
            },
            "fallback": {
                "mode": "auto",
                "similarity_threshold": 2,
                "provider_isolation": False,
                "max_attempts": 3,
            },
        }

        loader.save_routing(routing_raw)

        # 验证文件内容
        saved_content = (tmp_path / "routing.yaml").read_text(encoding="utf-8")
        assert "code:" in saved_content
        assert "编程" in saved_content

    def test_save_routing_creates_backup(self, tmp_path):
        """保存前创建备份文件"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        original_content = """
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
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
"""
        (tmp_path / "routing.yaml").write_text(original_content)
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

        loader = ConfigLoader(tmp_path)
        routing_raw = {
            "tasks": {
                "code": {
                    "name": "编程",
                    "description": "代码生成",
                }
            },
            "difficulties": {
                "easy": {
                    "description": "简单",
                    "max_tokens": 2000,
                }
            },
            "strategies": {
                "auto": {
                    "description": "自动",
                }
            },
            "fallback": {
                "mode": "auto",
                "similarity_threshold": 2,
                "provider_isolation": False,
                "max_attempts": 3,
            },
        }

        loader.save_routing(routing_raw)

        # 验证备份存在且内容正确
        backup_path = tmp_path / "routing.yaml.bak"
        assert backup_path.exists()
        assert backup_path.read_text(encoding="utf-8").strip() == original_content.strip()

    def test_save_routing_validation_failure_restores_backup(self, tmp_path):
        """验证失败时恢复备份"""
        (tmp_path / "providers.yaml").write_text("""
providers:
  openai:
    api_base: https://api.openai.com
    api_key: sk-test
    timeout: 30
""")
        original_content = """
tasks:
  chat:
    name: "聊天"
    description: "日常对话"
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
"""
        (tmp_path / "routing.yaml").write_text(original_content)
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

        loader = ConfigLoader(tmp_path)
        # 构造一个会导致验证失败的配置（缺少必填字段）
        bad_routing_raw = {
            "tasks": {},
            "difficulties": {},
            # 缺少 strategies 和 fallback
        }

        with pytest.raises(ConfigError) as exc_info:
            loader.save_routing(bad_routing_raw)

        assert "validation failed" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()

        # 验证原文件被恢复
        restored_content = (tmp_path / "routing.yaml").read_text(encoding="utf-8")
        assert restored_content.strip() == original_content.strip()

    def test_save_routing_with_formula_weights(self, tmp_path):
        """保存包含 formula 的 routing 配置"""
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

        loader = ConfigLoader(tmp_path)
        routing_raw = {
            "tasks": {
                "code": {
                    "name": "编程",
                    "description": "代码生成",
                }
            },
            "difficulties": {
                "easy": {
                    "description": "简单",
                    "max_tokens": 2000,
                }
            },
            "strategies": {
                "auto": {
                    "description": "自动",
                }
            },
            "formula": {
                "weights": {
                    "quality": 0.7,
                    "cost": 0.3,
                }
            },
            "fallback": {
                "mode": "auto",
                "similarity_threshold": 2,
                "provider_isolation": False,
                "max_attempts": 3,
            },
        }

        loader.save_routing(routing_raw)

        # 重新加载验证
        config = loader.load()
        assert config.routing.formula.weights == {"quality": 0.7, "cost": 0.3}
