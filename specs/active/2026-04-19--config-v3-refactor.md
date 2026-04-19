# Smart Router Config V3 重构规格

**日期**: 2026-04-19  
**状态**: 待实现  
**决策**: 完全重写，不兼容 V1/V2，一次性替换

---

## 1. 背景与目标

### 1.1 当前痛点

V2 配置存在以下耦合问题：

1. **API Key 重复配置**: 每个模型重复配置 `api_key` 和 `api_base`
2. **路由列表硬编码**: `stage_routing` 需要手动维护 15 个模型列表（5 任务 × 3 难度）
3. **模型能力不透明**: 模型的 quality/speed/cost 没有量化声明
4. **Fallback 手动维护**: 需要单独配置 `fallback_chain`

### 1.2 目标

实现三层完全解耦的配置架构：
- **Provider 层**: 纯连接信息（key/base）
- **Model 层**: 纯能力声明（quality/speed/cost）
- **Routing 层**: 纯策略配置（任务定义 + 路由算法）

**预期收益**:
- 增减模型只需改一处
- 路由策略完全动态计算
- Fallback 自动推导
- 配置更清晰，易于维护

---

## 2. 架构设计

### 2.1 三层架构概览

```
config/
├── providers.yaml     # 服务商连接信息
├── models.yaml        # 模型能力声明  
└── routing.yaml       # 任务定义与路由策略
```

**数据流**:

```
用户请求
    ↓
[routing.yaml] 识别任务类型 → 选择策略
    ↓
[models.yaml] 按 capabilities 筛选 → 评分排序
    ↓
[providers.yaml] 获取连接参数
    ↓
LiteLLM Proxy
```

### 2.2 Provider 层设计

**职责**: 管理服务商的连接信息（API Key、Base URL、超时等）

**示例** (`providers.yaml`):

```yaml
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY
    timeout: 30
    
  anthropic:
    api_base: https://api.anthropic.com
    api_key: os.environ/ANTHROPIC_API_KEY
    
  moonshot:
    api_base: https://api.moonshot.ai/v1
    api_key: os.environ/MOONSHOT_API_KEY
    
  aliyun:
    api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key: os.environ/DASHSCOPE_API_KEY
```

**Schema**:

```python
class ProviderConfig(BaseModel):
    api_base: str
    api_key: str                      # "os.environ/KEY_NAME" 或直接 key
    timeout: int = 30
    default_headers: Dict[str, str] = {}
    rate_limit: Optional[int] = None  # 每分钟请求数限制
```

### 2.3 Model 层设计

**职责**: 声明模型的能力属性（质量、速度、成本、支持的任务类型和难度）

**示例** (`models.yaml`):

```yaml
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9          # 1-10，质量评分
      speed: 8            # 1-10，响应速度
      cost: 3             # 1-10，成本（10=最便宜）
      context: 128000     # 上下文窗口
    supported_tasks: [code_review, writing, reasoning, chat, brainstorming]
    difficulty_support: [easy, medium, hard]
    
  gpt-4o-mini:
    provider: openai
    litellm_model: openai/gpt-4o-mini
    capabilities:
      quality: 6
      speed: 9
      cost: 9
      context: 128000
    supported_tasks: [brainstorming, chat, writing]
    difficulty_support: [easy, medium]  # 明确不支持 hard
    
  claude-3-opus:
    provider: anthropic
    litellm_model: anthropic/claude-3-opus-20240229
    capabilities:
      quality: 10
      speed: 4
      cost: 2
      context: 200000
    supported_tasks: [code_review, reasoning, writing]
    difficulty_support: [medium, hard]  # 不处理简单任务
```

**Schema**:

```python
class ModelCapabilities(BaseModel):
    quality: int = Field(ge=1, le=10)
    speed: int = Field(ge=1, le=10)
    cost: int = Field(ge=1, le=10)   # 10 = 最便宜
    context: int

class ModelConfig(BaseModel):
    provider: str                     # 引用 providers.yaml 中的名称
    litellm_model: str                # LiteLLM 格式，如 "openai/gpt-4o"
    capabilities: ModelCapabilities
    supported_tasks: List[str]
    difficulty_support: List[Literal["easy", "medium", "hard"]]
```

### 2.4 Routing 层设计

**职责**: 定义任务类型、难度等级、路由策略

**示例** (`routing.yaml`):

