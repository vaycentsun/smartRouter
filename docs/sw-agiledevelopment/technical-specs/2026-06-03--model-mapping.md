---
name: model-mapping
description: "Use when implementing model mapping (model forwarding/transparency proxy) feature in Smart Router"
---

# 模型映射表（Model Mapping）

## 概述
在 Smart Router 网关层增加模型映射功能，允许通过独立的 `model_mappings.yaml` 配置文件，将特定模型名称的请求精确转发到任意目标服务商的模型，实现请求的透明代理与转发。

## 背景与动机
当前 Smart Router 的智能路由基于任务分类和模型能力评分选择最优模型，全局模型覆盖（Model Override）则强制所有请求走指定模型。两者都无法满足以下场景：
1. 将客户端请求的 `gpt-4` 转发到阿里云 DashScope 的 `qwen-max`，而不修改客户端代码
2. 为单个模型配置独立的 API Key 和 Base URL，不受 `providers.yaml` 中 provider 定义的限制
3. 临时切换某个模型背后的实际服务商，无需重启服务

模型映射作为独立的转发层，优先级高于智能路由和全局覆盖，提供轻量级、条件化的请求重定向能力。

## 目标
- [ ] 新增 `model_mappings.yaml` 配置文件，包含全局开关和映射规则列表
- [ ] 支持全局开关控制映射功能总启停，每条规则有独立 `enabled` 开关
- [ ] 仅根据请求体中的 `model` 字段进行精确匹配（字符串完全相等）
- [ ] 匹配成功后，将请求转发到规则指定的目标模型、服务商地址和认证信息
- [ ] 映射优先级最高：请求先经过映射表，再到 Model Override，最后走智能路由
- [ ] `smart-router init` 自动将默认 `model_mappings.yaml` 复制到 `~/.smart-router/`
- [ ] Dashboard 前端新增"模型映射" Tab，支持表格展示和 YAML 编辑器修改
- [ ] 配置变更后通过热重载机制在 1 秒内生效，无需重启服务
- [ ] 映射规则中的 `api_key` 支持 `os.environ/KEY_NAME` 环境变量引用格式

## 非目标
- 不支持基于请求内容（prompt 文本、消息内容）的映射匹配
- 不支持通配符、正则表达式、前缀匹配或模糊匹配
- 不支持基于请求头（如 `X-Provider`）的匹配
- 不替换或删除现有的 Model Override 和智能路由功能
- 映射层不实现 fallback 重试（仍由 LiteLLM 和 SmartRouter 中间件负责）
- 不支持映射规则的批量导入/导出
- 不在映射配置中存储目标模型的能力评分（quality、cost 等）

## 设计方案

### 架构概述
模型映射功能作为 Smart Router 请求处理链的最前端拦截层，架构上分为配置层、中间件层和网关层三部分：

1. **配置层**：独立的 `model_mappings.yaml` + `ModelMappingConfig` Pydantic 模型 + `ConfigLoader` 扩展
2. **中间件层**：`SmartRouterMiddleware.dispatch` 在最前端解析请求体，检查映射表匹配
3. **网关层**：`SmartRouter` 启动时将映射目标注册为 LiteLLM 虚拟模型，使 LiteLLM 能正确转发到目标服务商

```
HTTP Request
    |
    v
SmartRouterMiddleware.dispatch
    |
    +-- 1. 解析请求体，获取 model 字段
    +-- 2. 检查 model_mappings（优先级最高）
    |       +-- 全局开关关闭？跳过
    |       +-- 按 from_model 精确匹配
    |       +-- 匹配成功：修改 request._body 中的 model 为 to_model
    |       +-- 在 request.state 标记映射信息
    |
    +-- 3. 检查 Model Override（次优先级）
    +-- 4. 检查智能路由（auto / stage: / strategy-）
    +-- 5. 调用 LiteLLM 下游处理
    |
    v
LiteLLM Router
    |
    +-- 查找 model_name 对应的 litellm_params
    +-- 若该模型是映射目标，litellm_params 包含目标 base_url/api_key
    +-- 转发 HTTP 请求到目标服务商
```

### 组件设计

#### 组件 1: ModelMappingConfig（Pydantic 模型）
**职责**：定义 `model_mappings.yaml` 的完整 Schema，提供验证和序列化能力

