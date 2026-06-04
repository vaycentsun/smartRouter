# 映射规则按端点过滤 - 技术规范

## 概述
在 `ModelMappingRule` 中新增 `endpoints` 字段（`List[str]`），允许每条规则独立配置适用于哪些 API 端点。中间件根据请求端点类型过滤匹配规则，前端 Dashboard 提供端点多选配置和展示。

## 组件设计

### 组件 1: ModelMappingRule（Schema 扩展）

**文件**: `core/smart_router/config/mapping_schema.py`

**变更**:
```python
class ModelMappingRule(BaseModel):
    # ... 现有字段 ...
    endpoints: List[str] = Field(
        default_factory=lambda: ["chat", "responses"],
        description="适用端点列表，可选值: chat, responses"
    )
    
    @model_validator(mode="after")
    def validate_fields(self):
        # ... 现有校验 ...
        # 新增：校验 endpoints 非空且值合法
        if not self.endpoints:
            raise ValueError("endpoints cannot be empty")
        valid_endpoints = {"chat", "responses"}
        invalid = set(self.endpoints) - valid_endpoints
        if invalid:
            raise ValueError(f"Invalid endpoints: {invalid}. Allowed: {valid_endpoints}")
        return self
```

**向后兼容**: 无 `endpoints` 字段的旧配置，Pydantic 会自动使用默认值 `["chat", "responses"]`。

### 组件 2: SmartRouterMiddleware._apply_model_mapping

**文件**: `core/smart_router/gateway/server.py`

**变更**:
```python
def _apply_model_mapping(self, model_name: str, endpoint_type: str) -> Optional[str]:
    """检查模型映射表，返回映射后的模型名，无匹配返回 None
    
    Args:
        model_name: 请求体中的模型名
        endpoint_type: 端点类型，"chat" 或 "responses"
    """
    mappings = getattr(self.router, 'model_mappings', None)
    if not mappings or not mappings.enabled:
        return None
    for rule in mappings.mappings:
        if rule.enabled and rule.from_model == model_name:
            # 检查规则是否适用于当前端点
            if endpoint_type in rule.endpoints:
                return rule.to_model
    return None
```

**调用点**（dispatch 方法中）:
```python
# 根据路径确定端点类型
endpoint_type = "chat" if is_chat_completions else "responses"

mapped_model = self._apply_model_mapping(original_model, endpoint_type)
```

### 组件 3: Dashboard API

**变更**: 无。API 已返回完整的 `ModelMappingRule` 字段，包括新增的 `endpoints`。`GET /api/model-mappings` 和 `PUT /api/model-mappings` 自动支持新字段。

### 组件 4: 前端 ModelMappingTab

**文件**: `frontend/src/components/ModelMappingTab.tsx`

**变更**:
1. **EMPTY_RULE 默认值**: `endpoints: ['chat', 'responses']`
2. **表单**: 在 "Enabled" 开关上方添加两个复选框：
   - ☑ Chat Completions (`/v1/chat/completions`)
   - ☑ Responses (`/v1/responses`)
3. **表格**: 新增 "Endpoints" 列，显示端点标签（如 `chat + responses`）
4. **类型定义**: `ModelMappingRule` 接口添加 `endpoints: string[]`

### 组件 5: 前端类型定义

**文件**: `frontend/src/types/index.ts`

**变更**:
```typescript
interface ModelMappingRule {
  // ... 现有字段 ...
  endpoints: string[]
}
```

## 数据流

```
1. 用户在前端勾选端点 → 保存规则
2. PUT /api/model-mappings → 后端验证 endpoints 字段
3. 保存到 model_mappings.yaml
4. ConfigWatcher 检测到变更 → 热重载
5. SmartRouter.reload_config() → 重新加载映射配置
6. 新请求到达 → dispatch 确定 endpoint_type → _apply_model_mapping 过滤
```

## 错误处理

| 错误场景 | 处理策略 |
|---------|---------|
| endpoints 为空列表 | Pydantic 验证失败，保存时返回 400 |
| endpoints 包含非法值 | Pydantic 验证失败，保存时返回 400 |
| 旧配置无 endpoints 字段 | Pydantic 自动使用默认值 `["chat", "responses"]` |

## 验收标准

- [ ] 规则配置 `endpoints: ["chat"]` 时，只在 `/v1/chat/completions` 上生效
- [ ] 规则配置 `endpoints: ["responses"]` 时，只在 `/v1/responses` 上生效
- [ ] 规则配置 `endpoints: ["chat", "responses"]` 时，两个端点都生效
- [ ] 规则无 `endpoints` 字段时，默认两个端点都生效
- [ ] 前端表单可以勾选/取消勾选端点
- [ ] 前端表格显示每条规则的适用端点
- [ ] 空 endpoints 列表验证失败返回 400
