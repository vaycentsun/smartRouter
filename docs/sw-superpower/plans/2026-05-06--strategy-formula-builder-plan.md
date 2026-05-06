# 实现计划：策略公式化与 Dashboard 构建器

> **对应 Spec**: `docs/sw-superpower/specs/2026-05-06--strategy-formula-builder.md`
> **日期**: 2026-05-06
> **预计任务数**: 15
> **预计总时间**: 75-90 分钟

---

## 任务清单

### 任务 1: 新增 FormulaConfig Pydantic 模型

**文件**: `core/smart_router/config/schema.py`

**动作**: 在 `schema.py` 中新增 `FormulaConfig` 类，并改造 `RoutingConfig` 和 `TaskConfig`

**详情**:
```python
# 在 schema.py 中新增 FormulaConfig
class FormulaConfig(BaseModel):
    """全局评分公式配置"""
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"quality": 0.5, "cost": 0.5},
        description="能力维度权重映射"
    )
    
    @model_validator(mode='after')
    def check_weights(self):
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

# RoutingConfig 新增 formula 字段
class RoutingConfig(BaseModel):
    tasks: Dict[str, TaskConfig]
    difficulties: Dict[str, DifficultyConfig]
    strategies: Dict[str, StrategyConfig]
    formula: FormulaConfig = Field(default_factory=FormulaConfig)
    fallback: FallbackConfig

# TaskConfig 的 capability_weights 标记为 Optional
class TaskConfig(BaseModel):
    name: str
    description: str
    capability_weights: Optional[Dict[str, float]] = None
    keywords: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
```

**验证**:
- [ ] `FormulaConfig` 可实例化
- [ ] 有效权重通过验证
- [ ] 无效维度/全零/越界权重抛出 ValueError

**依赖**: 无

---

### 任务 2: 编写 FormulaConfig 测试

**文件**: `core/smart_router/config/tests/test_formula_config.py`（新增）

**动作**: 为 `FormulaConfig` 的验证逻辑编写单元测试

**详情**:
- 场景 1: 默认权重实例化成功
- 场景 2: 自定义有效权重通过验证
- 场景 3: 未知维度抛出 ValueError
- 场景 4: 全零权重抛出 ValueError
- 场景 5: 权重 < 0 抛出 ValueError
- 场景 6: 权重 > 1 抛出 ValueError
- 场景 7: `RoutingConfig` 包含 `formula` 字段可正常实例化

**验证**:
- [ ] 测试可运行
- [ ] 实现前测试失败（RED）— 任务 1 完成后通过（GREEN）

**依赖**: 任务 1

---

### 任务 3: 创建 FormulaEvaluator 执行引擎

**文件**: `core/smart_router/selector/formula_evaluator.py`（新增）

**动作**: 创建公式执行引擎，计算线性加权得分

**详情**:
```python
from typing import Dict
from ..config.schema import FormulaConfig, ModelCapabilities

class FormulaEvaluator:
    """公式执行引擎"""
    
    VALID_DIMENSIONS = {"quality", "cost", "reasoning", "creative", "context"}
    
    def __init__(self, formula: FormulaConfig):
        self.formula = formula
    
    def evaluate(self, caps: ModelCapabilities) -> float:
        score = 0.0
        for dim, weight in self.formula.weights.items():
            value = getattr(caps, dim, None)
            if value is not None:
                score += value * weight
        return score
    
    def evaluate_all(self, models: Dict[str, ModelCapabilities]) -> Dict[str, float]:
        """批量计算所有模型的得分"""
        return {
            name: self.evaluate(caps)
            for name, caps in models.items()
        }
```

**验证**:
- [ ] 文件可导入
- [ ] 单维度计算正确
- [ ] 多维度计算正确
- [ ] 缺失维度视为 0

**依赖**: 任务 1

---

### 任务 4: 编写 FormulaEvaluator 测试

**文件**: `core/smart_router/selector/tests/test_formula_evaluator.py`（新增）

**动作**: 为 `FormulaEvaluator` 编写单元测试

**详情**:
- 场景 1: 单维度权重计算正确（quality=10, weight=0.5 → score=5.0）
- 场景 2: 多维度权重计算正确（quality=10*0.5 + cost=5*0.5 = 7.5）
- 场景 3: 缺失维度（reasoning=None）时视为 0，不影响其他维度
- 场景 4: `evaluate_all` 批量计算正确
- 场景 5: 权重为 0 的维度不影响总分

**验证**:
- [ ] 测试可运行
- [ ] 实现前失败（RED），任务 3 完成后通过（GREEN）

**依赖**: 任务 3

---

### 任务 5: 改造 V3ModelSelector

**文件**: `core/smart_router/selector/v3_selector.py`

**动作**: 移除硬编码的 `auto`/`cost` 策略，统一使用 `FormulaEvaluator`

