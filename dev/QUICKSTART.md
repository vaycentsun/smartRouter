# Smart Router 快速上手指南

## 🚀 5 分钟快速启动

### 1. 安装

```bash
cd dev/cli-tools/smart-router
pip install -e ".[dev]"
```

### 2. 初始化配置

```bash
# 生成配置文件
smart-router init

# 编辑配置，填入你的 API Key
vim smart-router.yaml
```

### 3. 启动服务（后台运行）

```bash
# 启动（后台运行）
smart-router start

# 查看状态
smart-router status

# 输出示例：
# ● Smart Router 运行中
#   PID: 12345
#   服务: http://127.0.0.1:4000
#   日志: ~/.smart-router/smart-router.log
```

### 4. 测试路由（不调用模型）

```bash
# 测试自动路由
smart-router dry-run "帮我审查这段 Python 代码"

# 使用阶段标记
smart-router dry-run "[stage:writing] 写一封商务邮件" --strategy quality
```

### 5. 客户端使用

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-smart-router-local"
)

# 自动路由
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "帮我审查这段代码"}]
)

# 使用阶段标记
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "[stage:code_review] 审查这段代码"}]
)
```

---

## 📋 常用命令速查

### 服务管理

| 命令 | 说明 |
|------|------|
| `smart-router start` | 后台启动服务 |
| `smart-router start --foreground` | 前台启动（调试用） |
| `smart-router stop` | 停止服务 |
| `smart-router restart` | 重启服务 |
| `smart-router status` | 查看运行状态 |

### 日志查看

| 命令 | 说明 |
|------|------|
| `smart-router logs` | 查看最后 50 行日志 |
| `smart-router logs -n 100` | 查看最后 100 行 |
| `smart-router logs -f` | 持续跟踪日志（Ctrl+C 退出） |

### 配置和测试

| 命令 | 说明 |
|------|------|
| `smart-router init` | 生成默认配置 |
| `smart-router validate` | 验证配置 |
| `smart-router dry-run "提示文本"` | 测试路由决策 |

---

## 🎯 阶段标记使用

在 prompt 中添加标记显式控制路由：

```python
# 代码审查
"[stage:code_review] 审查这段代码"

# 写作任务（简单）
"[stage:writing] [difficulty:easy] 写一封邮件"

# 复杂推理
"[stage:reasoning] [difficulty:hard] 证明这个定理"
```

### 支持的 Stage

| 标记 | 用途 | 默认模型 |
|------|------|----------|
| `brainstorming` | 头脑风暴 | qwen-turbo, gpt-4o-mini |
| `code_review` | 代码审查 | claude-3-sonnet |
| `writing` | 写作 | qwen-turbo, kimi-k2 |
| `reasoning` | 逻辑推理 | claude-3-opus |
| `chat` | 普通对话 | qwen-turbo, gpt-4o-mini |

---

## 🔧 故障排查

### 服务无法启动

```bash
# 检查端口占用
lsof -i :4000

# 查看日志
smart-router logs

# 验证配置
smart-router validate
```

### 检查环境变量

```bash
# 检查 API Key
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# 设置环境变量
export OPENAI_API_KEY="sk-..."
```

### 测试连通性

```bash
# 测试服务是否运行
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-smart-router-local"
```

---

## 📚 更多文档

- [详细使用指南](USAGE.md) - 完整的功能说明
- [配置示例](templates/smart-router.yaml) - 配置文件模板
- [项目 SPEC](../specs/active/2026-04-18--smart-router.md) - 设计文档

---

**Happy Routing!** 🚀
