# 添加自定义 Provider 与 Model - 实现计划

## 计划概览

| 编号 | 任务 | 文件 | 依赖 |
|------|------|------|------|
| 1 | 实现 ConfigLoader.create_provider | `core/smart_router/config/loader.py` | - |
| 2 | 测试 ConfigLoader.create_provider | `core/smart_router/config/tests/test_loader.py` | 1 |
| 3 | 实现 ConfigLoader.add_model | `core/smart_router/config/loader.py` | 1 |
| 4 | 测试 ConfigLoader.add_model | `core/smart_router/config/tests/test_loader.py` | 3 |
| 5 | 实现 POST /api/providers | `core/smart_router/gateway/dashboard_api.py` | 1 |
| 6 | 测试 POST /api/providers | `core/smart_router/gateway/tests/test_dashboard_api.py` | 5 |
| 7 | 实现 POST /api/providers/{name}/models | `core/smart_router/gateway/dashboard_api.py` | 3 |
| 8 | 测试 POST /api/providers/{name}/models | `core/smart_router/gateway/tests/test_dashboard_api.py` | 7 |
| 9 | 新增 TypeScript 类型 | `frontend/src/types/index.ts` | - |
| 10 | 新增 api/client 方法 | `frontend/src/api/client.ts` | 9 |
| 11 | 新增 store action | `frontend/src/store/useDashboardStore.ts` | 10 |
| 12 | 创建 AddProviderModal 组件 | `frontend/src/components/AddProviderModal.tsx` | 9 |
| 13 | 测试 AddProviderModal | `frontend/src/components/AddProviderModal.test.tsx` | 12 |
| 14 | 创建 AddModelModal 组件 | `frontend/src/components/AddModelModal.tsx` | 9 |
| 15 | 测试 AddModelModal | `frontend/src/components/AddModelModal.test.tsx` | 14 |
| 16 | 修改 ProviderSidebar | `frontend/src/components/ProviderSidebar.tsx` | - |
| 17 | 修改 ProviderModelsPanel | `frontend/src/components/ProviderModelsPanel.tsx` | - |
| 18 | 集成 ModelsExplorer | `frontend/src/components/ModelsExplorer.tsx` | 11, 12, 14, 16, 17 |

**任务总数**: 18  
**预计总时间**: ~180 分钟

---

### 任务 1: 实现 ConfigLoader.create_provider

**文件**: `core/smart_router/config/loader.py`

**动作**: 在 `ConfigLoader` 类中新增 `create_provider` 方法

**详情**:
- 方法签名: `def create_provider(self, name, api_base, api_key, timeout=30)`
- 读取 providers.yaml，检查 name 是否已存在，若存在抛 ConfigError
- 用正则校验 name 格式: 只允许字母数字下划线和连字符
- 构造 provider 节点并调用 `self.save_providers(providers)`（复用现有的备份+验证+回滚）

**验证**:
- [ ] 方法可调用
- [ ] 成功创建后 providers.yaml 包含新节点
- [ ] 名称冲突时抛出 ConfigError
- [ ] 名称含非法字符时抛出 ConfigError

**依赖**: 无

---

### 任务 2: 测试 ConfigLoader.create_provider

**文件**: `core/smart_router/config/tests/test_loader.py`

**动作**: 为 create_provider 编写单元测试

**详情**:
- 场景1: 正常创建 provider，验证 providers.yaml 内容和 loader.load() 可读取
- 场景2: name 已存在，验证抛出 ConfigError，原配置不变
- 场景3: name 含空格，验证抛出 ConfigError
- 场景4: 创建后若 validate 失败，验证备份回滚生效

**验证**:
- [ ] pytest 可运行
- [ ] 所有场景通过

**依赖**: 任务 1

---

### 任务 3: 实现 ConfigLoader.add_model

**文件**: `core/smart_router/config/loader.py`

**动作**: 在 `ConfigLoader` 类中新增 `add_model` 方法

**详情**:
- 方法签名: `def add_model(self, provider_name, name, litellm_model, quality, cost, context, supported_tasks, enabled=True)`
- 校验 name 格式（正则）
- 调用 self.load() 校验 model name 全局唯一性 和 provider 存在性
- 读取或创建 models/{provider_name}.yaml
- 追加 model 节点，备份+写入+validate+回滚（与 save_providers 模式一致）

**验证**:
- [ ] 方法可调用
- [ ] 成功添加后 YAML 包含新节点
- [ ] 文件不存在时自动创建
- [ ] model name 全局冲突时抛出 ConfigError
- [ ] provider 不存在时抛出 ConfigError
- [ ] 验证失败时备份回滚生效

**依赖**: 任务 1

---

### 任务 4: 测试 ConfigLoader.add_model

**文件**: `core/smart_router/config/tests/test_loader.py`

**动作**: 为 add_model 编写单元测试

**详情**:
- 场景1: 正常添加到已有文件
- 场景2: 添加到不存在的文件（自动创建）
- 场景3: model name 全局已存在，验证抛出 ConfigError
- 场景4: provider 不存在，验证抛出 ConfigError
- 场景5: name 含非法字符，验证抛出 ConfigError
- 场景6: 写入后 validate 失败，验证备份回滚

