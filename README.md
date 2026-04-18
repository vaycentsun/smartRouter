<div align="right">
  <strong>English</strong> | <a href="./README.zh.md">中文</a>
</div>

# Smart Router — Intelligent Model Routing Gateway

A multi-provider model intelligent routing CLI tool based on LiteLLM. Exposes a unified OpenAI API interface and automatically selects the most suitable underlying LLM based on task type and difficulty.

## Features

- 🔑 **Single Entry**: One API Key manages all providers
- 🧠 **Smart Routing**: Auto-detects task types (coding/writing/reasoning/...) and selects optimal models
- 🏷️ **Stage Markers**: Explicit routing control with `[stage:code_review]`
- 🔄 **Auto Fallback**: Automatic model upgrade and retry on failure
- 🌐 **Multi-Provider**: Supports OpenAI, Anthropic, Qwen, Kimi, MiniMax, GLM, etc.

---

## 🚀 5-Minute Quick Start

### 1. Installation

```bash
cd dev
pip install -e ".[dev]"
```

### 2. Initialize Configuration

```bash
# Generate config file
smart-router init

# Edit config and add your API Keys
vim smart-router.yaml
```

Example configuration:
```yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
```

### 3. Start Service (Background)

```bash
# Start in background (recommended)
smart-router start

# Check status
smart-router status

# Output example:
# ● Smart Router is running
#   PID: 12345
#   Service: http://127.0.0.1:4000
#   Logs: ~/.smart-router/smart-router.log
```

**Foreground mode** (for debugging):
```bash
export OPENAI_API_KEY="your-key"
smart-router start --foreground
# or
smart-router serve
```

### 4. Test Routing (No Model Call)

```bash
# Test auto-routing
smart-router dry-run "Review this Python code"

# Use stage marker
smart-router dry-run "[stage:writing] Write a business email" --strategy quality
```

### 5. Client Usage

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-smart-router-local"
)

# Auto-routing
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Review this code"}]
)

# Use stage marker
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "[stage:code_review] Review this code"}]
)
```

---

## 📋 Quick Command Reference

### Service Management

| Command | Description |
|---------|-------------|
| `smart-router start` | Start service in background |
| `smart-router start --foreground` | Start in foreground (debug mode) |
| `smart-router stop` | Stop service |
| `smart-router restart` | Restart service |
| `smart-router status` | Check service status |

### Logs

| Command | Description |
|---------|-------------|
| `smart-router logs` | View last 50 lines of logs |
| `smart-router logs -n 100` | View last 100 lines |
| `smart-router logs -f` | Follow logs (Ctrl+C to exit) |

### Configuration & Testing

| Command | Description |
|---------|-------------|
| `smart-router init` | Generate default configuration |
| `smart-router validate` | Validate configuration |
| `smart-router dry-run "prompt text"` | Test routing decision |

---

## 🎯 Stage Markers

Add markers to prompts for explicit routing control:

```python
# Code review
"[stage:code_review] Review this code"

# Writing task (easy)
"[stage:writing] [difficulty:easy] Write an email"

# Complex reasoning
"[stage:reasoning] [difficulty:hard] Prove this theorem"
```

### Supported Stages

| Marker | Purpose | Default Models |
|--------|---------|----------------|
| `brainstorming` | Brainstorming ideas | qwen-turbo, gpt-4o-mini |
| `code_review` | Code review | claude-3-sonnet |
| `writing` | Writing tasks | qwen-turbo, kimi-k2 |
| `reasoning` | Logical reasoning | claude-3-opus |
| `chat` | General chat | qwen-turbo, gpt-4o-mini |

More details: [Stage Marker System](doc/GUIDE.md#stage-marker-system)

---

## ⚙️ Configuration

See detailed comments in `templates/smart-router.yaml`.

### Routing Strategies

- `auto`: Use default recommendations from config
- `speed`: Select fastest responding model
- `cost`: Select most cost-effective model
- `quality`: Select highest quality model

More configuration details: [Configuration Guide](doc/GUIDE.md#configuration)

---

## 🔧 Troubleshooting

### Service Won't Start

```bash
# Check port usage
lsof -i :4000

# View logs
smart-router logs

# Validate configuration
smart-router validate

# Run in foreground to see detailed errors
smart-router start --foreground
```

### Check Environment Variables

```bash
# Check API Keys
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Set environment variable
export OPENAI_API_KEY="sk-..."
```

### Test Connectivity

```bash
# Test if service is running
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-smart-router-local"
```

More troubleshooting: [Troubleshooting Guide](doc/GUIDE.md#troubleshooting)

---

## 📚 Documentation

| Document | Content |
|----------|---------|
| [Complete Guide](doc/GUIDE.md) | Detailed CLI commands, configuration, best practices |
| [Config Template](dev/templates/smart-router.yaml) | Complete configuration example |
| [Design Doc](specs/active/2026-04-18--smart-router.md) | Architecture design and technical specs |

### Quick Navigation

- [CLI Commands](doc/GUIDE.md#cli-commands) - Complete guide for `start`, `stop`, `dry-run`, `validate`
- [Client Integration](doc/GUIDE.md#client-integration) - Python, JavaScript, Cursor, Claude Code setup
- [Best Practices](doc/GUIDE.md#best-practices) - Configuration management, cost optimization
- [Advanced Usage](doc/GUIDE.md#advanced-usage) - Custom task types, Fallback chain config
- [Troubleshooting](doc/GUIDE.md#troubleshooting) - Detailed troubleshooting steps

---

## 🏗️ Architecture

```
User Request → LiteLLM Proxy → SmartRouter Plugin
                                  ├── Stage Marker Parsing
                                  ├── Task Classification (L1 Rules + L2 Similarity)
                                  ├── Model Selection (auto/speed/cost/quality)
                                  └── Fallback Management
                    ↓
            Target Model Provider
```

### Components

- `cli.py` - CLI entry commands
- `plugin.py` - SmartRouter core plugin
- `server.py` - LiteLLM Proxy wrapper
- `config/` - Configuration loading and validation
- `classifier/` - Task classifier (L1 Rules + L2 Embedding)
- `selector/` - Model selection strategies
- `utils/` - Utility functions

---

## 🧪 Development

```bash
cd dev
pip install -e ".[dev]"

pytest tests/ -v
```

---

## 📄 License

MIT
