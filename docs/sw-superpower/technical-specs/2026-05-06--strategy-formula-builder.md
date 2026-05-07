# Spec: 策略公式化与 Dashboard 构建器

> **日期**: 2026-05-06
> **状态**: 设计完成，待实现
> **范围**: Core (Python) + Frontend (TypeScript/Vite)
> **目标**: 将硬编码的 `auto`/`cost` 策略替换为可配置的全局线性评分公式，并提供 Dashboard 可视化构建器

---

## 1. 背景与动机

当前 `V3ModelSelector` 的评分逻辑是硬编码的：
- `auto` 策略：使用 `tasks.<task>.capability_weights` 进行加权
- `cost` 策略：按 `cost` 降序 + quality 过滤

用户希望在 Dashboard 中**可视化配置评分公式**，从而统一成一个 `auto` 策略，让公式本身表达所有需求。

---

## 2. 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 配置粒度 | **全局统一** | 用户明确选择，配置更简洁 |
| 公式类型 | **线性加权** | 用户明确选择，足够表达需求 |
| 过滤条件 | **软过滤（权重偏好）** | 不硬排除模型，低 quality 模型得分低但不会选中。配置更简洁 |
| Dashboard | **完整构建器** | 用户明确选择，含滑块、预览、模板 |
| 向后兼容 | **自动迁移旧配置** | 旧 `capability_weights` 取均值作为全局公式；`strategy` 参数 deprecated |
| 持久化位置 | `routing.yaml` | 复用现有配置体系，支持热重载 |

---

## 3. 架构概览

```
User (Dashboard)
    ↓
Frontend: 公式构建器 UI
    ├── 能力滑块（quality/cost/reasoning/creative/context）
    ├── 实时预览（调用 /api/formula/preview）
    └── 预设模板（质量优先/成本优先/均衡）
    ↓ PUT /api/formula
Backend: Dashboard API
    ├── 验证公式有效性
    ├── 写入 routing.yaml（保留注释，使用 ruamel.yaml）
    └── 触发 ConfigWatcher 热重载
    ↓
Core: V3ModelSelector
    ├── FormulaEvaluator.evaluate(model_caps)
    │   └── score = Σ(dim × weight)
    └── 按 score 降序选最佳模型
    ↓
LiteLLM Router
```

---

## 4. 数据模型

### 4.1 `FormulaConfig`（新增 Pydantic 模型）

```python
class FormulaConfig(BaseModel):
    """全局评分公式配置"""
    
    # 能力维度权重（未指定的维度默认权重为 0）
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"quality": 0.5, "cost": 0.5},
        description="能力维度权重映射"
    )
    
    @model_validator(mode='after')
    def check_weights(self):
        """验证权重：
        1. 只包含已知的维度
        2. 至少有一个权重 > 0
        3. 权重范围 0.0 ~ 1.0
        """
        valid_dims = {"quality", "cost", "reasoning", "creative", "context"}
        unknown = set(self.weights.keys()) - valid_dims
        if unknown:
            raise ValueError(f"Unknown dimensions: {unknown}. Valid: {valid_dims}")
        if all(w == 0 for w in self.weights.values()):
            raise ValueError("At least one weight must be non-zero")
        for dim, weight in self.weights.items():
            if not (0.0 <= weight <= 1.0):
                raise ValueError(f"Weight for {dim} must be between 0.0 and 1.0, got {weight}")
        return self
```

### 4.2 `RoutingConfig` 改造

```python
class RoutingConfig(BaseModel):
    tasks: Dict[str, TaskConfig]
    difficulties: Dict[str, DifficultyConfig]
    strategies: Dict[str, StrategyConfig]  # 保留描述性字段，但不参与运行时
    
    # 新增：全局评分公式
    formula: FormulaConfig = Field(default_factory=FormulaConfig)
    
    # 移除：cost_quality_threshold（由公式自行表达）
    # 兼容：如果 routing.yaml 中仍包含 cost_quality_threshold，忽略即可
    
    # 保留：fallback 配置不变
    fallback: FallbackConfig
```