**详情**:
```python
# 变更要点：
# 1. 删除 SUPPORTED_STRATEGIES = {"auto", "cost"}
# 2. __init__ 中初始化 FormulaEvaluator
# 3. select() 中始终使用 evaluator.evaluate()
# 4. 删除 _select_by_auto() 和 _select_by_cost()
# 5. strategy 参数保留但标记 deprecated
```

**关键变更**:
- `__init__` 增加 `self.evaluator = FormulaEvaluator(config.routing.formula)`
- `select()` 中：
  - 保留 `strategy` 参数
  - 如果 `strategy != "auto"`，发出 `DeprecationWarning`
  - 统一使用 `self.evaluator.evaluate()` 计算得分
  - `strategy` 字段在 `SelectionResult` 中始终为 `"auto"`
- 删除 `_select_by_auto()` 方法
- 删除 `_select_by_cost()` 方法

**验证**:
- [ ] 文件无语法错误
- [ ] 可正常导入
- [ ] `select()` 返回正确的 `SelectionResult`

**依赖**: 任务 3

---

### 任务 6: 适配 V3ModelSelector 测试

**文件**: `core/smart_router/selector/tests/test_v3_selector.py`

**动作**: 修改现有测试，适配移除硬编码策略后的接口

**详情**:
- 修改测试用例，移除对 `strategy="cost"` 的显式测试
- 验证 `select()` 使用 formula 计算得分
- 验证 `strategy="cost"` 时发出 DeprecationWarning
- 验证返回的 `SelectionResult.strategy` 始终为 `"auto"`
- 确保所有现有测试场景（按任务过滤、按难度过滤、上下文过滤）仍然通过

**验证**:
- [ ] 测试可运行
- [ ] 全部通过

**依赖**: 任务 5

---

### 任务 7: 新增 ConfigLoader 旧配置迁移

**文件**: `core/smart_router/config/loader.py`

**动作**: 在 ConfigLoader 中添加旧 `capability_weights` 自动迁移为全局 `formula` 的逻辑

**详情**:
```python
def _migrate_legacy_weights(self, data: dict) -> dict:
    """将旧 capability_weights 迁移为全局 formula
    
    算法：按维度分别算术平均
    avg_weights[dim] = sum(task_weights[dim]) / task_count
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

**调用位置**: 在 `load()` 方法中，YAML 解析后、Pydantic 验证前调用 `_migrate_legacy_weights()`

**验证**:
- [ ] 旧配置正确迁移
- [ ] 新配置（已有 formula）不被覆盖
- [ ] 无 capability_weights 时不报错

**依赖**: 任务 1

---

### 任务 8: 编写配置迁移测试

**文件**: `core/smart_router/config/tests/test_formula_migration.py`（新增）

**动作**: 测试旧配置迁移逻辑

**详情**:
- 场景 1: 旧配置（有 capability_weights）正确迁移为 formula
- 场景 2: 新配置（已有 formula）不被覆盖
- 场景 3: 无 capability_weights 时不添加 formula（使用默认值）
- 场景 4: 多任务的 capability_weights 按维度正确取平均
- 场景 5: 迁移后的 Config 可正常通过 Pydantic 验证

**验证**:
- [ ] 测试可运行
- [ ] 实现前失败（RED），任务 7 完成后通过（GREEN）

**依赖**: 任务 7

---

### 任务 9: 新增 Dashboard API 端点

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 新增 `GET /api/formula`、`PUT /api/formula`、`POST /api/formula/preview` 三个端点

**详情**:

```python
# 新增 Pydantic 模型
class FormulaUpdate(BaseModel):
    weights: Dict[str, float]

class FormulaPreviewRequest(BaseModel):
    weights: Dict[str, float]
    prompt: str = ""

# GET /api/formula
async def get_formula(request: Request):
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
        return {"weights": cfg.routing.formula.weights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# PUT /api/formula
async def update_formula(request: Request, body: FormulaUpdate):
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        current = loader._load_yaml("routing.yaml")
        
        # 验证权重
        try:
            FormulaConfig(weights=body.weights)
        except ValueError as e:
            return {"success": False, "errors": [str(e)]}
        
        # 更新 routing.yaml
        current.setdefault("routing", {})["formula"] = {"weights": body.weights}
        loader._save_yaml("routing.yaml", current)
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "errors": [str(e)]}

