# 模型映射表（Model Mapping）- 实现计划

## 计划概览

**任务总数**: 18
**预计总时间**: 180 分钟（后端约 100 分钟，前端约 80 分钟）
**批次策略**: 一次性执行（18 个任务在 20 个以内，上下文可容纳）

---

## 后端任务

### 任务 1: 创建 ModelMapping Pydantic 模型

**文件**: `core/smart_router/config/mapping_schema.py`

**动作**: 创建 `ModelMappingRule` 和 `ModelMappingConfig` Pydantic 模型，定义 `model_mappings.yaml` 的完整 Schema

**详情**:
```python
from pydantic import BaseModel, Field, model_validator
from typing import List
import re

class ModelMappingRule(BaseModel):
    id: str = Field(description="规则唯一标识")
    enabled: bool = Field(default=True, description="规则独立开关")
    from_model: str = Field(description="匹配的请求模型名（精确匹配）")
    to_provider: str = Field(description="目标 provider 标识（仅用于展示和日志）")
    to_model: str = Field(description="目标模型名，将替换请求体中的 model 字段")
    to_litellm_provider: str = Field(default="openai", description="LiteLLM provider 前缀")
    to_base_url: str = Field(description="目标服务商 API Base URL")
    to_api_key: str = Field(description="目标 API Key，支持 os.environ/KEY_NAME 格式")
    
    @model_validator(mode='after')
    def validate_fields(self):
        if not re.match(r'^[a-zA-Z0-9_\-]+$', self.id):
            raise ValueError(f"Invalid id '{self.id}': only alphanumeric, underscore and hyphen are allowed")
        if not self.to_base_url.startswith(('http://', 'https://')):
            raise ValueError(f"to_base_url must start with http:// or https://")
        return self

class ModelMappingConfig(BaseModel):
    enabled: bool = Field(default=False, description="映射功能全局总开关")
    mappings: List[ModelMappingRule] = Field(default_factory=list, description="映射规则列表")
    
    @model_validator(mode='after')
    def validate_unique(self):
        ids = [r.id for r in self.mappings]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate mapping rule ids found")
        return self
```

**验证**:
- [ ] 文件可导入
- [ ] `ModelMappingConfig` 可正确序列化/反序列化
- [ ] 验证规则生效（重复 id、非法 base_url）

**依赖**: 无

---

### 任务 2: 编写 mapping_schema 测试

**文件**: `core/smart_router/config/tests/test_mapping_schema.py`

**动作**: 为 `ModelMappingConfig` 和 `ModelMappingRule` 编写单元测试

**详情**:
- 场景 1: 正常配置加载和验证通过
- 场景 2: 重复 `id` 时抛出 `ValidationError`
- 场景 3: `to_base_url` 不以 http/https 开头时抛出 `ValidationError`
- 场景 4: `id` 包含非法字符时抛出 `ValidationError`
- 场景 5: 空规则列表通过验证
- 场景 6: 环境变量格式的 `to_api_key` 通过验证（不做解析）

**验证**:
- [ ] 测试可运行
- [ ] 所有场景先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 1

---

### 任务 3: 创建 ModelMappingLoader

**文件**: `core/smart_router/config/mapping_loader.py`

**动作**: 实现 `ModelMappingLoader` 类，负责 `model_mappings.yaml` 的加载、保存、验证和环境变量解析

**详情**:
```python
import os
import yaml
from pathlib import Path
from typing import Optional

from .mapping_schema import ModelMappingConfig, ModelMappingRule
from .loader import ConfigError

class ModelMappingLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.filepath = self.config_dir / "model_mappings.yaml"

    def load(self) -> ModelMappingConfig:
        if not self.filepath.exists():
            return ModelMappingConfig(enabled=False, mappings=[])
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return ModelMappingConfig(**data)

    def save(self, config: ModelMappingConfig) -> None:
        backup_path = self.filepath.with_suffix(".yaml.bak")
        if self.filepath.exists():
            try:
                backup_path.write_text(self.filepath.read_text(encoding="utf-8"), encoding="utf-8")
            except IOError:
                pass
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    config.model_dump(),
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
        except Exception as e:
            if backup_path.exists():
                try:
                    self.filepath.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                except IOError:
                    pass
            raise ConfigError(f"Failed to write model_mappings.yaml: {e}") from e
        try:
            self.filepath.chmod(0o600)
        except OSError:
            pass

    def save_raw(self, raw_yaml_text: str) -> None:
        try:
            data = yaml.safe_load(raw_yaml_text)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}") from e
        try:
            config = ModelMappingConfig(**data)
        except Exception as e:
            raise ConfigError(f"Config validation failed: {e}") from e
        self.save(config)

    @staticmethod
    def resolve_api_key(api_key: str) -> str:
        if api_key.startswith("os.environ/"):
            env_var = api_key.replace("os.environ/", "")
            return os.environ.get(env_var, "")
        return api_key
```