### 4.3 `TaskConfig` 改造（向后兼容）

```python
class TaskConfig(BaseModel):
    name: str
    description: str
    
    # 旧字段保留但不参与评分（仅用于向后兼容和配置迁移）
    capability_weights: Optional[Dict[str, float]] = None
    
    keywords: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
```

---

## 5. 核心组件

### 5.1 `FormulaEvaluator`（新增）

```python
class FormulaEvaluator:
    """公式执行引擎
    
    计算模型得分：score = Σ(维度值 × 权重)
    缺失维度视为 0。
    """
    
    VALID_DIMENSIONS = {"quality", "cost", "reasoning", "creative", "context"}
    
    def __init__(self, formula: FormulaConfig):
        self.formula = formula
    
    def evaluate(self, caps: ModelCapabilities) -> float:
        """计算单个模型的评分"""
        score = 0.0
        
        for dim, weight in self.formula.weights.items():
            value = getattr(caps, dim, None)
            if value is None:
                # 对于可选维度（reasoning, creative），未设置时视为 0
                continue
            score += value * weight
        
        return score
```

### 5.2 `V3ModelSelector` 改造

**关键变更**：

```python
class V3ModelSelector:
    # 移除硬编码策略
    # SUPPORTED_STRATEGIES = {"auto", "cost"}  ← 删除
    
    def __init__(self, config: Config, available_models: Optional[List[str]] = None):
        self.config = config
        self.available_models = available_models
        # 初始化公式执行器
        self.evaluator = FormulaEvaluator(config.routing.formula)
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str = "auto",  # 保留参数但忽略，始终使用 formula
        required_context: int = 0
    ) -> SelectionResult:
        
        candidates = self._filter_candidates(task_type, difficulty, required_context)
        if not candidates:
            raise NoModelAvailableError(...)
        
        # 统一使用公式评分，不再区分 auto/cost
        scored = []
        for name, model in candidates:
            score = self.evaluator.evaluate(model.capabilities)
            scored.append((name, score, model))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        best_name, best_score, best_model = scored[0]
        
        return SelectionResult(
            model_name=best_name,
            task_type=task_type,
            difficulty=difficulty,
            strategy="auto",  # 始终返回 auto
            score=best_score,
            reason=f"Formula score: {best_score:.2f}"
        )
    
    # 删除 _select_by_auto() 和 _select_by_cost()
```

### 5.3 向后兼容：旧配置迁移

在 `ConfigLoader` 中，如果加载的旧配置没有 `formula` 字段但有 `tasks.*.capability_weights`：

```python
def _migrate_legacy_weights(self, data: dict) -> dict:
    """将旧 capability_weights 迁移为全局 formula
    
    算法：按维度分别算术平均
    avg_weights[dim] = sum(task_weights[dim] for all tasks) / task_count
    """
    if "formula" in data.get("routing", {}):
        return data
    
    from collections import defaultdict
    weights_sum = defaultdict(float)
    task_count = 0
    
    for task_config in data.get("routing", {}).get("tasks", {}).values():
        cw = task_config.get("capability_weights")
        if cw:
            for dim, weight in cw.items():
                weights_sum[dim] += weight
            task_count += 1
    
    if task_count > 0:
        avg_weights = {
            dim: round(total / task_count, 4)
            for dim, total in weights_sum.items()
        }
        data.setdefault("routing", {})["formula"] = {
            "weights": avg_weights
        }
    
    return data
```

### 5.4 `strategy` 参数向后兼容

保留 `strategy` 参数但标记为 deprecated，返回时附带 warning：

```python
# V3ModelSelector.select() 中
if strategy != "auto":
    import warnings
    warnings.warn(
        f"strategy='{strategy}' is deprecated. Use routing.formula weights instead.",
        DeprecationWarning,
        stacklevel=2
    )
```

---

## 6. API 设计

### 6.1 新增端点