```yaml
# 任务类型定义
tasks:
  code_review:
    name: "代码审查"
    description: "审查代码质量、发现 bug、建议改进"
    capability_weights:
      quality: 0.6
      speed: 0.2
      cost: 0.2
      
  reasoning:
    name: "逻辑推理"
    capability_weights:
      quality: 0.7
      speed: 0.1
      cost: 0.2
      
  writing:
    name: "写作"
    capability_weights:
      quality: 0.5
      speed: 0.3
      cost: 0.2
      
  brainstorming:
    name: "头脑风暴"
    capability_weights:
      quality: 0.3
      speed: 0.5
      cost: 0.2
      
  chat:
    name: "普通对话"
    capability_weights:
      quality: 0.4
      speed: 0.4
      cost: 0.2

# 难度定义
difficulties:
  easy:
    description: "简单任务，适合轻量级模型"
    max_tokens: 2000
    
  medium:
    description: "中等复杂度"
    max_tokens: 8000
    
  hard:
    description: "复杂任务，需要高质量模型"
    max_tokens: 32000

# 路由策略
strategies:
  auto:
    description: "综合评分，平衡质量/速度/成本"
    # 使用 task.capability_weights 计算得分
    
  quality:
    description: "质量优先"
    sort_by: quality
    order: desc
    
  speed:
    description: "速度优先"
    sort_by: speed
    order: desc
    
  cost:
    description: "成本优先"
    sort_by: cost
    order: desc

# Fallback 配置
fallback:
  mode: auto
  # 自动推导规则：quality 差异 <= threshold 的模型互为 fallback
  similarity_threshold: 2
```

**Schema**:

```python
class TaskConfig(BaseModel):
    name: str
    description: str
    capability_weights: Dict[str, float]  # quality/speed/cost 权重，总和应为 1.0

class DifficultyConfig(BaseModel):
    description: str
    max_tokens: int

class StrategyConfig(BaseModel):
    description: str
    # auto 策略使用 task 的 weights
    # quality/speed/cost 策略由代码硬编码处理

class FallbackConfig(BaseModel):
    mode: Literal["auto"] = "auto"
    similarity_threshold: int = 2

class RoutingConfig(BaseModel):
    tasks: Dict[str, TaskConfig]
    difficulties: Dict[str, DifficultyConfig]
    strategies: Dict[str, StrategyConfig]
    fallback: FallbackConfig
```

---

## 3. 核心算法

### 3.1 模型选择算法

```python
def select_model(
    config: ConfigV3,
    task_type: str, 
    difficulty: str, 
    strategy: str = "auto"
) -> str:
    """
    模型选择流程：
    1. 过滤：支持任务类型 + 支持难度
    2. 评分：按策略计算综合得分
    3. 排序：返回得分最高模型
    """
    
    # Step 1: 基础过滤
    candidates = []
    for name, model in config.models.items():
        if task_type not in model.supported_tasks:
            continue
        if difficulty not in model.difficulty_support:
            continue
        candidates.append((name, model))
    
    if not candidates:
        raise NoModelAvailableError(
            f"No model supports {task_type}/{difficulty}"
        )
    
    # Step 2 & 3: 策略评分与排序
    if strategy == "auto":
        task_weights = config.routing.tasks[task_type].capability_weights
        
        scored = []
        for name, model in candidates:
            caps = model.capabilities
            score = (
                caps.quality * task_weights.get("quality", 0.33) +
                caps.speed * task_weights.get("speed", 0.33) +
                caps.cost * task_weights.get("cost", 0.34)
            )
            scored.append((name, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]
    
    elif strategy in ["quality", "speed", "cost"]:
        attr = strategy
        candidates.sort(
            key=lambda x: getattr(x[1].capabilities, attr),
            reverse=True
        )
        return candidates[0][0]
    
    else:
        raise UnknownStrategyError(f"Unknown strategy: {strategy}")
```

### 3.2 Fallback 自动推导算法

```python
def derive_fallback_chains(
    models: Dict[str, ModelConfig],
    threshold: int = 2
) -> Dict[str, List[str]]:
    """
    基于 quality 相似度自动推导 fallback 链
    
    规则：
    1. 对于每个模型，找到 quality 差异 <= threshold 的其他模型
    2. 按 quality 降序排列
    3. 排除自身
    
    示例：
    - gpt-4o (quality=9) → [claude-3-opus(10), deepseek-chat(8)]
    - gpt-4o-mini (quality=6) → [deepseek-chat(8), kimi-k2(7)]
    """
    chains = {}
    
    for name, model in models.items():
        candidates = []
        model_quality = model.capabilities.quality
        
        for other_name, other in models.items():
            if other_name == name:
                continue
            
            quality_diff = abs(other.capabilities.quality - model_quality)
            if quality_diff <= threshold:
                candidates.append((other_name, other.capabilities.quality))
        
        # 按 quality 降序排列
        candidates.sort(key=lambda x: x[1], reverse=True)
        chains[name] = [n for n, _ in candidates]
    
    return chains
```

### 3.3 配置加载与验证

```python
class ConfigV3(BaseModel):
    """V3 配置根对象"""
    providers: Dict[str, ProviderConfig]
    models: Dict[str, ModelConfig]
    routing: RoutingConfig
    
    # 运行时派生
    _fallback_chains: Dict[str, List[str]] = PrivateAttr()
    
    @model_validator(mode="after")
    def validate_references(self):
        """验证 models 引用的 provider 都存在"""
        for name, model in self.models.items():
            if model.provider not in self.providers:
                raise ValueError(
                    f"Model '{name}' references unknown provider '{model.provider}'"
                )
        return self
    
    def model_post_init(self, __context):
        """预计算 fallback 链"""
        self._fallback_chains = derive_fallback_chains(
            self.models,
            self.routing.fallback.similarity_threshold
        )
    
    def get_litellm_params(self, model_name: str) -> Dict:
        """运行时组装 LiteLLM 参数"""
        model = self.models[model_name]
        provider = self.providers[model.provider]
        
        return {
            "model": model.litellm_model,
            "api_key": resolve_env_key(provider.api_key),
            "api_base": provider.api_base,
            "timeout": provider.timeout,
        }
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """获取模型的 fallback 链"""
        return self._fallback_chains.get(model_name, [])
```