**验证**:
- [ ] pytest 可运行
- [ ] 所有场景通过

**依赖**: 任务 3

---

### 任务 5: 实现 POST /api/providers

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 新增 CreateProviderRequest Pydantic 模型和 create_provider handler

**详情**:
- 新增 `class CreateProviderRequest(BaseModel)` 含 name, api_base, api_key, timeout 字段
- 新增 async handler `create_provider(request: CreateProviderRequest)`
- handler 中调用 `ConfigLoader.create_provider`
- 捕获 ConfigError 返回 400，其他异常返回 500
- 构造 ProviderInfo 格式的 success 响应
- 在 build_dashboard_app 中注册 `app.post("/api/providers")(create_provider)`

**验证**:
- [ ] FastAPI 启动无报错
- [ ] POST 返回正确结构

**依赖**: 任务 1

---

### 任务 6: 测试 POST /api/providers

**文件**: `core/smart_router/gateway/tests/test_dashboard_api.py`

**动作**: 为 POST /api/providers 编写 API 测试

**详情**:
- 场景1: 正常创建，返回 200 和 provider 信息
- 场景2: name 已存在，返回 400
- 场景3: name 含空格，返回 400
- 场景4: 缺少必填字段，返回 422
- 场景5: validate 失败，返回 500

**验证**:
- [ ] pytest 可运行
- [ ] 所有场景通过

**依赖**: 任务 5

---

### 任务 7: 实现 POST /api/providers/{name}/models

**文件**: `core/smart_router/gateway/dashboard_api.py`

**动作**: 新增 AddModelRequest Pydantic 模型和 add_model handler

**详情**:
- 新增 `class AddModelRequest(BaseModel)` 含 name, litellm_model, quality, cost, context, supported_tasks, enabled 字段
- 新增 async handler `add_model(provider_name, request: AddModelRequest)`
- 调用 `ConfigLoader.add_model`
- 捕获 ConfigError: 含 not found 返回 404，其他返回 400
- 构造 ModelInfo 格式的 success 响应
- 在 build_dashboard_app 中注册 `app.post("/api/providers/{provider_name}/models")(add_model)`

**验证**:
- [ ] FastAPI 启动无报错
- [ ] POST 返回正确结构

**依赖**: 任务 3

---

### 任务 8: 测试 POST /api/providers/{name}/models

**文件**: `core/smart_router/gateway/tests/test_dashboard_api.py`

**动作**: 为 POST /api/providers/{name}/models 编写 API 测试

**详情**:
- 场景1: 正常添加，返回 200
- 场景2: provider 不存在，返回 404
- 场景3: model name 已存在，返回 400
- 场景4: name 含空格，返回 400
- 场景5: 缺少必填字段，返回 422
- 场景6: validate 失败，返回 500

**验证**:
- [ ] pytest 可运行
- [ ] 所有场景通过

**依赖**: 任务 7

---

### 任务 9: 新增 TypeScript 类型

**文件**: `frontend/src/types/index.ts`

**动作**: 在文件末尾追加 CreateProviderRequest 和 AddModelRequest 接口

**详情**:
```typescript
export interface CreateProviderRequest {
  name: string
  api_base: string
  api_key: string
  timeout: number
}

export interface AddModelRequest {
  name: string
  litellm_model: string
  quality: number
  cost: number
  context: number
  supported_tasks: string[]
  enabled?: boolean
}
```

**验证**:
- [ ] TypeScript 编译无报错

**依赖**: 无

---

### 任务 10: 新增 api/client 方法

**文件**: `frontend/src/api/client.ts`

**动作**: 在 api 对象中新增 createProvider 和 addModel 方法

**详情**:
- createProvider: POST /api/providers，返回 { success, provider, error? }
- addModel: POST /api/providers/{providerName}/models，返回 { success, model, error? }

**验证**:
- [ ] TypeScript 编译无报错

**依赖**: 任务 9

---

### 任务 11: 新增 store action

**文件**: `frontend/src/store/useDashboardStore.ts`

**动作**: 在 DashboardState 接口和 store 实现中新增 createProvider 和 addModel

**详情**:
- createProvider: 调用 api.createProvider，设置 isSavingProviders 和 toast，成功后 fetchAll()
- addModel: 调用 api.addModel，设置 isLoading 和 toast，成功后 fetchAll()
- 错误处理与现有 saveProviders 一致

**验证**:
- [ ] TypeScript 编译无报错

**依赖**: 任务 10

---

### 任务 12: 创建 AddProviderModal 组件

**文件**: `frontend/src/components/AddProviderModal.tsx`

**动作**: 创建新组件，包含 Provider 基本信息表单

**详情**:
- Props: isOpen, onClose, onSubmit, isSaving
- 字段: name, api_base, api_key(password可切换), timeout
- 样式: tech-card, tech-input, tech-btn-primary
- 前端校验: name 非空, api_base 非空, timeout 为 1-300
- 提交失败显示红色错误提示

**验证**:
- [ ] 组件可 import
- [ ] TypeScript 编译无报错
- [ ] 渲染后表单字段齐全