```python
# 获取当前公式配置
GET /api/formula
Response: {
    "weights": {
        "quality": 0.6,
        "cost": 0.4
    }
}

# 更新公式配置
PUT /api/formula
Body: {
    "weights": {
        "quality": 0.6,
        "cost": 0.4
    }
}
Response: {"success": True} | {"success": False, "errors": ["..."]}

# 预览公式效果（静态预览：按 weights 对所有模型排序）
POST /api/formula/preview
Body: {
    "weights": {
        "quality": 0.6,
        "cost": 0.4
    },
    "prompt": "帮我写一段 Python 代码"
}
Response: {
    "task_type": "coding",
    "difficulty": "medium",
    "models": [
        {"name": "gpt-4o", "score": 7.2},
        {"name": "gpt-4o-mini", "score": 5.8}
    ]
}
```

**注意**：`GET /api/formula/templates` 端点**已删除**，模板定义移至前端常量（YAGNI）。

### 6.2 现有端点改造

```python
# dry_run 不再需要 strategy 参数
POST /api/dry-run
Body: {
    "prompt": "...",
    # "strategy": "auto"  ← 可选，忽略即可
}

# 响应中 strategy 始终为 "auto"
Response: {
    "strategy": "auto",
    "score": 7.2,
    ...
}
```

---

## 7. Dashboard 前端设计

### 7.1 页面布局

```
┌─────────────────────────────────────────────┐
│  Smart Router Dashboard                      │
│  [模型] [Provider] [路由策略▶] [告警]        │
├─────────────────────────────────────────────┤
│                                              │
│  策略公式构建器                               │
│                                              │
│  ┌──────────────┐  ┌────────────────────┐   │
│  │  预设模板     │  │  能力权重滑块      │   │
│  │              │  │                    │   │
│  │  ○ 质量优先   │  │  quality ████░░ 60%│   │
│  │  ○ 成本优先   │  │  cost    ███░░░ 40%│   │
│  │  ○ 均衡       │  │  reasoning █░░░░ 0%│   │
│  │  ○ 自定义     │  │  creative  █░░░░ 0%│   │
│  │              │  │  context   █░░░░ 0%│   │
│  └──────────────┘  └────────────────────┘   │
│                                              │
│  当前公式: quality * 0.6 + cost * 0.4        │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  实时预览                               │  │
│  │  [输入测试 prompt...       ] [预览]    │  │
│  │                                        │  │
│  │  gpt-4o      ████████░░ 7.2  ★        │  │
│  │  claude-3    ██████░░░░ 6.5            │  │
│  │  gpt-4o-mini █████░░░░░ 5.8            │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [保存并应用] [重置为默认值]                   │
│                                              │
└─────────────────────────────────────────────┘
```

### 7.2 交互流程

1. 用户选择预设模板 → 滑块自动调整
2. 用户拖动滑块 → 实时更新公式文本
3. 用户输入测试 prompt → 点击预览 → 调用 `/api/formula/preview`
4. 用户点击保存 → 调用 `PUT /api/formula` → 触发后端热重载

### 7.3 预设模板（前端常量）

```typescript
const FORMULA_TEMPLATES = [
  {
    id: "quality_first",
    name: "质量优先",
    description: "优先选择高质量模型",
    weights: { quality: 0.9, cost: 0.1, reasoning: 0.0, creative: 0.0, context: 0.0 }
  },
  {
    id: "cost_first",
    name: "成本优先",
    description: "优先选择便宜模型",
    weights: { quality: 0.1, cost: 0.9, reasoning: 0.0, creative: 0.0, context: 0.0 }
  },
  {
    id: "balanced",
    name: "均衡",
    description: "质量与成本兼顾",
    weights: { quality: 0.5, cost: 0.5, reasoning: 0.0, creative: 0.0, context: 0.0 }
  }
];
```

---

## 8. 配置迁移示例

### 旧配置（迁移前）

```yaml
# routing.yaml
tasks:
  coding:
    capability_weights:
      quality: 0.6
      cost: 0.4
  chat:
    capability_weights:
      quality: 0.35
      cost: 0.65

strategies:
  auto:
    description: "..."
  cost:
    description: "..."

cost_quality_threshold: 5
```

