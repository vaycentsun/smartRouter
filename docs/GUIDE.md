# Smart Router 使用指南

> 智能模型路由网关 —— 基于 LiteLLM 的多服务商自动路由 CLI 工具

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [安装配置](#安装配置)
4. [命令速查表](#命令速查表)
5. [CLI 命令详解](#cli-命令详解)
6. [阶段标记系统](#阶段标记系统)
7. [路由策略](#路由策略)
8. [客户端集成](#客户端集成)
9. [配置详解](#配置详解)
10. [故障排查](#故障排查)
11. [最佳实践](#最佳实践)

---

## 快速开始

### 5 分钟上手

```bash
# 1. 一键安装
./script/install.sh

# 2. 编辑配置，填入你的 API Key
vim smart-router.yaml

# 3. 健康检查
smr doctor

# 4. 启动服务（后台运行）
smr start

# 5. 查看状态
smr status
```

服务启动后，在另一个终端测试：

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-smart-router-local" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 服务管理命令

```bash
# 启动服务（后台运行）
smr start

# 前台运行（调试用）
smr start -f

# 查看运行状态
smr status

# 查看日志
smr logs
smr logs -f  # 持续跟踪

# 停止服务
smr stop

# 重启服务
smr restart
```

---

## 核心概念

### 什么是 Smart Router

Smart Router 是一个本地代理服务，它：

- **统一入口**：对外暴露标准 OpenAI API 格式
- **智能路由**：根据任务内容自动选择最合适的模型
- **多服务商支持**：同时管理 OpenAI、Claude、Qwen、Kimi 等多个服务商
- **阶段标记**：支持显式控制路由决策

### 工作流程

```
用户请求
    ↓
Smart Router 接收请求
    ↓
解析阶段标记 [stage:xxx]
    ↓ (无标记)
任务分类器 (L1规则 + L2相似度)
    ↓
模型选择器 (auto/speed/cost/quality)
    ↓
调用目标模型服务商
    ↓
返回响应
```

---

## 安装配置

### 系统要求

- Python 3.9+
- pip
- 至少一个 LLM 服务商的 API Key

### 安装步骤

```bash
# 一键安装
./script/install.sh

# 验证安装
smr doctor
```

安装脚本会自动完成：
1. 检查 Python 3.9+ 环境
2. 安装依赖（开发模式）
3. 验证安装
4. 生成默认配置文件

### 配置文件

运行 `smart-router init` 生成默认配置：

```yaml
# smart-router.yaml

server:
  port: 4000
  host: "127.0.0.1"
  master_key: "sk-smart-router-local"

model_list:
  # OpenAI
  - model_name: gpt-4o-mini
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY

  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  # Anthropic Claude
  - model_name: claude-3-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

  # 阿里通义千问
  - model_name: qwen-turbo
    litellm_params:
      model: dashscope/qwen-turbo
      api_key: os.environ/DASHSCOPE_API_KEY

  # Moonshot Kimi
  - model_name: kimi-k2
    litellm_params:
      model: moonshot/moonshot-v1-8k
      api_key: os.environ/MOONSHOT_API_KEY

  # MiniMax
  - model_name: minimax-m2
    litellm_params:
      model: minimax/MiniMax-Text-01
      api_key: os.environ/MINIMAX_API_KEY

  # 智谱 GLM
  - model_name: glm-5
    litellm_params:
      model: openai/glm-5
      api_base: https://open.bigmodel.cn/api/paas/v4
      api_key: os.environ/ZHIPU_API_KEY

smart_router:
  default_strategy: auto

  stage_routing:
    brainstorming:
      easy: ["qwen-turbo", "gpt-4o-mini"]
      medium: ["kimi-k2", "gpt-4o"]
      hard: ["claude-3-sonnet", "qwen-max"]

    code_review:
      easy: ["gpt-4o-mini"]
      medium: ["claude-3-sonnet", "glm-5"]
      hard: ["claude-3-opus", "deepseek-chat"]

    writing:
      easy: ["qwen-turbo"]
      medium: ["gpt-4o", "kimi-k2"]
      hard: ["claude-3-sonnet"]

    reasoning:
      easy: ["gpt-4o"]
      medium: ["deepseek-chat", "kimi-k2"]
      hard: ["claude-3-opus", "deepseek-r1"]

    chat:
      easy: ["qwen-turbo", "gpt-4o-mini"]
      medium: ["gpt-4o", "kimi-k2"]
      hard: ["claude-3-sonnet"]

  classification_rules:
    - pattern: '(?i)(review|审查|code.*quality|bug|lint)'
      task_type: code_review
      difficulty: medium

    - pattern: '(?i)(prove|证明|formal|theorem|形式化|verify)'
      task_type: reasoning
      difficulty: hard

    - pattern: '(?i)(write|draft|生成|撰写|compose)'
      task_type: writing
      difficulty: easy

    - pattern: '(?i)(brainstorm|头脑风暴|ideation|想一些)'
      task_type: brainstorming
      difficulty: easy

    - pattern: '(?i)(explain|解释|什么是|how to|怎么|如何)'
      task_type: chat
      difficulty: easy

  embedding_match:
    enabled: true
    custom_types: []

  fallback_chain:
    gpt-4o-mini: ["gpt-4o", "claude-3-sonnet"]
    qwen-turbo: ["qwen-max", "claude-3-sonnet"]
    kimi-k2: ["glm-5", "claude-3-sonnet"]
    gpt-4o: ["claude-3-sonnet", "qwen-max"]

  timeout:
    default: 30
    hard_tasks: 60

  max_fallback_retries: 2
```

### 环境变量设置

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# 阿里通义千问
export DASHSCOPE_API_KEY="sk-..."

# Moonshot
export MOONSHOT_API_KEY="sk-..."

# MiniMax
export MINIMAX_API_KEY="..."

# 智谱
export ZHIPU_API_KEY="..."
```

---

## 命令速查表

> 快速查找常用命令，详细说明见下方 [CLI 命令详解](#cli-命令详解)

### 安装与卸载

```bash
./script/install.sh         # 一键安装
./script/uninstall.sh       # 一键卸载
```

### 服务管理

```bash
smr start                   # 后台启动（推荐）
smr start -f                # 前台运行（调试）
smr stop                    # 停止服务
smr restart                 # 重启服务
smr status                  # 查看运行状态
smr logs                    # 查看最后 50 行日志
smr logs -f                 # 持续跟踪日志（tail -f）
```

### 配置管理

```bash
smr init                    # 生成默认配置文件
smr init -o ~/config/my.yaml        # 指定输出路径
smr validate                # 验证配置文件
```

### 路由测试

```bash
smr dry-run "帮我审查代码"          # 测试路由决策
smr dry-run "写文章" -s quality     # 指定 quality 策略
```

### 诊断工具

```bash
smr doctor                  # 运行健康检查
```

### 查看帮助

```bash
smr --help                  # 查看所有命令
smr start --help            # 查看具体命令帮助
```

> 💡 **提示**: `smr` 是 `smart-router` 的短命令别名，两者完全等价

---

## CLI 命令详解

### `init` - 初始化配置

生成默认配置文件：

```bash
# 在当前目录生成 smart-router.yaml
smart-router init

# 指定输出路径
smart-router init --output ~/config/smart-router.yaml
```

### `start` - 启动服务（推荐）

在**后台**启动 Smart Router 服务（推荐方式）：

```bash
# 后台启动（默认）
smart-router start

# 输出示例：
# ✓ Smart Router 已启动
#   PID: 12345
#   日志: ~/.smart-router/smart-router.log
#   服务: http://127.0.0.1:4000

# 指定配置文件
smart-router start --config ~/config/smart-router.yaml

# 前台运行（调试用）
smart-router start --foreground
```

**特点**：
- 后台运行，关闭终端后服务继续运行
- 自动记录 PID 到 `~/.smart-router/smart-router.pid`
- 日志自动保存到 `~/.smart-router/smart-router.log`

### `stop` - 停止服务

停止后台运行的 Smart Router 服务：

```bash
smart-router stop

# 输出示例：
# 正在停止 Smart Router (PID: 12345)...
# ✓ Smart Router 已停止
```

### `restart` - 重启服务

重启 Smart Router 服务：

```bash
smart-router restart

# 指定配置重启
smart-router restart --config ~/config/smart-router.yaml
```

### `status` - 查看状态

查看 Smart Router 运行状态：

```bash
smart-router status

# 运行中示例：
# ● Smart Router 运行中
#   PID: 12345
#   服务: http://127.0.0.1:4000
#   日志: ~/.smart-router/smart-router.log
#   最近日志:
#     INFO: Started server process [12345]

# 未运行示例：
# ● Smart Router 未运行
```

### `logs` - 查看日志

查看服务日志：

```bash
# 查看最后 50 行日志
smart-router logs

# 查看最后 100 行
smart-router logs --lines 100
smart-router logs -n 100

# 持续跟踪日志（类似 tail -f，按 Ctrl+C 退出）
smart-router logs --follow
smart-router logs -f
```

### `serve` - 前台启动（兼容）

前台启动服务（用于调试）：

```bash
# 使用默认配置
smart-router start --foreground

# 指定配置文件
smart-router start --foreground --config ~/config/smart-router.yaml
```

**注意**：此命令会阻塞终端，适合调试使用。生产环境建议使用 `smart-router start`（后台运行）。

服务启动后：
- API 端点：`http://localhost:4000/v1/chat/completions`
- 认证密钥：`sk-smart-router-local`（可在配置中修改）

### `dry-run` - 测试路由

测试路由决策，不实际调用模型：

```bash
# 基本用法
smart-router dry-run "帮我审查这段代码"

# 指定策略
smart-router dry-run "写一篇文章" --strategy quality

# 指定配置
smart-router dry-run "解释量子计算" --config ~/my-config.yaml
```

输出示例：
```
          Smart Router 路由决策
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 项目     ┃ 值                          ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 输入文本 │ 帮我审查这段 Python 代码    │
│ 识别标记 │ stage=None, difficulty=None │
│ 任务类型 │ code_review                 │
│ 预估难度 │ medium                      │
│ 置信度   │ 0.80                        │
│ 分类来源 │ rule_engine                 │
│ 策略     │ auto                        │
│ 选中模型 │ claude-3-sonnet             │
└──────────┴─────────────────────────────┘
```

### `validate` - 验证配置

运行健康检查（包含配置验证）：

```bash
smart-router doctor
```

输出示例：
```
✓ Python 版本: 3.9.6
✓ 核心模块导入正常
✓ 核心功能测试通过
✓ 配置文件存在: smart-router.yaml
✓ 配置加载成功 (11 个模型)
✓ 配置验证通过
  模型数: 11, 阶段数: 5, 规则数: 5
  规则数: 5
```

---

## 阶段标记系统

### 什么是阶段标记

阶段标记是在 prompt 中嵌入的特殊标记，用于显式控制路由决策：

```
[stage:code_review] 审查这段代码
[stage:writing] [difficulty:easy] 写一封邮件
```

### 支持的标记

| 标记 | 示例 | 说明 |
|------|------|------|
| `[stage:xxx]` | `[stage:code_review]` | 指定任务阶段 |
| `[difficulty:xxx]` | `[difficulty:hard]` | 指定难度级别 |

### 预定义阶段

| 阶段 | 用途 | 默认模型 |
|------|------|----------|
| `brainstorming` | 头脑风暴、创意发散 | qwen-turbo, gpt-4o-mini |
| `code_review` | 代码审查、bug 查找 | claude-3-sonnet, gpt-4o |
| `writing` | 写作、文案生成 | qwen-turbo, kimi-k2 |
| `reasoning` | 逻辑推理、数学证明 | claude-3-opus, deepseek-r1 |
| `chat` | 普通对话、问答 | qwen-turbo, gpt-4o-mini |

### 难度级别

| 级别 | 说明 | 典型场景 |
|------|------|----------|
| `easy` | 简单任务 | 日常问答、简单生成 |
| `medium` | 中等任务 | 代码审查、一般写作 |
| `hard` | 复杂任务 | 数学证明、复杂推理 |

### 使用示例

```python
# 显式指定代码审查
messages = [
    {"role": "user", "content": "[stage:code_review] 审查这段 Python 代码\n\ndef fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)"}
]

# 指定写作任务和难度
messages = [
    {"role": "user", "content": "[stage:writing] [difficulty:easy] 写一封请假邮件"}
]

# 复杂推理任务
messages = [
    {"role": "user", "content": "[stage:reasoning] [difficulty:hard] 证明费马小定理"}
]
```

---

## 路由策略

### 策略类型

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| `auto` | 使用配置中的默认推荐 | 大多数场景 |
| `speed` | 选择响应最快的模型 | 实时交互 |
| `cost` | 选择成本最低的模型 | 批量处理 |
| `quality` | 选择质量最高的模型 | 重要任务 |

### 使用策略

```bash
# CLI 中使用
smart-router dry-run "写一篇文章" --strategy quality

# 客户端中使用（通过 HTTP 头，需要扩展支持）
```

### 策略配置

在 `smart-router.yaml` 中配置每个阶段的模型列表：

```yaml
stage_routing:
  code_review:
    easy: ["gpt-4o-mini"]           # speed/cost 策略选择
    medium: ["claude-3-sonnet"]     # auto 策略选择
    hard: ["claude-3-opus"]         # quality 策略选择
```

---

## 客户端集成

### Python (OpenAI SDK)

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
print(response.choices[0].message.content)

# 使用阶段标记
response = client.chat.completions.create(
    model="auto",
    messages=[{
        "role": "user",
        "content": "[stage:writing] 写一封商务邮件"
    }]
)
```

### cURL

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-smart-router-local" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### JavaScript/TypeScript

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:4000',
  apiKey: 'sk-smart-router-local',
});

async function chat() {
  const response = await client.chat.completions.create({
    model: 'auto',
    messages: [{ role: 'user', content: '你好' }],
  });
  console.log(response.choices[0].message.content);
}
```

### Cursor / VS Code

在 Cursor 设置中：
1. 打开设置 → AI → OpenAI
2. 设置 Base URL: `http://localhost:4000`
3. 设置 API Key: `sk-smart-router-local`
4. 模型选择: `auto`

### Claude Code

```bash
claude config set apiBaseUrl http://localhost:4000
claude config set apiKey sk-smart-router-local
```

---

## 配置详解

### 完整配置示例

```yaml
# smart-router.yaml

# 服务器配置
server:
  port: 4000                    # 服务端口
  host: "127.0.0.1"            # 绑定地址（0.0.0.0 允许外部访问）
  master_key: "sk-smart-router-local"  # API 认证密钥

# 模型列表
model_list:
  - model_name: gpt-4o-mini     # 本地使用的模型名称
    litellm_params:
      model: openai/gpt-4o-mini # LiteLLM 格式
      api_key: os.environ/OPENAI_API_KEY  # 环境变量引用

  - model_name: claude-3-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

# 智能路由配置
smart_router:
  default_strategy: auto        # 默认策略

  # 阶段路由表
  stage_routing:
    brainstorming:
      easy: ["qwen-turbo", "gpt-4o-mini"]
      medium: ["kimi-k2", "gpt-4o"]
      hard: ["claude-3-sonnet", "qwen-max"]

  # 分类规则（正则匹配）
  classification_rules:
    - pattern: '(?i)(review|审查)'
      task_type: code_review
      difficulty: medium

  # Embedding 匹配配置
  embedding_match:
    enabled: true
    custom_types: []            # 自定义任务类型

  # Fallback 链
  fallback_chain:
    gpt-4o-mini: ["gpt-4o", "claude-3-sonnet"]

  # 超时配置
  timeout:
    default: 30                 # 默认超时（秒）
    hard_tasks: 60              # 困难任务超时

  max_fallback_retries: 2       # 最大重试次数
```

### 配置优先级

1. 命令行参数 (`--config`)
2. 当前目录的 `smart-router.yaml`
3. 向上查找父目录的 `smart-router.yaml`

---

## 故障排查

### 常见问题

#### 1. 服务启动失败

```bash
# 检查依赖
pip install litellm typer rich pyyaml pydantic

# 检查端口占用
lsof -i :4000

# 使用其他端口
# 修改 smart-router.yaml 中的 port
```

**后台启动失败**：

```bash
# 查看详细错误日志
smart-router logs

# 前台运行查看实时错误
smart-router start --foreground

# 检查 PID 文件
ls ~/.smart-router/smart-router.pid

# 手动清理 PID 文件（如果进程已不存在）
rm ~/.smart-router/smart-router.pid
```

#### 2. 服务无法停止

```bash
# 查看当前状态
smart-router status

# 如果状态显示运行但无法停止，手动终止
kill -9 $(cat ~/.smart-router/smart-router.pid)
rm ~/.smart-router/smart-router.pid

# 或使用 lsof 查找并终止
lsof -i :4000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

#### 3. API Key 错误

```bash
# 检查环境变量
echo $OPENAI_API_KEY

# 运行健康检查（包含配置验证）
smart-router doctor

# 测试时临时设置
export OPENAI_API_KEY="sk-..."
smart-router start
```

#### 4. 模型无法访问

```bash
# 测试单个模型连通性
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 查看 LiteLLM 日志
smart-router logs -f

# 在配置中添加 debug: true
```

#### 5. 路由不生效

```bash
# 使用 dry-run 测试
smart-router dry-run "你的提示文本"

# 运行健康检查
smart-router doctor

# 查看路由决策日志
smart-router logs | grep "路由决策"
```

#### 6. 日志查看问题

```bash
# 日志文件位置
cat ~/.smart-router/smart-router.log

# 日志文件过大，清空日志
> ~/.smart-router/smart-router.log

# 限制日志大小（生产环境建议）
smart-router logs | tail -n 1000 > /tmp/temp.log
mv /tmp/temp.log ~/.smart-router/smart-router.log
```

### 调试模式

```python
# 在代码中启用调试
import litellm
litellm.set_verbose = True
```

---

## 最佳实践

### 1. 配置管理

```bash
# 为不同环境创建不同配置
smart-router init --output ~/.config/smart-router/prod.yaml
smart-router init --output ~/.config/smart-router/dev.yaml

# 使用环境变量切换
export SMART_ROUTER_CONFIG=~/.config/smart-router/prod.yaml
smart-router start --config $SMART_ROUTER_CONFIG
```

### 2. 阶段标记使用

- **简单任务**：不需要标记，让系统自动分类
- **明确场景**：使用 `[stage:xxx]` 确保路由正确
- **复杂任务**：使用 `[difficulty:hard]` 确保使用强模型

### 3. 成本优化

```yaml
# 默认使用小模型
stage_routing:
  chat:
    easy: ["qwen-turbo"]      # 成本低
    medium: ["gpt-4o"]
    hard: ["claude-3-sonnet"] # 成本高

# 批量任务使用 cost 策略
smart-router dry-run "批量任务" --strategy cost
```

### 4. 质量保障

```yaml
# 重要任务使用 quality 策略
# 或显式指定强模型

messages = [
    {"role": "user", "content": "[stage:reasoning] [difficulty:hard] 关键任务"}
]
```

### 5. 服务管理最佳实践

```bash
# 创建启动脚本 ~/start-smart-router.sh
#!/bin/bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-..."
cd ~/smartRouter
smart-router start

# 创建停止脚本 ~/stop-smart-router.sh
#!/bin/bash
smart-router stop

# 添加到系统启动（macOS）
# 创建 ~/Library/LaunchAgents/com.smart-router.plist

# 使用 systemd 管理（Linux 生产环境）
# 创建 /etc/systemd/system/smart-router.service
```

**systemd 服务配置示例**：

```ini
# /etc/systemd/system/smart-router.service
[Unit]
Description=Smart Router Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/smartRouter
Environment="OPENAI_API_KEY=sk-..."
Environment="ANTHROPIC_API_KEY=sk-..."
ExecStart=/usr/local/bin/smart-router start --foreground
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable smart-router
sudo systemctl start smart-router
sudo systemctl status smart-router
sudo systemctl stop smart-router
```

### 6. 日志轮转

```bash
# 使用 logrotate（Linux）
# 创建 /etc/logrotate.d/smart-router

# 手动清理日志（添加到 crontab）
0 0 * * 0 > ~/.smart-router/smart-router.log
```

---

## 高级用法

### 自定义任务类型

```yaml
smart_router:
  embedding_match:
    enabled: true
    custom_types:
      - name: "sql_optimization"
        examples:
          - "优化 SQL 查询"
          - "添加索引建议"
          - "查询性能调优"
```

### 自定义分类规则

```yaml
classification_rules:
  - pattern: '(?i)(sql|查询|索引|database)'
    task_type: sql_optimization
    difficulty: medium
```

### Fallback 链配置

```yaml
fallback_chain:
  # 小模型失败时升级
  gpt-4o-mini: ["gpt-4o", "claude-3-sonnet"]
  qwen-turbo: ["qwen-max", "claude-3-sonnet"]
  
  # 国内模型失败时切换到国际模型
  qwen-max: ["gpt-4o", "claude-3-sonnet"]
  kimi-k2: ["gpt-4o", "claude-3-sonnet"]
```

---

## 更新日志

### v0.1.0 (2026-04-18)

- 初始版本发布
- 支持 6 家模型服务商
- 实现 L1 规则引擎 + L2 Embedding 匹配
- 支持阶段标记系统
- 4 种路由策略
- 完整的 CLI 工具
- 27 个单元测试

---

## 相关资源

- [LiteLLM 文档](https://docs.litellm.ai/)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [项目 SPEC](../specs/active/2026-04-18--smart-router.md)
- [快速开始指南](../README.md#5-分钟快速开始) - 回到主 README

---

## 反馈和支持

如有问题或建议，请：
1. 查看本使用指南
2. 运行 `smart-router doctor` 检查配置和运行状态
3. 使用 `smart-router dry-run` 测试路由
4. 提交 Issue 到项目仓库

---

**Happy Routing!** 🚀