---

## 4. 文件变更清单

### 4.1 新增文件

| 文件 | 说明 |
|------|------|
| `src/smart_router/config/v3_schema.py` | V3 Pydantic Schema 定义 |
| `src/smart_router/config/v3_loader.py` | V3 配置加载器 |
| `src/smart_router/selector/v3_selector.py` | V3 模型选择器 |
| `config/examples/v3/providers.yaml` | V3 Provider 示例 |
| `config/examples/v3/models.yaml` | V3 Models 示例 |
| `config/examples/v3/routing.yaml` | V3 Routing 示例 |

### 4.2 修改文件

| 文件 | 变更 |
|------|------|
| `src/smart_router/config/schema.py` | 保留 V2 schema，作为兼容性参考 |
| `src/smart_router/config/loader.py` | 修改默认加载逻辑，优先尝试 V3 |
| `src/smart_router/plugin.py` | 适配 V3 Config 接口 |
| `src/smart_router/cli.py` | 添加 V3 init 命令，生成三文件模板 |

### 4.3 删除/废弃

- 旧的单文件配置格式不再支持
- `stage_routing` 硬编码列表机制废弃
- 手动 `fallback_chain` 配置废弃

---

## 5. 迁移指南

### 5.1 手动迁移步骤

1. **提取 Providers**
   - 从原 `model_list` 收集所有唯一的 provider + api_base + api_key
   - 写入 `providers.yaml`

2. **转换 Models**
   - 为每个模型评估 quality/speed/cost 分数（1-10）
   - 声明 `supported_tasks` 和 `difficulty_support`
   - 写入 `models.yaml`

3. **配置 Routing**
   - 根据原 `classification_rules` 完善 task 定义
   - 调整各 task 的 `capability_weights`
   - 写入 `routing.yaml`

### 5.2 示例：V2 → V3 迁移

**V2 配置片段**:
```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

smart_router:
  stage_routing:
    code_review:
      easy: ["gpt-4o-mini"]
      medium: ["claude-3-sonnet"]
      hard: ["claude-3-opus"]
```

**V3 配置**:
```yaml
# providers.yaml
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY

# models.yaml
models:
  gpt-4o:
    provider: openai
    litellm_model: openai/gpt-4o
    capabilities: {quality: 9, speed: 8, cost: 3, context: 128000}
    supported_tasks: [code_review, writing, reasoning, chat, brainstorming]
    difficulty_support: [easy, medium, hard]

# routing.yaml (code_review 任务定义)
tasks:
  code_review:
    name: "代码审查"
    capability_weights: {quality: 0.6, speed: 0.2, cost: 0.2}
# 不再需要 stage_routing 硬编码列表！
```

---

## 6. 测试策略

### 6.1 单元测试

- `test_v3_schema.py`: 验证 Pydantic Schema 的校验逻辑
- `test_v3_loader.py`: 验证配置加载和引用检查
- `test_v3_selector.py`: 验证模型选择算法
- `test_fallback_derivation.py`: 验证 fallback 自动推导

### 6.2 集成测试

- 完整配置加载 → 模型选择 → LiteLLM 参数组装流程
- 多任务类型 × 多难度 × 多策略 组合测试

### 6.3 性能基准

- 配置加载时间 < 100ms（文件数增加的影响）
- 模型选择延迟 < 1ms（纯内存计算）

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 用户不熟悉新配置格式 | 高 | 提供详细的迁移指南和示例；保留旧版文档链接 |
| capability 评分主观 | 中 | 提供评分指南；社区共享评分模板 |
| 三文件管理复杂度 | 低 | CLI 提供 `validate` 命令统一检查三文件一致性 |
| 自动 fallback 不够精确 | 低 | 未来版本可支持显式覆盖 |

---

## 8. 成功标准

- [ ] 三文件配置加载正常，无引用错误
- [ ] 模型选择结果符合预期（可用 dry-run 验证）
- [ ] Fallback 链自动推导正确
- [ ] 所有单元测试通过
- [ ] 配置示例文档完整

---

## 9. 后续扩展（Out of Scope）

以下功能不在本次重构范围内，但新架构已预留支持：

- **Provider 多 Key 轮询**: `api_keys: [key1, key2]` + 负载均衡
- **动态 capability 更新**: 运行时根据实际响应时间调整 speed 评分
- **模型评分社区共享**: 导入社区维护的模型评分模板
- **图形化配置编辑器**: Web UI 编辑三文件配置

---

**Spec 版本**: 1.0  
**作者**: AI Assistant  
**最后更新**: 2026-04-19
