<div align="right">
  <strong>English</strong> | <a href="./docs/README.zh.md">中文</a>
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

### Prerequisites

- **Python 3.9+** is required

### 1. Installation

Choose one of the following methods:

#### Option A: pip install (Recommended)

```bash
pip install smart-router
```

#### Option B: One-line curl install

```bash
curl -fsSL https://raw.githubusercontent.com/vaycentsun/smartRouter/main/script/install-remote.sh | bash
```

#### Option C: Homebrew (macOS/Linux)

```bash
brew tap vaycentsun/smart-router
brew install smart-router
```

#### Option D: Local install (from source)

```bash
git clone https://github.com/vaycentsun/smartRouter.git
cd smartRouter
./script/install.sh
```

### Uninstall

One-line uninstall:

```bash
curl -fsSL https://raw.githubusercontent.com/vaycentsun/smartRouter/main/script/uninstall.sh | bash
```

Or manually:

```bash
# Stop service
smart-router stop

# Uninstall package
pip uninstall smart-router

# Clean up data
rm -rf ~/.smart-router
```

### 2. Initialize Configuration

```bash
# Download config files via curl (no pip install needed)
curl -sSL https://raw.githubusercontent.com/vaycentsun/smartRouter/main/script/download-config.py | python3

# Or via CLI after pip install
smart-router init

# Force overwrite existing files
smart-router init --force

# Specify custom directory
smart-router init --output ./my-config
```

Edit the three config files:
```bash
vim ~/.smart-router/providers.yaml  # API keys and base URLs
vim ~/.smart-router/models.yaml     # Model capabilities
vim ~/.smart-router/routing.yaml    # Task definitions and routing strategies
```

Smart Router uses a three-file decoupled architecture:
- **providers.yaml** - API keys and base URLs per provider
- **models.yaml** - Model capabilities (quality/speed/cost scores)
- **routing.yaml** - Task definitions and routing strategies

See [Configuration Guide](#configuration) for details.

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

| `smart-router doctor` | Run health check (includes config validation) |
| `smart-router dry-run "prompt text"` | Test routing decision |
| `smart-router list` | List configured providers and models |

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

More details: [Stage Marker System](docs/GUIDE.md#stage-marker-system)

---

## ⚙️ Configuration

Smart Router uses a three-file decoupled architecture:

```
config/
├── providers.yaml    # Provider connection settings
├── models.yaml       # Model capability declarations  
└── routing.yaml      # Task definitions and routing rules
```

#### providers.yaml

Define API endpoints and authentication once per provider:

```yaml
providers:
  openai:
    api_base: https://api.openai.com/v1
    api_key: os.environ/OPENAI_API_KEY
    timeout: 30
    
  anthropic:
    api_base: https://api.anthropic.com
    api_key: os.environ/ANTHROPIC_API_KEY
```

#### models.yaml

Declare model capabilities (quality/speed/cost scores 1-10):

```yaml
models:
  gpt-4o:
    provider: openai              # References provider above
    litellm_model: openai/gpt-4o
    capabilities:
      quality: 9                  # Quality score (1-10)
      speed: 8                    # Response speed (1-10)
      cost: 3                     # Cost efficiency (10=cheapest)
      context: 128000             # Context window
    supported_tasks: [chat, code_review, writing]
    difficulty_support: [easy, medium, hard]
```

#### routing.yaml

Define tasks and routing strategies:

```yaml
tasks:
  code_review:
    name: "Code Review"
    description: "Review code quality"
    capability_weights:           # How to weight capabilities
      quality: 0.6                # 60% weight on quality
      speed: 0.2                  # 20% weight on speed
      cost: 0.2                   # 20% weight on cost

strategies:
  auto:     # Uses task weights to calculate composite score
  quality:  # Selects highest quality model
  speed:    # Selects fastest model
  cost:     # Selects most cost-effective model

fallback:
  mode: auto
  similarity_threshold: 2  # Models within ±2 quality are fallbacks
```

**Key advantages:**
- Add/remove models by editing only `models.yaml`
- Routing is dynamically calculated - no manual list maintenance
- Fallback chains auto-derived from capability similarity
- Clear separation of concerns

### Routing Strategies

- `auto`: Use weighted capability scores to select best model
- `speed`: Select fastest responding model
- `cost`: Select most cost-effective model
- `quality`: Select highest quality model

More configuration details: [Configuration Guide](docs/GUIDE.md#configuration)

---

## 🔧 Troubleshooting

### Service Won't Start

```bash
# Check port usage
lsof -i :4000

# View logs
smart-router logs

# Run health check (includes config validation)
smart-router doctor

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

More troubleshooting: [Troubleshooting Guide](docs/GUIDE.md#troubleshooting)

---

## 📚 Documentation

| Document | Content |
|----------|---------|
| [Complete Guide](docs/GUIDE.md) | Detailed CLI commands, configuration, best practices |
| [V3 Config Examples](config/examples/v3/) | V3 three-file configuration examples |
| [V3 Design Spec](specs/active/2026-04-19--config-v3-refactor.md) | V3 architecture design and migration guide |
| [Design Doc](specs/active/2026-04-18--smart-router.md) | Original architecture design and technical specs |

### Quick Navigation

- [CLI Commands](docs/GUIDE.md#cli-commands) - Complete guide for `start`, `stop`, `dry-run`, `validate`
- [Client Integration](docs/GUIDE.md#client-integration) - Python, JavaScript, Cursor, Claude Code setup
- [Best Practices](docs/GUIDE.md#best-practices) - Configuration management, cost optimization
- [Advanced Usage](docs/GUIDE.md#advanced-usage) - Custom task types, Fallback chain config
- [Troubleshooting](docs/GUIDE.md#troubleshooting) - Detailed troubleshooting steps

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

- `src/smart_router/cli.py` - CLI entry commands
- `src/smart_router/plugin.py` - SmartRouter core plugin (V2 config)
- `src/smart_router/plugin_v3_adapter.py` - V3 configuration adapter
- `src/smart_router/server.py` - LiteLLM Proxy wrapper
- `src/smart_router/config/` - Configuration loading and validation
  - `v3_schema.py` - V3 Pydantic schemas
  - `v3_loader.py` - V3 three-file config loader
- `src/smart_router/classifier/` - Task classifier (L1 Rules + L2 Embedding)
- `src/smart_router/selector/` - Model selection strategies
  - `v3_selector.py` - V3 capability-based selector
- `src/smart_router/utils/` - Utility functions

---

## 🧪 Development

```bash
pip install -e ".[dev]"

pytest tests/ -v
```

---

## 📄 License

MIT
