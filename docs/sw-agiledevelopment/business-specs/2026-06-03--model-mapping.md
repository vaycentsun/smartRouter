# 模型映射表（Model Mapping）- 业务需求

## 概述
为 Smart Router 增加模型映射表功能，允许管理员通过 YAML 配置文件定义请求模型到目标模型/服务商的精确映射规则，实现请求的透明转发与代理。

## 背景与动机
当前 Smart Router 的智能路由和全局模型覆盖（Model Override）功能无法灵活应对以下场景：
- 需要将特定模型名称的请求转发到完全不同的服务商（如将 `gpt-4` 转发到国产厂商的兼容接口）
- 需要在不修改客户端代码的情况下，临时切换某个模型背后的实际服务提供商
- 需要为不同模型配置独立的 API Key 和 Base URL，而不受 providers.yaml 的限制

模型映射表提供了一个轻量级的条件转发层，优先级高于智能路由和全局覆盖。

## 用户与角色
- **主要用户**: Smart Router 管理员/运维人员
- **使用场景**:
  1. 运维人员通过 Dashboard 的模型映射 Tab 查看和编辑映射规则
  2. 管理员通过 CLI `init` 生成默认映射配置文件，随后手动编辑
  3. 运行时映射规则变更自动生效（通过配置热重载或 Dashboard API）

## 关键约束
- **技术约束**: 基于现有 V3 三文件配置架构扩展，不破坏现有 providers.yaml / models.yaml / routing.yaml 的验证逻辑
- **安全约束**: API Key 在 YAML 中支持 `os.environ/KEY_NAME` 引用格式，禁止明文强约束可适当放宽（因映射规则本身可能需要独立密钥）
- **兼容性约束**: 映射目标模型不需要在 models.yaml 中预先定义，完全独立
- **前端约束**: 遵循现有 Dashboard 的 Tab 布局风格和组件设计模式

## 目标
- [ ] 新增独立的 `model_mappings.yaml` 配置文件，包含全局开关和映射规则列表
- [ ] 支持全局开关控制映射功能总启停，以及每条规则的独立启停开关
- [ ] 仅根据请求中的 `model` 字段进行精确匹配（不支持通配符）
- [ ] 匹配成功后，将请求转发到规则指定的目标 provider、model、baseurl、apikey
- [ ] 映射功能优先级最高：请求先经过映射表，再经过 Model Override，最后才走智能路由
- [ ] `smart-router init` 和安装流程自动将默认 `model_mappings.yaml` 复制到 `~/.smart-router/`
- [ ] Dashboard 前端新增"模型映射" Tab，支持表格形式展示和 YAML 编辑器直接修改
- [ ] 配置变更后无需重启服务即可生效

## 非目标
- 不支持基于请求内容（如 prompt 文本）的映射匹配
- 不支持通配符、正则表达式或模糊匹配
- 不支持按请求头（如 X-Provider）进行匹配
- 不替换现有的 Model Override 功能，两者共存
- 不在映射层实现 fallback 重试（fallback 仍由智能路由层负责）
- 不需要支持映射规则的导入/导出或批量操作

## 方案决策

**选定方案**: 方案一 — 独立配置文件 + 中间件层拦截 + 动态 LiteLLM 虚拟模型注册

**原因**:
1. **完全独立的目标配置**: 映射目标不需要在现有 models.yaml / providers.yaml 中定义，最符合用户需求
2. **架构一致**: 复用现有的 ConfigLoader、配置热重载（ConfigWatcher）和中间件（SmartRouterMiddleware）机制
3. **优先级可控**: 在 middleware `dispatch` 的最前端插入映射逻辑，天然实现"优先级最高"
4. **技术可行**: 通过为每个映射目标生成独立的 LiteLLM 虚拟模型条目，利用 LiteLLM 自身的请求转发能力，避免自行处理 HTTP 代理的复杂性

**替代方案**:
- **方案二（请求直接代理转发）**: 在 middleware 中匹配后直接构造 HTTP 请求转发。放弃原因：需要自行处理流式响应、错误码转换、认证头、SSE 解析等，工作量大且易出错，同时会失去 LiteLLM 的日志、重试、批处理等能力。
- **方案三（集成到现有配置）**: 将映射规则放入 routing.yaml 或新增 providers 类型。放弃原因：会破坏现有三文件解耦架构，且目标模型不在 models.yaml 中时会导致 Config 验证失败，需要大规模修改 schema。

## 关键组件（草案）

### 1. ModelMappingConfig（Pydantic 模型）
定义 `model_mappings.yaml` 的 Schema：
```yaml
enabled: true  # 全局开关
mappings:
  - id: "map-gpt4-to-qwen"      # 规则唯一标识
    enabled: true               # 规则开关
    from_model: "gpt-4"         # 匹配的请求模型名（精确匹配）
    to_provider: "aliyun-proxy" # 目标 provider 名称（仅用于标识）
    to_model: "qwen-max"        # 目标模型名
    to_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    to_api_key: "os.environ/ALIYUN_API_KEY"
```

