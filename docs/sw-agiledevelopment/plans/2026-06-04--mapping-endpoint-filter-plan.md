# 映射规则按端点过滤 - 实施计划

## 任务列表

### 任务 1: 修改 ModelMappingRule Schema

**文件**: `core/smart_router/config/mapping_schema.py`

**动作**: 新增 `endpoints` 字段和验证逻辑

**详情**:
- 在 `ModelMappingRule` 中添加 `endpoints: List[str] = Field(default_factory=lambda: ["chat", "responses"])`
- 在 `validate_fields` 中新增 endpoints 校验：非空、值必须在 {"chat", "responses"} 中

**验证**:
- [ ] Pydantic 能正确解析含/不含 endpoints 的配置
- [ ] 空列表触发 ValueError
- [ ] 非法值触发 ValueError

---

### 任务 2: 修改 _apply_model_mapping 传入端点类型

**文件**: `core/smart_router/gateway/server.py`

**动作**: 修改方法签名，增加 endpoint_type 参数，调用处传入端点类型

**详情**:
- 签名改为 `_apply_model_mapping(self, model_name: str, endpoint_type: str) -> Optional[str]`
- 循环内增加 `if endpoint_type in rule.endpoints:` 判断
- dispatch 中调用时传入 `endpoint_type = "chat" if is_chat_completions else "responses"`

**验证**:
- [ ] 单元测试：chat 端点只匹配含 chat 的规则
- [ ] 单元测试：responses 端点只匹配含 responses 的规则

---

### 任务 3: 修改前端类型定义

**文件**: `frontend/src/types/index.ts`

**动作**: ModelMappingRule 接口添加 endpoints 字段

**详情**:
```typescript
interface ModelMappingRule {
  // ... 现有字段
  endpoints: string[]
}
```

**验证**:
- [ ] TypeScript 编译通过

---

### 任务 4: 修改前端 ModelMappingTab 表单

**文件**: `frontend/src/components/ModelMappingTab.tsx`

**动作**: 在表单中添加端点多选复选框

**详情**:
- EMPTY_RULE 添加 `endpoints: ['chat', 'responses']`
- 在表单底部（Enabled 开关上方）添加两个复选框
- 使用 ToggleSwitch 或原生 checkbox
- 标签：Chat Completions / Responses

**验证**:
- [ ] 表单渲染正确
- [ ] 勾选/取消勾选能正确更新 form.endpoints

---

### 任务 5: 修改前端 ModelMappingTab 表格

**文件**: `frontend/src/components/ModelMappingTab.tsx`

**动作**: 表格新增 Endpoints 列

**详情**:
- 表头新增 "Endpoints" 列
- 每行显示端点标签（如 `chat, responses`）
- 放在 "To Provider" 和 "To Base URL" 之间

**验证**:
- [ ] 表格正确显示端点信息

---

### 任务 6: 添加前端翻译

**文件**: `frontend/src/i18n/I18nProvider.tsx`

**动作**: 添加端点相关翻译键

**详情**:
```
'Chat Completions': { zh: 'Chat Completions', en: 'Chat Completions' }
'Responses': { zh: 'Responses', en: 'Responses' }
'Endpoints': { zh: '适用端点', en: 'Endpoints' }
```

**验证**:
- [ ] 翻译键在 UI 中正确显示

---

### 任务 7: 编写后端端点过滤测试

**文件**: `core/smart_router/gateway/tests/test_mapping_api.py`

**动作**: 新增测试覆盖端点过滤逻辑

**详情**:
- `test_chat_endpoint_only_matches_chat_rules`: chat 端点不匹配仅 responses 的规则
- `test_responses_endpoint_only_matches_responses_rules`: responses 端点不匹配仅 chat 的规则
- `test_both_endpoints_matches_both_rules`: 两个端点都匹配含两个端点的规则
- `test_default_endpoints_backward_compatible`: 无 endpoints 字段时默认匹配两个端点

**验证**:
- [ ] 测试先失败（RED）→ 任务 1-2 完成后通过（GREEN）

---

### 任务 8: 运行全量测试

**动作**: 运行后端和前端测试

**验证**:
- [ ] test_mapping_api.py 全部通过
- [ ] test_server.py 全部通过
