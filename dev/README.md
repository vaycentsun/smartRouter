# Smart Router — 智能模型路由网关

基于 LiteLLM 的多服务商模型智能路由 CLI 工具。对外暴露统一 OpenAI API 接口，根据任务类型和难度自动选择最合适的底层大模型。

## 特性

- 🔑 **单一入口**：一个 API Key 管理所有服务商
- 🧠 **智能路由**：自动识别任务类型（coding/writing/reasoning/...）并选择最优模型
- 🏷️ **阶段标记**：`[stage:code_review]` 显式控制路由
- 🔄 **自动 Fallback**：模型失败时自动升级重试
- 🌐 **多服务商**：支持 OpenAI、Anthropic、Qwen、Kimi、MiniMax、GLM 等

## 安装

```bash
cd dev/cli-tools/smart-router
pip install -e ".[dev]"
```

## 快速开始

### 1. 初始化配置

```bash
smart-router init
```

编辑生成的 `smart-router.yaml`，填入你的 API Key 环境变量名：

```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
```

### 2. 启动服务（后台运行）

```bash
# 后台启动（推荐）
smart-router start

# 查看状态
smart-router status

# 查看日志
smart-router logs

# 停止服务
smart-router stop

# 重启服务
smart-router restart
```

服务运行在 `http://localhost:4000`

**前台运行**（用于调试）：
```bash
export OPENAI_API_KEY="your-key"
smart-router start --foreground
# 或
smart-router serve
```

### 3. 客户端配置

在任意支持自定义 base_url 的客户端中：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-smart-router-local"
)

response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "帮我审查这段代码"}]
)

response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "[stage:code_review] 审查这段代码"}]
)
```

### 4. 测试路由决策（不调用模型）

```bash
smart-router dry-run "帮我写一段 Python 快速排序"
smart-router dry-run "[stage:writing] 写一封商务邮件" --strategy quality
```

### 5. 验证配置

```bash
smart-router validate
```

## 配置说明

详见 `templates/smart-router.yaml` 中的详细注释。

### 路由策略

- `auto`：使用配置的默认推荐
- `speed`：选择响应速度最快的模型
- `cost`：选择成本最低的模型
- `quality`：选择质量最高的模型

### 阶段标记

在 prompt 中使用标记显式控制路由：

- `[stage:xxx]` - 指定任务阶段
- `[difficulty:xxx]` - 指定难度 (easy/medium/hard)

示例：
```
[stage:code_review] [difficulty:hard] 审查这段代码
```

## 架构

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

## 开发

```bash
cd dev/cli-tools/smart-router
pip install -e ".[dev]"

pytest tests/ -v
```

## License

MIT