**接口**:
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ModelMappingRule(BaseModel):
    id: str = Field(description="规则唯一标识，用于日志和前端展示")
    enabled: bool = Field(default=True, description="规则独立开关")
    from_model: str = Field(description="匹配的请求模型名（精确匹配）")
    to_provider: str = Field(description="目标 provider 标识（仅用于展示和日志）")
    to_model: str = Field(description="目标模型名，将替换请求体中的 model 字段")
    to_litellm_provider: str = Field(default="openai", description="LiteLLM  provider 前缀，用于构造 litellm_params.model")
    to_base_url: str = Field(description="目标服务商 API Base URL")
    to_api_key: str = Field(description="目标 API Key，支持 os.environ/KEY_NAME 格式")

class ModelMappingConfig(BaseModel):
    enabled: bool = Field(default=False, description="映射功能全局总开关")
    mappings: List[ModelMappingRule] = Field(default_factory=list, description="映射规则列表")
```

**验证规则**:
- `id` 在全局范围内唯一
- `from_model` 在 `mappings` 列表内唯一（重复时 YAML 中靠前的优先）
- `to_base_url` 必须为有效 URL（以 http:// 或 https:// 开头）
- `to_api_key` 为空字符串时通过验证，但会记录警告

**依赖**:
- `pydantic`
- `core/smart_router/config/schema.py`（参考其 ProviderConfig 的验证模式）

#### 组件 2: ModelMappingLoader
**职责**：负责 `model_mappings.yaml` 的加载、保存、验证和环境变量解析

**接口**:
```python
from pathlib import Path
from typing import Optional

class ModelMappingLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self.filepath = self.config_dir / "model_mappings.yaml"

    def load(self) -> ModelMappingConfig:
        """加载 model_mappings.yaml，解析环境变量引用"""
        ...

    def save(self, config: ModelMappingConfig) -> None:
        """保存配置到 YAML，带备份和回滚机制"""
        ...

    def save_raw(self, raw_yaml_text: str) -> None:
        """保存原始 YAML 文本，解析验证后回滚"""
        ...

    def validate(self, config: ModelMappingConfig) -> list[str]:
        """验证配置，返回错误列表（空表示通过）"""
        ...

    @staticmethod
    def resolve_api_key(api_key: str) -> str:
        """解析 os.environ/KEY_NAME 格式为实际值"""
        ...
```

**实现细节**:
- `load()` 读取 YAML 后，先不做环境变量解析（保留原始字符串给前端展示），但 `resolve_api_key()` 提供解析能力
- `save()` 使用 `yaml.safe_dump` 序列化 Pydantic 模型
- `save_raw()` 先尝试 `yaml.safe_load` 原始文本，再验证，验证失败则抛出 `ConfigError`
- 保存前自动备份原文件为 `.yaml.bak`，验证失败时自动回滚

**依赖**:
- `pyyaml`
- `core/smart_router/config/loader.py`（参考 `ConfigLoader.save_providers` 的备份回滚模式）

#### 组件 3: SmartRouter 扩展
**职责**：持有 `model_mappings` 配置，启动时将映射目标注册为 LiteLLM 虚拟模型，运行时支持重载

**接口变更**:
```python
class SmartRouter(Router):
    def __init__(self, config: Config, config_dir: Optional[Path] = None, *args, **kwargs):
        self.sr_config = config
        self.config_dir = config_dir
        self.model_mappings: Optional[ModelMappingConfig] = None
        
        # 加载映射配置
        if config_dir:
            self._load_model_mappings()
        
        # 构建 LiteLLM 模型列表时，包含映射目标虚拟模型
        litellm_model_list = self._build_litellm_model_list(config, self.model_mappings)
        ...

    def _load_model_mappings(self) -> None:
        """从 config_dir 加载 model_mappings.yaml"""
        ...

    def _build_litellm_model_list(self, config: Config, mappings: Optional[ModelMappingConfig]) -> list[dict]:
        """构建 LiteLLM model_list，包含原有可用模型 + 映射目标虚拟模型"""
        ...

    def reload_config(self, config: Config):
        """扩展现有方法，同时重载 model_mappings"""
        self.sr_config = config
        if self.config_dir:
            self._load_model_mappings()
        # 重建 LiteLLM 模型列表
        litellm_model_list = self._build_litellm_model_list(config, self.model_mappings)
        # 安全更新父类 Router 的模型列表
        ...