**依赖**: 任务 9

---

### 任务 13: 测试 AddProviderModal

**文件**: `frontend/src/components/AddProviderModal.test.tsx`

**动作**: 为 AddProviderModal 编写单元测试

**详情**:
- 场景1: 渲染 Modal，检查字段存在
- 场景2: 填写有效数据点击 Save，验证 onSubmit 被调用
- 场景3: name 为空点击 Save，验证 onSubmit 未被调用
- 场景4: timeout 为 0，验证 onSubmit 未被调用
- 场景5: 点击 Cancel，验证 onClose 被调用

**验证**:
- [ ] vitest 可运行
- [ ] 所有场景通过

**依赖**: 任务 12

---

### 任务 14: 创建 AddModelModal 组件

**文件**: `frontend/src/components/AddModelModal.tsx`

**动作**: 创建新组件，包含 Model 能力参数表单

**详情**:
- Props: providerName, isOpen, onClose, onSubmit, isSaving
- 字段: name, litellm_model, quality(1-10), cost(1-10), context, supported_tasks(逗号分隔), enabled
- 样式: tech-card, tech-input, tech-btn-primary
- 前端校验: name 非空, litellm_model 非空, quality/cost 为 1-10, context 为正整数, supported_tasks 至少一项
- 提交时逗号分隔字符串解析为 string[]

**验证**:
- [ ] 组件可 import
- [ ] TypeScript 编译无报错
- [ ] 渲染后表单字段齐全

**依赖**: 任务 9

---

### 任务 15: 测试 AddModelModal

**文件**: `frontend/src/components/AddModelModal.test.tsx`

**动作**: 为 AddModelModal 编写单元测试

**详情**:
- 场景1: 渲染 Modal，检查字段
- 场景2: 填写有效数据点击 Save，验证 onSubmit 被调用且 supported_tasks 解析正确
- 场景3: name 为空，验证 onSubmit 未被调用
- 场景4: quality = 11，验证 onSubmit 未被调用
- 场景5: supported_tasks 为空，验证 onSubmit 未被调用
- 场景6: 点击 Cancel，验证 onClose 被调用

**验证**:
- [ ] vitest 可运行
- [ ] 所有场景通过

**依赖**: 任务 14

---

### 任务 16: 修改 ProviderSidebar

**文件**: `frontend/src/components/ProviderSidebar.tsx`

**动作**: 在 provider 列表上方添加 "+ Add Provider" 按钮

**详情**:
- 新增可选 prop onAddProvider
- 在 provider 列表 map 之前插入按钮: w-full tech-btn tech-btn-primary px-3 py-2 rounded-sm text-xs font-mono mb-2
- 无 provider 时也保留该按钮

**验证**:
- [ ] TypeScript 编译无报错
- [ ] 渲染后按钮可见
- [ ] 点击触发 onAddProvider

**依赖**: 无

---

### 任务 17: 修改 ProviderModelsPanel

**文件**: `frontend/src/components/ProviderModelsPanel.tsx`

**动作**: 在头部编辑按钮旁添加 "+ Add Model" 按钮

**详情**:
- 新增可选 prop onAddModel
- 在头部 flex 区域(EDIT 按钮旁)插入按钮: tech-btn tech-btn-primary px-3 py-2 rounded-sm text-xs
- 仅在 provider 非 null 时显示

**验证**:
- [ ] TypeScript 编译无报错
- [ ] 渲染后按钮可见
- [ ] 点击触发 onAddModel

**依赖**: 无

---

### 任务 18: 集成 ModelsExplorer

**文件**: `frontend/src/components/ModelsExplorer.tsx`

**动作**: 集成 Modal 组件和按钮回调

**详情**:
- 新增 state: addProviderOpen, addModelOpen
- 导入并渲染 AddProviderModal 和 AddModelModal
- 将 onAddProvider 传给 ProviderSidebar，onAddModel 传给 ProviderModelsPanel
- 从 useDashboardStore 解构 createProvider 和 addModel
- Modal onSubmit 调用 store action 并关闭 Modal

**验证**:
- [ ] TypeScript 编译无报错
- [ ] 页面渲染无报错
- [ ] 点击按钮打开对应 Modal
- [ ] 提交后 Modal 关闭且列表刷新

**依赖**: 任务 11, 12, 14, 16, 17

---

## 深度自检清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | 完整性 | 无 TODO、无占位符、无空描述 |
| 2 | 规范对齐 | 所有 technical-spec 组件和接口都有对应任务 |
| 3 | 任务分解 | 每个任务边界清晰，可在 10 分钟内完成 |
| 4 | 可构建性 | 文件路径明确，详情足够判断如何实现 |
| 5 | 验收标准覆盖 | 11 条验收标准均有对应验证任务 |
| 6 | 明确性 | 每个任务有确切文件路径、足够详情、清晰验证步骤 |
| 7 | 可验证性 | 每个任务的验证步骤可执行、可判断通过/失败 |
| 8 | 顺序合理性 | 依赖正确，实现+测试成对相邻，基础组件优先 |

**自检结论**: 通过
