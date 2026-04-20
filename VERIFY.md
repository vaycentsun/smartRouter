# Smart Router 验证测试指南

## 一、基础验证（无需 API Key）

### 1. 检查服务状态
```bash
smr status
```
预期输出：
```
✓ Smart Router 运行中
  PID: 75730
  端口: 4000
```

### 2. 健康检查
```bash
smr doctor
```
预期输出：
```
✓ Python 版本: 3.9.6
✓ 配置加载成功 (X 个模型)
✓ 配置验证通过
✓ 服务运行中 (PID: XXXXX)
```

### 3. 查看可用模型
```bash
smr list
```
显示所有配置的 Provider 和模型，以及 API Key 配置状态。

### 4. 查看日志
```bash
# 最近 50 行
smr logs

# 实时跟踪
smr logs -f
```

---

## 二、API 接口验证

### 1. 测试模型列表接口
```bash
curl http://127.0.0.1:4000/v1/models \
  -H "Authorization: Bearer sk-smart-router-local"
```
预期：返回 JSON 格式的模型列表

### 2. 测试对话接口（需要配置 API Key）
```bash
curl http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-smart-router-local" \
  -d '{
    "model": "glm-4-plus",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 50
  }'
```

### 3. 使用 Python SDK 测试
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:4000",
    api_key="sk-smart-router-local"
)

# 测试模型列表
models = client.models.list()
print(f"可用模型: {len(models.data)} 个")

# 测试对话
response = client.chat.completions.create(
    model="glm-4-plus",
    messages=[{"role": "user", "content": "你好"}],
    max_tokens=50
)
print(response.choices[0].message.content)
```

---

## 三、路由功能验证

### 1. 使用阶段标记
```bash
curl http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-smart-router-local" \
  -d '{
    "model": "gpt-4o",
    "messages": [
      {"role": "user", "content": "[stage:code_review]\n请审查这段代码"}
    ]
  }'
```

可用的阶段标记：
- `[stage:brainstorming]` - 头脑风暴
- `[stage:code_review]` - 代码审查
- `[stage:writing]` - 内容写作
- `[stage:reasoning]` - 逻辑推理
- `[stage:chat]` - 日常对话

### 2. 使用难度标记
```bash
# 显式指定难度
[difficulty:easy] 简单问题
[difficulty:medium] 中等难度
[difficulty:hard] 困难任务
[difficulty:expert] 专家级
```

---

## 四、故障排查

### 问题 1: API Key 错误
```
AuthenticationError: The api_key client option must be set
```
**解决**: 
1. 检查 `~/.smart-router/providers.yaml` 中的 API Key 配置
2. 确保环境变量已设置：`export DASHSCOPE_API_KEY="sk-xxx"`
3. 重启服务：`smr restart`

### 问题 2: 服务未启动
```
Connection refused
```
**解决**:
```bash
smr start
# 或前台启动查看错误
smr start -f
```

### 问题 3: 配置错误
```bash
# 验证配置
smr doctor

# 查看详细错误
smr logs -f
```

---

## 五、性能测试

### 1. 并发测试
```bash
# 安装依赖
pip install locust

# 创建测试文件 locustfile.py
```

### 2. 延迟测试
```bash
# 使用 curl 的 -w 参数
curl -w "@curl-format.txt" http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-smart-router-local" \
  -d '{...}'
```

---

## 六、验证清单

| 检查项 | 命令 | 预期结果 |
|-------|------|---------|
| 服务运行 | `smr status` | ✓ 运行中 |
| 配置正确 | `smr doctor` | ✓ 所有检查通过 |
| 模型列表 | `smr list` | 显示所有模型 |
| API 可用 | `curl /v1/models` | 返回 JSON |
| 对话正常 | `curl /v1/chat/completions` | 返回回复 |
| 路由生效 | 带 stage 标记请求 | 路由到正确模型 |