**验证**:
- [ ] 文件可导入
- [ ] `load()` 正确解析 YAML
- [ ] `save()` 带备份和回滚
- [ ] `save_raw()` 验证失败时回滚
- [ ] `resolve_api_key()` 正确解析环境变量

**依赖**: 任务 1

---

### 任务 4: 编写 mapping_loader 测试

**文件**: `core/smart_router/config/tests/test_mapping_loader.py`

**动作**: 为 `ModelMappingLoader` 编写单元测试

**详情**:
- 场景 1: `load()` 加载存在的 YAML 文件
- 场景 2: `load()` 文件不存在时返回默认空配置
- 场景 3: `save()` 保存配置后文件内容与预期一致
- 场景 4: `save_raw()` 保存有效 YAML 后配置正确
- 场景 5: `save_raw()` 保存无效 YAML 时抛出 `ConfigError` 且原文件不被破坏
- 场景 6: `resolve_api_key()` 解析 `os.environ/KEY_NAME`
- 场景 7: `resolve_api_key()` 返回普通字符串原值

**验证**:
- [ ] 测试可运行
- [ ] 所有场景先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 3

---

### 任务 5: 创建 model_mappings.yaml 默认模板

**文件**: `core/smart_router/templates/model_mappings.yaml`

**动作**: 创建默认的 `model_mappings.yaml` 模板文件

**详情**:
```yaml
# Model Mappings Configuration
# 模型映射表：将特定模型名称的请求转发到目标服务商
# 优先级：映射表 > Model Override > 智能路由

enabled: false  # 全局开关

mappings: []
  # 映射规则示例（取消注释并修改后生效）：
  # - id: "map-gpt4-to-qwen"
  #   enabled: true
  #   from_model: "gpt-4"
  #   to_provider: "aliyun"
  #   to_model: "qwen-max"
  #   to_litellm_provider: "openai"
  #   to_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  #   to_api_key: "os.environ/DASHSCOPE_API_KEY"
```

**验证**:
- [ ] 文件存在且内容正确
- [ ] YAML 语法有效
- [ ] `ModelMappingLoader.load()` 能正确加载此模板

**依赖**: 无（可与任务 1-4 并行）

---

### 任务 6: 扩展 SmartRouter 支持模型映射

**文件**: `core/smart_router/router/plugin.py`

**动作**: 扩展 `SmartRouter.__init__` 和 `reload_config`，加载映射配置并在 LiteLLM model_list 中注册映射目标虚拟模型

**详情**:
- 修改 `__init__` 签名：`def __init__(self, config: Config, config_dir: Optional[Path] = None, *args, **kwargs)`
- 新增 `self.config_dir = config_dir`
- 新增 `self.model_mappings: Optional[ModelMappingConfig] = None`
- 在 `__init__` 中调用 `self._load_model_mappings()`
- 修改 `litellm_model_list` 构建逻辑，调用 `self._build_litellm_model_list(config, self.model_mappings)`
- 新增 `_load_model_mappings()`：使用 `ModelMappingLoader` 加载配置
- 新增 `_build_litellm_model_list(config, mappings)`：原有模型 + 映射目标虚拟模型
- 修改 `reload_config`：同时重新加载 `model_mappings` 并重建 model_list

**关键代码**:
```python
def _build_litellm_model_list(self, config, mappings):
    model_list = []
    for model_name in config.get_available_models():
        litellm_params = config.get_litellm_params(model_name)
        model_list.append({"model_name": model_name, "litellm_params": litellm_params})
    
    if mappings and mappings.enabled:
        for rule in mappings.mappings:
            if not rule.enabled:
                continue
            api_key = ModelMappingLoader.resolve_api_key(rule.to_api_key)
            litellm_model = f"{rule.to_litellm_provider}/{rule.to_model}"
            model_list.append({
                "model_name": rule.to_model,
                "litellm_params": {
                    "model": litellm_model,
                    "api_base": rule.to_base_url,
                    "api_key": api_key,
                    "timeout": 30,
                }
            })
    return model_list
```