### 2. ModelMappingLoader / ConfigLoader 扩展
- `ConfigLoader` 新增 `load_model_mappings()` 方法
- 新增 `save_model_mappings()` 支持保存（带备份和回滚）
- 验证规则 ID 唯一性、`from_model` 不重复（或定义重复时的优先级策略）

### 3. SmartRouterMiddleware 扩展
- 在 `dispatch` 方法最前端，请求体解析后，优先检查映射表
- 匹配逻辑：
  1. 全局开关关闭 → 跳过
  2. 按 `from_model` 精确匹配请求体中的 `model` 字段
  3. 取第一条匹配且 `enabled=true` 的规则
  4. 将请求体中的 `model` 替换为 `to_model`
  5. 在 `request.state` 中标记 `smart_router_mapped = True`，记录原始模型和映射规则

### 4. SmartRouter / LiteLLM 模型列表扩展
- `SmartRouter.__init__` 和 `reload_config` 时，读取映射规则
- 为每个 `enabled` 的映射规则的目标模型，生成一个 LiteLLM `model_list` 条目：
  ```python
  {
      "model_name": "mapped-<from_model>",  # 或直接 to_model？
      "litellm_params": {
          "model": f"{to_provider}/{to_model}",
          "api_base": to_base_url,
          "api_key": resolved_api_key,
      }
  }
  ```
- 更优方案：映射替换请求 model 为 `to_model`，同时确保 `to_model` 在 LiteLLM 的 model_list 中有对应的完整 litellm_params。由于目标模型不在现有 models.yaml 中，需要动态生成这些条目。

### 5. Dashboard API（FastAPI）
- `GET /api/model-mappings` — 获取当前映射配置（结构化 JSON）
- `PUT /api/model-mappings` — 保存映射配置（JSON → YAML → 验证 → 热重载）
- `GET /api/model-mappings/yaml` — 获取原始 YAML 文本（供编辑器使用）
- `PUT /api/model-mappings/yaml` — 保存原始 YAML 文本（供编辑器使用）

### 6. Dashboard 前端 — ModelMappingTab
- 新增 Tab 页"模型映射"
- 两种视图模式切换：
  - **表格视图**: 展示规则列表（from_model → to_model, to_provider, enabled, 开关按钮）
  - **YAML 编辑器**: 基于 CodeMirror / Monaco 或纯 textarea 的 YAML 编辑器，带语法高亮和验证
- 顶部显示全局开关 Toggle
- 保存按钮触发 API 保存，成功后提示

## 验收标准（初稿）
- [ ] 运行 `smart-router init` 后，`~/.smart-router/model_mappings.yaml` 存在且包含默认注释模板
- [ ] 全局开关关闭时，无论映射规则如何配置，请求均不触发映射，正常走原有路由逻辑
- [ ] 全局开关开启时，请求 model 精确匹配 `from_model` 且规则 enabled 时，请求被转发到目标配置
- [ ] 请求的原始 model 名称通过响应头 `X-Smart-Router-Original` 返回，映射后的 model 通过 `X-Smart-Router-Model` 返回
- [ ] Dashboard 中新增"模型映射" Tab，能正确展示当前规则列表
- [ ] Dashboard 中能通过 YAML 编辑器修改并保存映射配置，保存后新配置在 1 秒内生效（通过热重载）
- [ ] 映射规则的 API Key 支持 `os.environ/KEY_NAME` 格式
- [ ] 当多条规则具有相同的 `from_model` 时，按 YAML 中定义的顺序取第一条匹配

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LiteLLM 不支持运行时动态添加 model_list 条目 | 高 | 映射目标模型作为"虚拟模型"在启动时即注册到 LiteLLM Router；运行时映射规则变更通过修改 `SmartRouterMiddleware` 的内存状态实现，不依赖 LiteLLM 运行时注册 |
| 目标 base_url/api_key 配置错误导致请求失败 | 中 | 保存 YAML 时进行基础格式验证；Dashboard 提供"测试连通性"按钮（未来迭代） |
| 映射规则与现有模型名冲突 | 中 | 验证阶段检查 `from_model` 是否和现有 models.yaml 中的模型名冲突，如有冲突则发出警告但不阻止（因为映射优先级高，冲突是预期行为） |
| 前端 YAML 编辑器体验差 | 低 | 使用现有纯文本编辑器方案（如 textarea + yaml 高亮），不引入 Monaco 等重型依赖 |
| 配置热重载时映射规则未同步更新 | 高 | 扩展 `ConfigWatcher` 监听 `model_mappings.yaml`；扩展 `SmartRouter.reload_config` 同步重新加载映射配置并更新中间件状态 |