### 新配置（迁移后）

```yaml
# routing.yaml
tasks:
  coding:
    # capability_weights 保留但不参与评分
    capability_weights:
      quality: 0.6
      cost: 0.4
  chat:
    capability_weights:
      quality: 0.35
      cost: 0.65

# 新增全局公式（取旧权重的均值）
formula:
  weights:
    quality: 0.475  # (0.6 + 0.35) / 2
    cost: 0.525     # (0.4 + 0.65) / 2

strategies:
  auto:
    name: "智能自动"
    description: "基于全局 formula 动态计算"

# cost_quality_threshold 移除
```

---

## 9. 验收标准

### 9.1 后端

- [ ] `FormulaConfig` Pydantic 模型正确验证权重（维度有效性、非零、0-1范围）
- [ ] `FormulaEvaluator` 正确计算线性加权得分（缺失维度视为 0）
- [ ] `V3ModelSelector` 使用公式替代硬编码策略（删除 auto/cost 分支）
- [ ] 旧配置无 `formula` 时自动迁移 `capability_weights`（按维度算术平均）
- [ ] `routing.yaml` 修改后触发热重载
- [ ] API 端点 `/api/formula`、`/api/formula/preview` 正常工作
- [ ] `strategy` 非 "auto" 时返回 DeprecationWarning
- [ ] 所有现有测试通过（或适配新接口后通过）

### 9.2 前端

- [ ] Dashboard 新增"路由策略"页面
- [ ] 能力权重滑块可拖动（0-100%）
- [ ] 3 个预设模板可一键切换
- [ ] 实时预览显示各模型得分排名
- [ ] 保存按钮持久化到 `routing.yaml`
- [ ] 公式验证错误友好提示

### 9.3 集成

- [ ] `make build` 前后端构建成功
- [ ] `make test` 全部通过
- [ ] 手动测试：修改公式后请求路由行为变化

---

## 10. 风险与回退

| 风险 | 缓解措施 |
|------|---------|
| 旧配置迁移导致评分行为变化 | 记录迁移日志，Dashboard 显示"旧配置已迁移"提示 |
| 公式权重总和不为 1 | 不强制归一化，权重范围 0-1，排序不受归一化影响 |
| Dashboard 公式构建器复杂度高 | 先实现基础滑块+保存，预览功能后续迭代 |
| 向后兼容 breakage | `strategy` 参数 deprecated + warning，不报错 |
| 持久化时丢失 YAML 注释 | 使用 `ruamel.yaml` 保留注释 |

---

## 11. 相关文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `core/smart_router/config/schema.py` | 修改 | 新增 `FormulaConfig`，改造 `RoutingConfig`/`TaskConfig` |
| `core/smart_router/config/loader.py` | 修改 | 新增旧配置迁移逻辑 |
| `core/smart_router/selector/v3_selector.py` | 修改 | 移除硬编码策略，使用 `FormulaEvaluator` |
| `core/smart_router/selector/formula_evaluator.py` | 新增 | 公式执行引擎 |
| `core/smart_router/gateway/dashboard_api.py` | 修改 | 新增 `/api/formula` 端点 |
| `core/smart_router/templates/routing.yaml` | 修改 | 更新默认模板 |
| `frontend/src/` | 新增/修改 | Dashboard 策略构建器页面 |
| `core/smart_router/selector/tests/test_formula_evaluator.py` | 新增 | `FormulaEvaluator` 测试 |
| `core/smart_router/config/tests/test_formula_migration.py` | 新增 | 配置迁移测试 |
| `core/smart_router/selector/tests/test_v3_selector.py` | 修改 | 适配新接口 |
| `core/smart_router/router/tests/test_plugin.py` | 修改 | 适配新接口 |
| `core/smart_router/gateway/tests/test_server.py` | 修改 | 适配新接口 |

---

*Spec 编写完成，准备进入实现计划阶段。*