**验证**:
- [ ] `SmartRouter` 可正常初始化
- [ ] 包含映射规则时，`model_list` 包含虚拟模型条目
- [ ] `reload_config` 后映射配置更新
- [ ] 不破坏现有路由逻辑

**依赖**: 任务 1, 3, 5

---

### 任务 7: 编写 SmartRouter 映射测试

**文件**: `core/smart_router/router/tests/test_plugin_mapping.py`

**动作**: 为 SmartRouter 的模型映射扩展编写单元测试

**详情**:
- 场景 1: 无映射配置时，`model_list` 只包含原有模型
- 场景 2: 有映射配置且全局开关开启时，`model_list` 包含映射目标虚拟模型
- 场景 3: 映射规则 `enabled=false` 时，不生成虚拟模型
- 场景 4: `reload_config` 后，新的映射配置生效
- 场景 5: 映射目标的 `api_key` 正确解析环境变量

**验证**:
- [ ] 测试可运行
- [ ] 所有场景先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 6

---

### 任务 8: 扩展 SmartRouterMiddleware 支持映射

**文件**: `core/smart_router/gateway/server.py`

**动作**: 在 `SmartRouterMiddleware.dispatch` 最前端插入模型映射匹配逻辑

**详情**:
- 在 `dispatch` 方法中，请求体解析后、Model Override 检查之前，添加 `_apply_model_mapping` 调用
- 匹配成功时：修改 `request._body` 中的 model 为 `to_model`，标记 `request.state`，直接调用 `call_next(request)` 并返回
- 添加响应头 `X-Smart-Router-Mapped` 等
- 新增 `_apply_model_mapping(model_name)` 方法

**关键逻辑**:
```python
def _apply_model_mapping(self, model_name: str) -> Optional[str]:
    mappings = getattr(self.router, 'model_mappings', None)
    if not mappings or not mappings.enabled:
        return None
    for rule in mappings.mappings:
        if rule.enabled and rule.from_model == model_name:
            return rule.to_model
    return None
```

**验证**:
- [ ] 全局开关关闭时，不触发映射
- [ ] 精确匹配时，请求体 model 被替换
- [ ] 匹配后直接返回，不进入后续路由逻辑
- [ ] 响应头包含映射信息

**依赖**: 任务 1, 3, 6

---

### 任务 9: 在 start_server 中注册 Dashboard API

**文件**: `core/smart_router/gateway/server.py`

**动作**: 在 `start_server` 函数中注册 4 个模型映射 Dashboard API endpoint

**详情**:
- `GET /api/model-mappings` — 返回结构化配置
- `PUT /api/model-mappings` — 保存结构化配置
- `GET /api/model-mappings/yaml` — 返回原始 YAML
- `PUT /api/model-mappings/yaml` — 保存原始 YAML

**验证**:
- [ ] 4 个 API 可访问
- [ ] GET 返回正确数据
- [ ] PUT 保存后文件更新
- [ ] 保存无效 YAML 返回 400

**依赖**: 任务 3, 8

---

### 任务 10: 编写 gateway 映射测试

**文件**: `core/smart_router/gateway/tests/test_mapping_api.py`

**动作**: 为中间件映射逻辑和 Dashboard API 编写集成测试

**详情**:
- 场景 1: 中间件精确匹配映射规则，请求体 model 被替换
- 场景 2: 中间件无匹配时，请求体不变
- 场景 3: API GET /api/model-mappings 返回正确 JSON
- 场景 4: API PUT /api/model-mappings/yaml 保存后文件内容正确
- 场景 5: API PUT 无效 YAML 返回 400
- 场景 6: 响应头包含 X-Smart-Router-Mapped

**验证**:
- [ ] 测试可运行
- [ ] 所有场景先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 8, 9

---

### 任务 11: 扩展 cli.py init 命令

**文件**: `core/smart_router/cli.py`

**动作**: 修改 `init` 命令，将 `model_mappings.yaml` 复制到用户配置目录

**详情**:
- 在 `init` 命令中，将 `model_mappings.yaml` 加入 `top_level_files` 列表
- 在 `_write_default_configs` 中添加 `model_mappings.yaml` 的默认内容写入

**验证**:
- [ ] `smart-router init` 后 `model_mappings.yaml` 存在
- [ ] `--safe` 模式下不覆盖已有文件
- [ ] `--force` 模式下覆盖已有文件

**依赖**: 任务 5

---

### 任务 12: 编写 cli init 测试

**文件**: `core/smart_router/tests/cli/test_init_mapping.py`