```

**虚拟模型注册逻辑**:
```python
def _build_litellm_model_list(self, config, mappings):
    model_list = []
    
    # 1. 原有可用模型（保持现有逻辑）
    for model_name in config.get_available_models():
        litellm_params = config.get_litellm_params(model_name)
        model_list.append({
            "model_name": model_name,
            "litellm_params": litellm_params
        })
    
    # 2. 映射目标虚拟模型
    if mappings and mappings.enabled:
        for rule in mappings.mappings:
            if not rule.enabled:
                continue
            
            # 解析 API Key
            api_key = ModelMappingLoader.resolve_api_key(rule.to_api_key)
            
            # 构造 LiteLLM 模型标识
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

**关键约束**：
- 映射目标的 `model_name` 使用 `to_model`，如果 `to_model` 与现有模型名冲突，映射目标优先（因为映射在中间件层已替换请求体中的 model）
- 映射目标的 `model_name` 如果相同但 `to_base_url` 不同，后定义的覆盖先定义的（需在验证阶段发出警告）

**依赖**:
- `litellm.router.Router`
- `core/smart_router/router/plugin.py`

#### 组件 4: SmartRouterMiddleware 扩展
**职责**：在请求处理链最前端拦截并执行模型映射

**接口变更**:
```python
class SmartRouterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 现有递归保护逻辑保持不变
        if request.scope.get("_smart_router_internal_retry"):
            return await call_next(request)
        
        routed = False
        
        # 只处理 chat/completions 请求
        if request.url.path == "/v1/chat/completions" and request.method == "POST":
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    original_model = data.get("model", "")
                    
                    # ====== 新增：模型映射检查（优先级最高）======
                    mapped_model = self._apply_model_mapping(original_model)
                    if mapped_model:
                        data["model"] = mapped_model
                        modified_body = json.dumps(data).encode("utf-8")
                        request._body = modified_body
                        
                        request.state.smart_router_mapped = True
                        request.state.smart_router_mapped_from = original_model
                        request.state.smart_router_mapped_to = mapped_model
                        
                        # 记录路由信息（供后续统计使用）
                        request_id = str(uuid.uuid4())[:8]
                        request.state.smart_router_request_id = request_id
                        request.state.smart_router_routing_info = {
                            "request_id": request_id,
                            "original_model": original_model,
                            "selected_model": mapped_model,
                            "task_type": "mapping",
                            "difficulty": None,
                            "strategy": "mapping",
                            "fallback_chain": [],
                        }
                        
                        console.print(f"[cyan]模型映射: {original_model} -> {mapped_model}[/cyan]")
                        
                        # 映射后直接透传，不再进入后续路由逻辑
                        response = await call_next(request)
                        
                        # 添加映射响应头
                        response.headers["X-Smart-Router-Mapped"] = "true"
                        response.headers["X-Smart-Router-Mapped-From"] = original_model
                        response.headers["X-Smart-Router-Mapped-To"] = mapped_model
                        
                        return response
                    
                    # ====== 原有逻辑继续：Model Override / 智能路由 ======
                    # ... 保持现有代码不变 ...
                    
            except Exception as e:
                console.print(f"[yellow]模型映射处理失败: {e}[/yellow]")
                import traceback
                console.print(traceback.format_exc())
        
        # 原有逻辑：未映射的请求继续走后续流程
        if not routed:
            response = await call_next(request)
        
        # ... 后续响应头添加逻辑保持不变 ...
        return response
    
    def _apply_model_mapping(self, model_name: str) -> Optional[str]:
        """检查模型映射表，返回映射后的模型名，无匹配返回 None"""
        mappings = getattr(self.router, 'model_mappings', None)
        if not mappings or not mappings.enabled:
            return None
        
        for rule in mappings.mappings:
            if rule.enabled and rule.from_model == model_name:
                return rule.to_model
        
        return None
```

**关键决策**：映射匹配后**直接调用 `call_next`**，不再进入 Model Override 和智能路由逻辑。这确保了映射优先级最高。

