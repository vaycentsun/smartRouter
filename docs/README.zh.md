<div align="right">
  <a href="./README.md">English</a> | <strong>中文</strong>
</div>

# Smart Router — 智能模型路由网关

基于 LiteLLM 的多服务商模型智能路由 CLI 工具。对外暴露统一 OpenAI API 接口，根据任务类型和难度自动选择最合适的底层大模型。

## 特性

- 🔑 **单一入口**：一个 API Key 管理所有服务商
- 🧠 **智能路由**：自动识别任务类型（coding/writing/reasoning/...）并选择最优模型
- 🏷️ **阶段标记**：`[stage:code_review]` 显式控制路由
- 🔄 **自动 Fallback**：模型失败时自动升级重试
- 🌐 **多服务商**：支持 OpenAI、Anthropic、Qwen、Kimi、MiniMax、GLM 等

---

## 🚀 5 分钟快速开始

### 1. 安装

```bash
./script/install.sh
```

### 2. 初始化配置

```bash
# 生成配置文件
smart-router init

# 编辑配置，填入你的 API Key
vim smart-router.yaml
```

配置示例：
```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
```

### 3. 启动服务（后台运行）

```bash
# 后台启动（推荐）
smart-router start

# 查看状态
smart-router status

# 输出示例：
# ● Smart Router 运行中
#   PID: 12345
#   服务: http://127.0.0.1:4000
#   日志: ~/.smart-router/smart-router.log
```

**前台运行**（用于调试）：
```bash
export OPENAI_API_KEY="your-key"
smart-router start --foreground
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
| `smart-router doctor` | 运行健康检查（包含配置验证） |
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

更多详细说明见 [阶段标记系统](GUIDE.md#阶段标记系统)。

---

## ⚙️ 配置说明

详见 `templates/smart-router.yaml` 中的详细注释。

### 路由策略

- `auto`：使用配置的默认推荐
- `speed`：选择响应速度最快的模型
- `cost`：选择成本最低的模型
- `quality`：选择质量最高的模型

更多配置说明见 [配置详解](GUIDE.md#配置详解)。

---

## 🔧 故障排查

### 服务无法启动

```bash
# 检查端口占用
lsof -i :4000

# 查看日志
smart-router logs

# 运行健康检查（包含配置验证）
smart-router doctor

# 前台运行查看详细错误
smart-router start --foreground
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

更多故障排查见 [故障排查](GUIDE.md#故障排查) 章节。

---

## 📚 详细文档

| 文档 | 内容 |
|------|------|
| [完整使用指南](GUIDE.md) | 详细的 CLI 命令说明、配置详解、最佳实践 |
| [配置模板](../config/smart-router.yaml) | 完整的配置文件示例 |
| [设计文档](specs/active/2026-04-18--smart-router.md) | 架构设计和技术规格 |

### 快速导航

- [CLI 命令详解](GUIDE.md#cli-命令详解) - `start`, `stop`, `dry-run`, `validate` 等命令的完整说明
- [客户端集成](GUIDE.md#客户端集成) - Python, JavaScript, Cursor, Claude Code 的配置方法
- [最佳实践](GUIDE.md#最佳实践) - 配置管理、成本优化、服务管理建议
- [高级用法](GUIDE.md#高级用法) - 自定义任务类型、Fallback 链配置
- [故障排查](GUIDE.md#故障排查) - 详细的故障排查步骤

---

## 🏗️ 架构

```
用户请求 → LiteLLM Proxy → SmartRouter 插件
                              ├── 阶段标记解析
                              ├── 任务分类 (L1规则 + L2相似度)
                              ├── 模型选择 (auto/speed/cost/quality)
                              └── Fallback 管理
                ↓
         目标模型服务商
```

### 组件

- `cli.py` - CLI 入口命令
- `plugin.py` - SmartRouter 核心插件
- `server.py` - LiteLLM Proxy 封装
- `config/` - 配置加载和验证
- `classifier/` - 任务分类器 (L1规则 + L2 Embedding)
- `selector/` - 模型选择策略
- `utils/` - 工具函数

---

## 🧪 开发

```bash
./script/install.sh

pytest tests/ -v
```

---

## 📄 License

MIT