**动作**: 为 `init` 命令的模型映射文件生成编写测试

**详情**:
- 场景 1: `init` 生成 `model_mappings.yaml`
- 场景 2: `init --safe` 不覆盖已有 `model_mappings.yaml`
- 场景 3: 生成的文件内容可正确加载为 `ModelMappingConfig`

**验证**:
- [ ] 测试可运行
- [ ] 所有场景先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 11

---

## 前端任务

### 任务 13: 新增 ModelMapping TypeScript 类型

**文件**: `frontend/src/types/index.ts`

**动作**: 在现有 types 文件中添加模型映射相关的 TypeScript 接口

**详情**:
```typescript
export interface ModelMappingRule {
  id: string
  enabled: boolean
  from_model: string
  to_provider: string
  to_model: string
  to_litellm_provider: string
  to_base_url: string
  to_api_key: string
}

export interface ModelMappingConfig {
  enabled: boolean
  mappings: ModelMappingRule[]
}
```

**验证**:
- [ ] TypeScript 编译无错误
- [ ] 类型在其他文件中可正确引用

**依赖**: 无

---

### 任务 14: 扩展 API 客户端

**文件**: `frontend/src/api/client.ts`

**动作**: 在 `api` 对象中新增 4 个模型映射相关方法

**详情**:
```typescript
getModelMappings: () =>
  client.get<ModelMappingConfig>('/api/model-mappings').then((r) => r.data),
updateModelMappings: (data: ModelMappingConfig) =>
  client.put<{ success: boolean }>('/api/model-mappings', data).then((r) => r.data),
getModelMappingsYaml: () =>
  client.get<{ yaml: string }>('/api/model-mappings/yaml').then((r) => r.data),
updateModelMappingsYaml: (yaml: string) =>
  client.put<{ success: boolean }>('/api/model-mappings/yaml', { yaml }).then((r) => r.data),
```

**验证**:
- [ ] TypeScript 编译无错误
- [ ] 新增方法可在组件中调用

**依赖**: 任务 13

---

### 任务 15: 新增 i18n 翻译键

**文件**: `frontend/src/i18n/I18nProvider.tsx`

**动作**: 在 `dict` 中添加模型映射相关的翻译键

**详情**:
```typescript
'MAPPINGS': { zh: '模型映射', en: 'MAPPINGS' },
'Model Mapping': { zh: '模型映射', en: 'Model Mapping' },
'Global Enabled': { zh: '全局启用', en: 'Global Enabled' },
'From Model': { zh: '源模型', en: 'From Model' },
'To Model': { zh: '目标模型', en: 'To Model' },
'To Provider': { zh: '目标 Provider', en: 'To Provider' },
'To Base URL': { zh: '目标 Base URL', en: 'To Base URL' },
'To API Key': { zh: '目标 API Key', en: 'To API Key' },
'Add Mapping': { zh: '添加映射', en: 'Add Mapping' },
'Edit Mapping': { zh: '编辑映射', en: 'Edit Mapping' },
'Delete Mapping': { zh: '删除映射', en: 'Delete Mapping' },
'YAML Editor': { zh: 'YAML 编辑器', en: 'YAML Editor' },
'Table View': { zh: '表格视图', en: 'Table View' },
'No mappings configured': { zh: '暂无映射规则', en: 'No mappings configured' },
```

**验证**:
- [ ] TypeScript 编译无错误
- [ ] 翻译键在组件中可正确显示

**依赖**: 无

---

### 任务 16: 创建 ModelMappingTab 组件

**文件**: `frontend/src/components/ModelMappingTab.tsx`

**动作**: 创建模型映射 Tab 主组件，包含表格视图和 YAML 编辑器

**详情**:
- 使用 React hooks（useState, useEffect）管理状态
- 全局开关 Toggle（顶部）
- 视图切换按钮（表格 / YAML）
- 表格视图：
  - 规则列表（from_model → to_model, to_provider, enabled 开关）
  - 每行编辑/删除按钮
  - 底部"添加规则"按钮，点击弹出表单模态框
- YAML 视图：
  - 全宽 textarea（等宽字体，min-h-[400px]）
  - 保存按钮
- 错误提示：顶部显示保存错误
- 使用现有 `useDashboardStore` 的 `fetchAll` 或直接调用 API