**依赖**:
- `starlette.middleware.base.BaseHTTPMiddleware`
- `core/smart_router/gateway/server.py`

#### 组件 5: Dashboard API（FastAPI）
**职责**：提供模型映射配置的查询和修改接口

**接口定义**:
```python
from fastapi import HTTPException

# 获取结构化映射配置
@app.get("/api/model-mappings")
async def get_model_mappings():
    """返回当前 model_mappings.yaml 的结构化内容"""
    loader = ModelMappingLoader(config_dir)
    config = loader.load()
    return {
        "enabled": config.enabled,
        "mappings": [
            {
                "id": r.id,
                "enabled": r.enabled,
                "from_model": r.from_model,
                "to_provider": r.to_provider,
                "to_model": r.to_model,
                "to_litellm_provider": r.to_litellm_provider,
                "to_base_url": r.to_base_url,
                "to_api_key": r.to_api_key,  # 返回原始值（含 os.environ/ 前缀）
            }
            for r in config.mappings
        ]
    }

# 保存结构化映射配置
@app.put("/api/model-mappings")
async def update_model_mappings(body: dict):
    """接收 JSON，验证后保存为 YAML 并触发热重载"""
    try:
        config = ModelMappingConfig(**body)
        loader = ModelMappingLoader(config_dir)
        loader.save(config)
        return {"success": True}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 获取原始 YAML
@app.get("/api/model-mappings/yaml")
async def get_model_mappings_yaml():
    """返回原始 YAML 文本，供编辑器使用"""
    filepath = config_dir / "model_mappings.yaml"
    if not filepath.exists():
        return {"yaml": "enabled: false\nmappings: []\n"}
    return {"yaml": filepath.read_text(encoding="utf-8")}

# 保存原始 YAML
@app.put("/api/model-mappings/yaml")
async def update_model_mappings_yaml(body: dict):
    """接收 YAML 文本，验证后保存并触发热重载"""
    raw_yaml = body.get("yaml", "")
    try:
        loader = ModelMappingLoader(config_dir)
        loader.save_raw(raw_yaml)
        return {"success": True}
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**依赖**:
- `fastapi`
- `core/smart_router/gateway/server.py`

#### 组件 6: Dashboard 前端 — ModelMappingTab
**职责**：在 Dashboard 中展示和编辑模型映射规则

**组件结构**:
```typescript
// frontend/src/components/ModelMappingTab.tsx
interface ModelMappingRule {
  id: string
  enabled: boolean
  from_model: string
  to_provider: string
  to_model: string
  to_litellm_provider: string
  to_base_url: string
  to_api_key: string
}

interface ModelMappingConfig {
  enabled: boolean
  mappings: ModelMappingRule[]
}