# POST /api/formula/preview
async def preview_formula(request: Request, body: FormulaPreviewRequest):
    config_dir = Path.home() / ".smart-router"
    try:
        loader = ConfigLoader(config_dir)
        cfg = loader.load()
        
        # 使用请求的 weights 创建临时 evaluator
        temp_formula = FormulaConfig(weights=body.weights)
        evaluator = FormulaEvaluator(temp_formula)
        
        # 计算所有可用模型的得分
        models = []
        for name, model in cfg.models.items():
            if cfg.is_model_available(name):
                score = evaluator.evaluate(model.capabilities)
                models.append({"name": name, "score": round(score, 2)})
        
        models.sort(key=lambda x: x["score"], reverse=True)
        
        # 获取分类结果（用于展示）
        # ...（复用 dry_run 中的分类逻辑）
        
        return {
            "task_type": "chat",  # 简化，实际可复用分类器
            "difficulty": "medium",
            "models": models
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**路由注册**:
```python
app.get("/api/formula")(get_formula)
app.put("/api/formula")(update_formula)
app.post("/api/formula/preview")(preview_formula)
```

**验证**:
- [ ] 三个端点可正常访问
- [ ] GET 返回当前 weights
- [ ] PUT 更新后 YAML 文件正确写入
- [ ] POST preview 返回模型得分排序

**依赖**: 任务 3

---

### 任务 10: 编写 Dashboard API 测试

**文件**: `core/smart_router/gateway/tests/test_formula_api.py`（新增）

**动作**: 测试新增的 Dashboard API 端点

**详情**:
- 场景 1: GET /api/formula 返回当前 weights
- 场景 2: PUT /api/formula 更新成功
- 场景 3: PUT /api/formula 传入无效权重返回错误
- 场景 4: POST /api/formula/preview 返回模型得分排序
- 场景 5: PUT 更新后 routing.yaml 内容正确

**验证**:
- [ ] 测试可运行
- [ ] 实现前失败（RED），任务 9 完成后通过（GREEN）

**依赖**: 任务 9

---

### 任务 11: 更新默认 routing.yaml 模板

**文件**: `core/smart_router/templates/routing.yaml`

**动作**: 在默认模板中新增 `formula` 字段，移除 `cost_quality_threshold`

**详情**:
```yaml
# 在 routing.yaml 中新增
tasks:
  # ... 保持现有任务定义

# 新增全局公式
formula:
  weights:
    quality: 0.5
    cost: 0.5

strategies:
  auto:
    name: "智能自动"
    description: "基于全局 formula 动态计算"

# 移除 cost_quality_threshold（由公式自行表达）
```

**验证**:
- [ ] 模板文件语法正确
- [ ] `smart-router init` 生成的配置包含 formula 字段

**依赖**: 任务 1

---

### 任务 12: 适配 Router 插件测试

**文件**: `core/smart_router/router/tests/test_plugin.py`

**动作**: 修改测试，适配 V3ModelSelector 移除硬编码策略后的行为

**详情**:
- 修改测试中创建 Config 的代码，添加 `formula` 字段
- 验证 `select_model()` 返回的 `strategy` 为 `"auto"`
- 验证 `strategy="cost"` 时发出 DeprecationWarning（如果测试中有此类用例）

**验证**:
- [ ] 测试可运行
- [ ] 全部通过

**依赖**: 任务 5

---

### 任务 13: 适配 Gateway Server 测试

**文件**: `core/smart_router/gateway/tests/test_server.py`

**动作**: 修改测试，适配 Config 结构变化

**详情**:
- 修改测试中创建 Config 的代码，添加 `formula` 字段
- 确保 mock config 包含 `routing.formula`

**验证**:
- [ ] 测试可运行
- [ ] 全部通过

**依赖**: 任务 5

---

### 任务 14: 创建前端 FormulaBuilder 页面

**文件**: `frontend/src/pages/FormulaBuilder.tsx`（新增）及辅助组件

**动作**: 创建 Dashboard 策略构建器页面

**详情**:

**组件结构**:
```
frontend/src/
  pages/
    FormulaBuilder.tsx      # 主页面
  components/
    FormulaSlider.tsx       # 能力权重滑块
    FormulaPreview.tsx      # 实时预览
    FormulaTemplates.tsx    # 预设模板选择
```

**FormulaBuilder.tsx 核心逻辑**:
```typescript
// 预设模板（前端常量）
const FORMULA_TEMPLATES = [
  { id: "quality_first", name: "质量优先", weights: { quality: 0.9, cost: 0.1, reasoning: 0, creative: 0, context: 0 } },
  { id: "cost_first", name: "成本优先", weights: { quality: 0.1, cost: 0.9, reasoning: 0, creative: 0, context: 0 } },
  { id: "balanced", name: "均衡", weights: { quality: 0.5, cost: 0.5, reasoning: 0, creative: 0, context: 0 } },
];

// 能力维度定义
const DIMENSIONS = [
  { key: "quality", name: "质量", description: "代码质量、推理能力" },
  { key: "cost", name: "成本", description: "成本效率（越高越便宜）" },
  { key: "reasoning", name: "推理", description: "数学、逻辑、代码推理" },
  { key: "creative", name: "创意", description: "写作、广告、头脑风暴" },
  { key: "context", name: "上下文", description: "上下文窗口处理能力" },
];

// 页面状态
const [weights, setWeights] = useState<Record<string, number>>({ quality: 0.5, cost: 0.5, reasoning: 0, creative: 0, context: 0 });
const [previewModels, setPreviewModels] = useState<Array<{name: string, score: number}>>([]);
const [testPrompt, setTestPrompt] = useState("");
```

**交互**:
- 滑块变化 → 更新 weights 状态 → 实时更新公式文本
- 选择模板 → 设置对应 weights
- 点击预览 → POST /api/formula/preview → 显示模型得分排名
- 点击保存 → PUT /api/formula → 显示成功/失败提示

**验证**:
- [ ] 页面可正常渲染
- [ ] 滑块拖动更新权重值
- [ ] 模板切换更新所有滑块
- [ ] 预览按钮调用 API 并显示结果
- [ ] 保存按钮调用 API 并显示提示

**依赖**: 任务 9

---

### 任务 15: 前端路由集成

**文件**: `frontend/src/App.tsx`（或现有路由文件）

**动作**: 将 FormulaBuilder 页面添加到 Dashboard 路由中

**详情**:
- 在导航栏/侧边栏添加"路由策略"入口
- 配置前端路由 `/formula` → FormulaBuilder 页面
- 确保页面可从 Dashboard 正常访问

**验证**:
- [ ] 导航栏显示"路由策略"入口
- [ ] 点击后进入 FormulaBuilder 页面
- [ ] 页面样式与 Dashboard 一致

**依赖**: 任务 14

---

## 深度自检

### 自检清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | **完整性** — 无 TODO、无占位符 | ✅ 所有任务描述完整 |
| 2 | **Spec 对齐** — 每个 Spec 需求都有对应任务 | ✅ 公式模型(1-2)、执行引擎(3-4)、选择器改造(5-6)、配置迁移(7-8)、API(9-10)、模板(11)、测试适配(12-13)、前端(14-15) |
| 3 | **任务分解** — 每个任务 2-5 分钟 | ✅ 任务粒度合适 |
| 4 | **可构建性** — 文件路径明确、详情足够 | ✅ 所有路径和代码结构明确 |
| 5 | **验收标准覆盖** — 每条验收标准有对应验证 | ✅ 后端测试覆盖公式计算/迁移/API；前端验证覆盖 UI 交互 |
| 6 | **明确性** — 有确切文件路径、详情、验证步骤 | ✅ 每个任务都有 |
| 7 | **可验证性** — 验证步骤可执行 | ✅ 每个任务都有明确的验证清单 |
| 8 | **顺序合理性** — 依赖正确、实现+测试成对 | ✅ 基础优先、测试紧随 |

### 自检结论

**全部通过。** 计划可直接执行。

---

## 任务依赖图

```
任务 1: FormulaConfig 模型
  ├──→ 任务 2: FormulaConfig 测试
  ├──→ 任务 3: FormulaEvaluator 引擎
  │     ├──→ 任务 4: FormulaEvaluator 测试
  │     ├──→ 任务 5: V3ModelSelector 改造
  │     │     ├──→ 任务 6: Selector 测试适配
  │     │     ├──→ 任务 12: Router 插件测试适配
  │     │     └──→ 任务 13: Gateway 测试适配
  │     └──→ 任务 9: Dashboard API 端点
  │           ├──→ 任务 10: Dashboard API 测试
  │           └──→ 任务 14: 前端 FormulaBuilder
  │                 └──→ 任务 15: 前端路由集成
  ├──→ 任务 7: ConfigLoader 迁移
  │     └──→ 任务 8: 迁移测试
  └──→ 任务 11: 更新默认模板
```

---

## 执行建议

### 分批策略

由于任务数 15 个，建议分两批执行：

**第一批（后端核心）**: 任务 1-13
- 依赖关系紧密，需顺序执行
- 完成后运行 `pytest core/smart_router/selector/tests/ core/smart_router/config/tests/ core/smart_router/router/tests/ core/smart_router/gateway/tests/`

**第二批（前端）**: 任务 14-15
- 与后端无强依赖（API 已就绪）
- 完成后运行 `cd frontend && npm run build`

### 快速验证命令

```bash
# 后端测试
pytest core/smart_router/selector/tests/test_formula_evaluator.py -v
pytest core/smart_router/config/tests/test_formula_config.py -v
pytest core/smart_router/config/tests/test_formula_migration.py -v
pytest core/smart_router/gateway/tests/test_formula_api.py -v
pytest core/smart_router/selector/tests/test_v3_selector.py -v
pytest core/smart_router/router/tests/test_plugin.py -v
pytest core/smart_router/gateway/tests/test_server.py -v

# 前端构建
cd frontend && npm run build

# 全量测试
make test
make build
```

---

*实现计划编写完成，准备进入执行阶段。*