**关键结构**:
```tsx
export function ModelMappingTab() {
  const [config, setConfig] = useState<ModelMappingConfig>({ enabled: false, mappings: [] })
  const [viewMode, setViewMode] = useState<'table' | 'yaml'>('table')
  const [yamlText, setYamlText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editingRule, setEditingRule] = useState<ModelMappingRule | null>(null)
  const { t } = useTranslation()

  useEffect(() => { fetchConfig(); fetchYaml() }, [])

  const fetchConfig = async () => { ... }
  const fetchYaml = async () => { ... }
  const saveConfig = async () => { ... }
  const saveYaml = async () => { ... }
  const handleToggleRule = (id: string, enabled: boolean) => { ... }
  const handleDeleteRule = (id: string) => { ... }
  const handleSaveRule = (rule: ModelMappingRule) => { ... }

  return (
    <div className="space-y-4">
      {/* 全局开关 + 视图切换 */}
      {/* 错误提示 */}
      {/* viewMode === 'table' ? <TableView /> : <YamlEditor /> */}
    </div>
  )
}
```

**验证**:
- [ ] 组件可正常渲染
- [ ] 表格视图正确展示规则列表
- [ ] YAML 视图正确展示 YAML 内容
- [ ] 全局开关可切换
- [ ] 保存按钮触发 API 调用

**依赖**: 任务 13, 14, 15

---

### 任务 17: 编写 ModelMappingTab 测试

**文件**: `frontend/src/components/ModelMappingTab.test.tsx`

**动作**: 为 ModelMappingTab 组件编写单元测试

**详情**:
- 场景 1: 组件渲染，显示"暂无映射规则"
- 场景 2: 加载配置后，表格视图显示规则列表
- 场景 3: 切换视图到 YAML 编辑器
- 场景 4: 全局开关 Toggle 切换
- 场景 5: 删除规则按钮触发确认
- 场景 6: 保存 YAML 按钮触发 API 调用
- Mock API 调用（使用 `vi.mock` 或 msw）

**验证**:
- [ ] 测试可运行
- [ ] 所有场景先失败（RED）→ 实现后通过（GREEN）

**依赖**: 任务 16

---

### 任务 18: 扩展 App.tsx

**文件**: `frontend/src/App.tsx`

**动作**: 在 tabs 数组和 Switch 路由中添加"模型映射"入口

**详情**:
- 在 `tabs` 数组中添加：
  ```typescript
  { key: 'mappings', label: t('MAPPINGS'), path: '/mappings', icon: (...) }
  ```
- 在 `Switch` 中添加：
  ```tsx
  <Route path="/mappings" component={ModelMappingTab} />
  ```
- 导入 `ModelMappingTab`

**验证**:
- [ ] Dashboard 中显示"模型映射" Tab
- [ ] 点击 Tab 切换到模型映射页面
- [ ] 路由 `/mappings` 正确渲染 ModelMappingTab

**依赖**: 任务 16

---

## 深度自检

### 完整性
- [x] 无待办事项、无占位符、无空任务描述

### 规范对齐
- [x] 所有 technical-spec 中的组件都有对应任务
- [x] 验收标准全部有对应的实现或测试任务覆盖

### 任务分解
- [x] 每个任务边界清晰，能在 10 分钟以内完成

### 可构建性
- [x] 文件路径明确
- [x] 创建任务提供了完整代码结构
- [x] 修改任务提供了关键逻辑和变更位置
- [x] 测试任务提供了场景列表

### 验收标准覆盖

| 验收标准 | 对应任务 |
|---------|---------|
| `smart-router init` 生成 `model_mappings.yaml` | 任务 5, 11, 12 |
| 全局开关关闭时请求不触发映射 | 任务 8, 10 |
| 全局开关开启且规则 enabled 时请求转发 | 任务 6, 8, 10 |
| 响应头包含映射信息 | 任务 8, 10 |
| Dashboard 新增"模型映射" Tab | 任务 16, 18 |
| Dashboard YAML 编辑器修改保存生效 | 任务 9, 14, 16, 17 |
| API Key 支持 `os.environ/KEY_NAME` | 任务 3, 4, 6, 7 |
| 重复 `from_model` 取第一条 | 任务 8, 10 |
| 保存无效配置时显示错误且不破坏原文件 | 任务 3, 4, 9, 10 |
| 目标模型不需要预先定义 | 任务 6, 7 |

### 顺序合理性
- [x] 基础组件优先（任务 1 schema → 任务 3 loader）
- [x] 实现+测试成对相邻
- [x] 前端任务在后端核心完成后执行
- [x] App.tsx 修改在最后（依赖 ModelMappingTab）

---

## 下一步

调用 `sw-subagent-development` 执行此计划。