export function ModelMappingTab() {
  const [config, setConfig] = useState<ModelMappingConfig>({ enabled: false, mappings: [] })
  const [viewMode, setViewMode] = useState<'table' | 'yaml'>('table')
  const [yamlText, setYamlText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 加载配置
  const fetchConfig = async () => {
    const data = await api.getModelMappings()
    setConfig(data)
  }

  const fetchYaml = async () => {
    const data = await api.getModelMappingsYaml()
    setYamlText(data.yaml)
  }

  // 保存配置（表格模式）
  const saveConfig = async () => {
    setLoading(true)
    try {
      await api.updateModelMappings(config)
      setError(null)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // 保存 YAML
  const saveYaml = async () => {
    setLoading(true)
    try {
      await api.updateModelMappingsYaml({ yaml: yamlText })
      setError(null)
      await fetchConfig() // 重新加载以同步
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ... JSX 渲染 ...
}
```

**界面设计**:
- 顶部：全局开关 Toggle + "模型映射"标题 + 视图切换按钮（表格 / YAML）
- 表格视图：
  - 规则列表，每行展示 from_model → to_model、to_provider、to_base_url、enabled 开关
  - 每行有"编辑"和"删除"按钮
  - 底部有"添加规则"按钮，点击弹出表单
- YAML 视图：
  - 全宽 textarea，使用等宽字体和 YAML 语法高亮（通过 CSS 实现基础高亮，不引入重型编辑器库）
  - 行号显示（可选）
  - "保存"按钮
- 错误提示：保存失败时在顶部显示红色错误信息

**依赖**:
- `react`
- `wouter`（路由已存在，无需新增）
- `axios`（通过 `api/client.ts`）
- 现有 Tailwind CSS 样式体系

### 数据流

#### 运行时请求数据流
```
Client Request (model: "gpt-4")
    |
    v
SmartRouterMiddleware.dispatch
    |
    +-- 解析 body: {"model": "gpt-4", "messages": [...]}
    +-- _apply_model_mapping("gpt-4")
    |       +-- model_mappings.enabled == true
    |       +-- 找到规则: from_model="gpt-4" -> to_model="qwen-max"
    |       +-- 返回 "qwen-max"
    |
    +-- 修改 body: {"model": "qwen-max", "messages": [...]}
    +-- request._body = modified_body
    +-- request.state 记录映射信息
    |
    v
call_next(request) -> LiteLLM Router
    |
    +-- LiteLLM 查找 model_name="qwen-max" 的 litellm_params
    +-- 找到虚拟模型条目:
    |       {
    |           "model_name": "qwen-max",
    |           "litellm_params": {
    |               "model": "openai/qwen-max",
    |               "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    |               "api_key": "sk-xxx"
    |           }
    |       }
    |
    v
HTTP Request to Aliyun DashScope
    |
    v
Aliyun Response
    |
    v
LiteLLM -> SmartRouterMiddleware
    |
    +-- 添加响应头:
    |       X-Smart-Router-Mapped: true
    |       X-Smart-Router-Mapped-From: gpt-4
    |       X-Smart-Router-Mapped-To: qwen-max
    |       X-Smart-Router-Model: qwen-max
    |       X-Smart-Router-Original: gpt-4
    |
    v
Client Response
```

#### 配置变更数据流
```
Dashboard YAML 编辑器修改
    |
    v
PUT /api/model-mappings/yaml
    |
    v
ModelMappingLoader.save_raw()
    +-- yaml.safe_load 验证
    +-- 备份原文件
    +-- 写入新文件
    +-- ModelMappingConfig 验证
    |       +-- 失败: 恢复备份，抛出 ConfigError
    |       +-- 成功: 继续
    |
    v
ConfigWatcher 检测到文件变更
    |
    v
SmartRouter.reload_config()
    +-- 重新加载 model_mappings.yaml
    +-- 重建 LiteLLM model_list（包含新的映射目标）
    +-- 安全更新父类 Router 的模型列表
    |
    v
新配置生效（无需重启）
```

### 错误处理

| 错误场景 | 处理策略 | 返回给客户端 |
|---------|---------|------------|
| 映射规则 `to_base_url` 格式无效 | `ModelMappingConfig` 验证失败，`save()` 时抛出 `ConfigError`，回滚文件 | Dashboard 显示 400 错误详情 |
| 映射规则的 `to_api_key` 解析失败（环境变量不存在） | 启动时发出警告日志；请求到达时 LiteLLM 会返回 401，由现有 fallback 机制处理 | 客户端收到正常的 LiteLLM 错误响应 |
| 映射目标模型在 LiteLLM model_list 中注册失败 | `SmartRouter._build_litellm_model_list` 时捕获异常，跳过该映射规则，继续启动 | 服务正常启动，该映射规则不生效 |
| 多条规则具有相同的 `from_model` | 验证阶段发出警告；运行时按 YAML 中定义的顺序取第一条匹配 | 无（第一条匹配生效） |
| 映射目标 `to_model` 与现有模型名冲突 | 映射目标虚拟模型覆盖现有模型条目（因为映射在中间件层已替换 model） | 无（映射优先级高，冲突是预期行为） |
| YAML 语法错误 | `save_raw()` 时 `yaml.safe_load` 抛出异常，回滚文件 | Dashboard 显示 400 错误：YAML 语法错误 |

### 安全考虑
1. **API Key 存储**：映射规则中的 `to_api_key` 支持 `os.environ/KEY_NAME` 格式，推荐生产环境使用此方式。Dashboard 获取配置时返回原始字符串（含 `os.environ/` 前缀），不解析为实际值。
2. **配置写入权限**：`save_raw()` 保存后尝试设置文件权限为 `0o600`，防止其他用户读取 API Key。
3. **输入校验**：`to_base_url` 必须为非空字符串且以 `http://` 或 `https://` 开头；`id` 只允许字母、数字、下划线和连字符。
4. **跨站请求伪造（CSRF）**：Dashboard API 通过同源策略保护（服务绑定在 127.0.0.1 或内网），暂不额外增加 CSRF Token。

## 验收标准
- [ ] `smart-router init` 执行后，`~/.smart-router/model_mappings.yaml` 存在，包含注释说明和空规则列表示例
- [ ] 全局开关 `enabled: false` 时，无论规则如何配置，请求均不触发映射，正常走 Model Override 或智能路由
- [ ] 全局开关 `enabled: true` 且规则 `enabled: true` 时，请求 model 精确匹配 `from_model`，请求被转发到目标配置
- [ ] 映射后的请求在响应头中包含 `X-Smart-Router-Mapped: true`、`X-Smart-Router-Mapped-From`、`X-Smart-Router-Mapped-To`
- [ ] Dashboard 中新增"模型映射" Tab，能通过表格视图查看规则列表、切换规则开关、添加/删除规则
- [ ] Dashboard 中能通过 YAML 编辑器直接修改 `model_mappings.yaml` 内容，保存后配置在 1 秒内通过热重载生效
- [ ] 映射规则的 `to_api_key` 支持 `os.environ/KEY_NAME` 格式，运行时正确解析环境变量
- [ ] 当多个规则具有相同 `from_model` 时，按 YAML 中定义的顺序取第一条匹配
- [ ] 保存无效 YAML 或验证失败的配置时，Dashboard 显示明确错误信息，且原配置文件不被破坏
- [ ] 映射目标模型不需要在 `models.yaml` 或 `providers.yaml` 中预先定义

## 实现任务（概览）
1. 定义 `ModelMappingConfig` 和 `ModelMappingRule` Pydantic 模型
2. 实现 `ModelMappingLoader`（加载、保存、验证、环境变量解析）
3. 扩展 `SmartRouter.__init__` 和 `reload_config`，支持加载和注册映射目标虚拟模型
4. 扩展 `SmartRouterMiddleware.dispatch`，在最前端插入映射匹配逻辑
5. 在 `start_server` 中注册 Dashboard API（GET/PUT /api/model-mappings, /api/model-mappings/yaml）
6. 扩展 `smart-router init` 命令，生成默认 `model_mappings.yaml`
7. 前端：新增 `ModelMappingTab` 组件（表格视图 + YAML 编辑器）
8. 前端：扩展 `api/client.ts`，新增模型映射相关 API 方法
9. 前端：扩展 `App.tsx`，在 tabs 中新增"模型映射"入口
10. 编写后端单元测试（ModelMappingLoader、SmartRouter 扩展、Middleware 映射逻辑）
11. 编写前端单元测试（ModelMappingTab 组件渲染和交互）

## 技术栈
- **后端**: Python 3.9+, Pydantic, PyYAML, LiteLLM, FastAPI, Starlette
- **前端**: React 18, TypeScript, Tailwind CSS, wouter, axios
- **配置管理**: YAML, watchdog（热重载）

## 依赖

### 外部依赖
- `pydantic`（已有）
- `pyyaml`（已有）
- `watchdog`（已有）
- `fastapi`（已有，通过 LiteLLM 引入）

### 内部依赖
- `core/smart_router/config/loader.py` — 参考其备份回滚和验证模式
- `core/smart_router/config/schema.py` — 参考 ProviderConfig 和 Config 的验证模式
- `core/smart_router/config/watcher.py` — 复用其文件监听和去抖动机制
- `core/smart_router/router/plugin.py` — 扩展 SmartRouter 类
- `core/smart_router/gateway/server.py` — 扩展中间件和注册 API
- `frontend/src/api/client.ts` — 扩展 API 客户端
- `frontend/src/App.tsx` — 新增 Tab 路由

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LiteLLM 不支持运行时动态修改 model_list | 高 | 映射目标作为虚拟模型在启动时注册；运行时配置变更通过 `SmartRouter.reload_config` 调用 `set_model_list` 安全更新（参考现有 `reload_config` 中的父类更新逻辑） |
| `to_model` 与现有模型名冲突导致 LiteLLM 混淆 | 中 | 映射在中间件层已将请求 model 替换为 `to_model`，所以 LiteLLM 看到的 model_name 就是 `to_model`。如果 `to_model` 恰好是现有模型名，LiteLLM 会按 model_list 中的定义处理，但由于映射已发生，行为是确定的 |
| 映射规则指向无效 base_url 导致请求失败 | 中 | 验证阶段检查 URL 格式；Dashboard 未来可扩展"测试连通性"功能；请求失败由现有 fallback 机制处理 |
| YAML 编辑器保存错误配置导致服务不可用 | 中 | `save_raw()` 的备份回滚机制确保验证失败时文件不被破坏；全局开关可快速关闭整个映射功能 |
| 前端引入重型编辑器库增加 bundle 体积 | 低 | YAML 编辑器使用原生 textarea + CSS 语法高亮，不引入 Monaco/CodeMirror |
| 配置热重载时 `model_mappings.yaml` 变更未触发 | 高 | `ConfigWatcher` 已监听 `.yaml` 文件变更；确保 `model_mappings.yaml` 放在 `config_dir` 下即可被监听 |

## 附录

### 参考文档
- `docs/sw-agiledevelopment/business-specs/2026-06-03--model-mapping.md` — 业务需求文档
- `core/AGENTS.md` — 后端架构指南
- `frontend/AGENTS.md` — 前端开发指南
- `docs/GUIDE.md` — CLI 使用指南
- LiteLLM Router 文档: https://docs.litellm.ai/docs/proxy/virtual_keys

### 默认配置文件模板
`smart-router init` 生成的默认 `model_mappings.yaml`：

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
  #
  # - id: "map-gpt4o-to-glm"
  #   enabled: false
  #   from_model: "gpt-4o"
  #   to_provider: "zhipu"
  #   to_model: "glm-4"
  #   to_litellm_provider: "openai"
  #   to_base_url: "https://open.bigmodel.cn/api/paas/v4"
  #   to_api_key: "os.environ/ZHIPU_API_KEY"
```

### 决策记录

**决策 1**: 映射匹配后修改请求体中的 model 字段，而不是保持原 model 让 LiteLLM 通过别名解析
- **原因**: LiteLLM 的 model_list 按 `model_name` 索引，修改请求体中的 model 为最直观的实现方式，且与现有 Model Override 的处理模式一致
- **替代方案**: 在 LiteLLM model_list 中为 `from_model` 注册指向目标配置的 litellm_params。放弃原因：如果 `from_model` 同时也是现有模型名，会造成歧义

**决策 2**: 映射目标使用 `to_model` 作为 LiteLLM 虚拟模型的 `model_name`
- **原因**: 请求体已被替换为 `to_model`，LiteLLM 自然查找 `to_model` 的 litellm_params
- **替代方案**: 使用 `mapped-<from_model>` 作为虚拟模型名。放弃原因：需要额外维护 from_model 到虚拟模型名的映射关系，增加复杂度

**决策 3**: 映射规则配置独立为 `model_mappings.yaml`，不集成到 routing.yaml
- **原因**: 保持三文件架构的纯粹性，映射配置有独立的验证规则和生命周期
- **替代方案**: 在 routing.yaml 中新增 `mappings` section。放弃原因：会污染 routing 配置的语义，且 mapping 的目标模型不需要在 models.yaml 中定义，与 routing 的验证逻辑冲突

**决策 4**: 映射层拦截后不进入后续路由逻辑（Model Override / 智能路由）
- **原因**: 业务需求明确映射优先级最高。映射的本质是"透明代理"，不应再经过上层路由决策
- **替代方案**: 映射后继续走原有路由流程。放弃原因：违背业务需求，可能导致 Model Override 覆盖映射结果

**决策 5**: Dashboard YAML 编辑器使用原生 textarea，不引入 Monaco/CodeMirror
- **原因**: 保持 bundle 体积最小化；YAML 文件通常较短（< 200 行），原生 textarea 足够
- **替代方案**: 引入 Monaco Editor。放弃原因：增加约 1MB+ bundle 体积，与项目轻量级定位不符
