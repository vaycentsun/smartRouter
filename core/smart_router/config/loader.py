"""V3 Configuration Loader"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional
import yaml
from pydantic import ValidationError

from .schema import Config


class ConfigLoader:
    """Smart Router 配置加载器"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
    
    def load(self) -> Config:
        """从三文件加载配置"""
        providers = self._load_yaml("providers.yaml")
        models = self._load_models()
        routing = self._load_yaml("routing.yaml")
        
        # 迁移旧配置：capability_weights -> formula.weights
        routing = self._migrate_legacy_weights(routing)
        
        providers_dict = providers.get("providers", {})
        
        # 自动注入 _virtual provider（如果缺失），确保虚拟模型（auto/smart-router 等）
        # 在旧版 providers.yaml（未包含 _virtual）下也能正常加载
        if "_virtual" not in providers_dict:
            providers_dict["_virtual"] = {
                "api_base": "",
                "api_key": "",
                "timeout": 30,
            }
        
        try:
            config = Config(
                providers=providers_dict,
                models=models,
                routing=routing
            )
            return config
        except ValidationError as e:
            raise ConfigError(f"Configuration validation failed: {e}") from e
    
    def _migrate_legacy_weights(self, data: dict) -> dict:
        """将旧 capability_weights 迁移为全局 formula
        
        算法：按维度分别算术平均
        avg_weights[dim] = sum(task_weights[dim]) / task_count
        """
        if "formula" in data:
            return data
        
        valid_dims = {"quality", "cost", "reasoning", "creative", "context"}
        weights_sum = defaultdict(float)
        task_count = 0
        
        for task_config in data.get("tasks", {}).values():
            cw = task_config.get("capability_weights")
            if cw:
                for dim, weight in cw.items():
                    if dim in valid_dims:
                        weights_sum[dim] += weight
                task_count += 1
        
        if task_count > 0:
            avg_weights = {
                dim: round(total / task_count, 4)
                for dim, total in weights_sum.items()
                if dim in valid_dims
            }
            if avg_weights:
                data["formula"] = {
                    "weights": avg_weights
                }
        
        return data
    
    def _load_models(self) -> dict:
        """从 models/ 目录加载所有 YAML 文件并合并
        
        Returns:
            合并后的 models 字典
        
        Raises:
            ConfigError: models/ 目录缺失、存在废弃的 models.yaml、
                         或检测到模型键冲突
        """
        models_dir = self.config_dir / "models"
        models_yaml = self.config_dir / "models.yaml"
        
        if not models_dir.exists():
            if models_yaml.exists():
                raise ConfigError(
                    "models/ 目录不存在。models.yaml 单文件已废弃，"
                    "请拆分到 models/ 目录。参考：`smr init` 生成新模板"
                )
            else:
                raise ConfigError(
                    f"Configuration directory not found: {models_dir}"
                )
        
        merged_models = {}
        yaml_files = sorted(models_dir.glob("*.yaml"))
        
        for filepath in yaml_files:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            file_models = data.get("models", {})
            for model_name, model_config in file_models.items():
                if model_name in merged_models:
                    raise ConfigError(
                        f"模型 '{model_name}' 在多个文件中定义，"
                        f"发生冲突：{filepath.name}"
                    )
                merged_models[model_name] = model_config
        
        return merged_models
    
    def _load_yaml(self, filename: str) -> dict:
        """加载单个 YAML 文件"""
        filepath = self.config_dir / filename
        if not filepath.exists():
            raise ConfigError(f"Configuration file not found: {filepath}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def validate(self) -> list[str]:
        """验证配置，返回错误列表（空表示通过）"""
        errors = []

        # 检查文件/目录存在
        if not (self.config_dir / "providers.yaml").exists():
            errors.append("Missing configuration file: providers.yaml")
        
        models_dir = self.config_dir / "models"
        models_yaml = self.config_dir / "models.yaml"
        if not models_dir.exists():
            if models_yaml.exists():
                errors.append(
                    "models/ 目录不存在。models.yaml 单文件已废弃，"
                    "请拆分到 models/ 目录。参考：`smr init` 生成新模板"
                )
            else:
                errors.append("Missing configuration directory: models/")
        
        if not (self.config_dir / "routing.yaml").exists():
            errors.append("Missing configuration file: routing.yaml")

        if errors:
            return errors

        # 尝试加载并验证
        try:
            self.load()
        except ConfigError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected error: {e}")

        return errors

    def save_providers(self, providers_raw: dict) -> None:
        """保存 providers 配置到 YAML 文件

        Args:
            providers_raw: 原始 provider 字典，直接序列化写入

        Raises:
            ConfigError: 写入或验证失败时抛出
        """
        filepath = self.config_dir / "providers.yaml"

        # 写入前备份原文件（简单备份）
        if filepath.exists():
            backup_path = filepath.with_suffix(".yaml.bak")
            try:
                backup_path.write_text(filepath.read_text(), encoding="utf-8")
            except IOError:
                pass  # 备份失败不影响主流程

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    {"providers": providers_raw},
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
        except Exception as e:
            raise ConfigError(f"Failed to write providers.yaml: {e}") from e

        # 写入后验证整体配置一致性
        errors = self.validate()
        if errors:
            # 验证失败，尝试恢复备份
            if backup_path.exists():
                try:
                    filepath.write_text(backup_path.read_text(), encoding="utf-8")
                except IOError:
                    pass
            raise ConfigError(f"Config validation failed after save: {'; '.join(errors)}")

    def save_routing(self, routing_raw: dict) -> None:
        """保存 routing 配置到 YAML 文件

        Args:
            routing_raw: 原始 routing 字典，直接序列化写入

        Raises:
            ConfigError: 写入或验证失败时抛出
        """
        filepath = self.config_dir / "routing.yaml"

        # 备份原文件
        if filepath.exists():
            backup_path = filepath.with_suffix(".yaml.bak")
            try:
                backup_path.write_text(filepath.read_text(), encoding="utf-8")
            except IOError:
                pass

        try:
            # 尝试使用 ruamel.yaml 保留注释
            try:
                from ruamel.yaml import YAML
                yaml_inst = YAML()
                yaml_inst.preserve_quotes = True
                yaml_inst.default_flow_style = False

                # 读取现有文件以保留注释
                if filepath.exists():
                    with open(filepath, "r", encoding="utf-8") as f:
                        existing = yaml_inst.load(f)
                    # 合并新数据
                    existing.update(routing_raw)
                else:
                    existing = routing_raw

                with open(filepath, "w", encoding="utf-8") as f:
                    yaml_inst.dump(existing, f)
            except ImportError:
                # 回退到标准 yaml
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.safe_dump(
                        routing_raw,
                        f,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                    )
        except Exception as e:
            raise ConfigError(f"Failed to write routing.yaml: {e}") from e

        # 写入后验证
        errors = self.validate()
        if errors:
            if backup_path.exists():
                try:
                    filepath.write_text(backup_path.read_text(), encoding="utf-8")
                except IOError:
                    pass
            raise ConfigError(f"Config validation failed after save: {'; '.join(errors)}")

    def save_model(self, provider_name: str, model_name: str, enabled: bool) -> None:
        """保存单个模型的 enabled 状态到对应 YAML 文件

        Args:
            provider_name: Provider 名称，用于定位文件 models/{provider_name}.yaml
            model_name: 模型名称
            enabled: 开关状态

        Raises:
            ConfigError: 文件不存在、模型不存在、写入失败或验证失败
        """
        filepath = self.config_dir / "models" / f"{provider_name}.yaml"
        if not filepath.exists():
            raise ConfigError(f"Configuration file not found: {filepath}")

        # 备份原文件
        backup_path = filepath.with_suffix(".yaml.bak")
        if filepath.exists():
            try:
                backup_path.write_text(filepath.read_text(encoding="utf-8"), encoding="utf-8")
            except IOError:
                pass

        # 读取并修改
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigError(f"Failed to read {filepath}: {e}") from e

        models = data.get("models", {})
        if model_name not in models:
            raise ConfigError(f"Model '{model_name}' not found in {filepath.name}")

        models[model_name]["enabled"] = enabled

        # 尝试使用 ruamel.yaml 保留注释
        try:
            from ruamel.yaml import YAML
            yaml_inst = YAML()
            yaml_inst.preserve_quotes = True
            yaml_inst.default_flow_style = False

            with open(filepath, "r", encoding="utf-8") as f:
                existing = yaml_inst.load(f)
            existing["models"][model_name]["enabled"] = enabled

            with open(filepath, "w", encoding="utf-8") as f:
                yaml_inst.dump(existing, f)
        except ImportError:
            # 回退到标准 yaml
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.safe_dump(
                        data,
                        f,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                    )
            except Exception as e:
                raise ConfigError(f"Failed to write {filepath}: {e}") from e

        # 写入后验证
        errors = self.validate()
        if errors:
            if backup_path.exists():
                try:
                    filepath.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                except IOError:
                    pass
            raise ConfigError(f"Config validation failed after save: {'; '.join(errors)}")

    def create_provider(self, name: str, api_base: str, api_key: str, timeout: int = 30) -> None:
        """创建新的 provider 配置

        Args:
            name: Provider 名称，只允许字母、数字、下划线和连字符
            api_base: API 基础地址
            api_key: API 密钥
            timeout: 超时时间（秒），默认 30

        Raises:
            ConfigError: 名称格式非法或已存在时抛出
        """
        # 校验 name 格式：只允许字母数字下划线和连字符
        if not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            raise ConfigError(f"Invalid provider name '{name}': only alphanumeric, underscore and hyphen are allowed")

        # 读取现有 providers 配置
        providers_data = self._load_yaml("providers.yaml")
        providers = providers_data.get("providers", {})

        # 检查名称是否已存在
        if name in providers:
            raise ConfigError(f"Provider '{name}' already exists")

        # 构造 provider 节点
        providers[name] = {
            "api_base": api_base,
            "api_key": api_key,
            "timeout": timeout,
        }

        # 保存并触发验证+回滚机制
        self.save_providers(providers)


class ConfigError(Exception):
    """配置错误"""
    pass


def load_config(config_dir: Optional[Path] = None) -> Config:
    """便捷函数：加载 V3 配置"""
    if config_dir is None:
        config_dir = Path.cwd()
    
    loader = ConfigLoader(config_dir)
    return loader.load()
