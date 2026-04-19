# Smart Router 智能路由配置指南

## 📋 快速开始

### 1. 查看当前路由决策
```bash
source venv/bin/activate

# 测试不同场景的自动路由
smart-router dry-run "帮我 review 这段代码"
smart-router dry-run "帮我写一篇文章"
smart-router dry-run "证明勾股定理"
```

---

## 🎯 三种控制路由的方式

### 方式一：自动识别（推荐日常使用）

系统自动分析你的输入，匹配最合适的模型：

```bash
# 自动识别为 code_review → 路由到 claude-3-sonnet
curl http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-smart-router-local" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kimi-k2",
    "messages": [{"role": "user", "content": "帮我 review 这段代码"}]
  }'
```

**识别规则**（在 `smart-router.yaml` 中配置）：
- `code_review`: 包含 "review", "审查", "代码", "重构" 等关键词
- `writing`: 包含 "写", "撰写", "文章", "邮件" 等关键词
- `reasoning`: 包含 "证明", "数学题", "计算" 等关键词
- `brainstorming`: 包含 "想法", "方案", "创意" 等关键词
- `chat`: 其他普通对话

---

### 方式二：显式 Stage Marker（精确控制）

在消息中插入 `[stage:xxx]` 标记，强制指定任务类型：

```bash
# 强制使用 code_review 路由
curl http://127.0.0.1:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-smart-router-local" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kimi-k2",
    "messages": [{"role": "user", "content": "[stage:code_review] 分析这段代码"}]
  }'
```

**可用的 Stage Marker**：
- `[stage:code_review]` - 代码审查
- `[stage:writing]` - 写作任务
- `[stage:reasoning]` - 推理/数学
- `[stage:brainstorming]` - 头脑风暴
- `[stage:chat]` - 普通对话

**组合 difficulty**（可选）：
- `[stage:writing] [difficulty:hard] 写一份商业计划书`
- `[stage:code_review] [difficulty:easy] 简单看看这段代码`

---

### 方式三：切换策略（全局调整）

修改 `smart-router.yaml` 中的默认策略：

```yaml
smart_router:
  default_strategy: quality  # 可选: auto, speed, cost, quality
```

**策略说明**：

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| `auto` | 使用 medium 难度列表的第一个模型 | 平衡质量与速度 |
| `speed` | 选择最快的模型（列表第一个） | 追求响应速度 |
| `cost` | 选择最便宜的模型（列表第一个） | 节省成本 |
| `quality` | 选择最强的模型（列表最后一个） | 追求最佳质量 |

---

## ⚙️ 配置路由表（stage_routing）

编辑 `smart-router.yaml`：

```yaml
smart_router:
  stage_routing:
    # 代码审查场景
    code_review:
      easy: ["gpt-4o-mini"]                    # 简单检查 → 便宜快速
      medium: ["kimi-k2", "claude-3-sonnet"]   # 一般 CR → 平衡选择
      hard: ["claude-3-opus"]                  # 架构审查 → 最强模型

    # 写作场景
    writing:
      easy: ["qwen-turbo"]                     # 简单文案
      medium: ["kimi-k2", "gpt-4o"]            # 一般文章
      hard: ["claude-3-sonnet"]                # 专业写作

    # 推理场景
    reasoning:
      easy: ["gpt-4o"]
      medium: ["deepseek-chat", "kimi-k2"]
      hard: ["deepseek-r1", "claude-3-opus"]   # R1 推理最强

    # 普通对话
    chat:
      easy: ["minimax-m2", "qwen-turbo"]      # 快速响应
      medium: ["kimi-k2", "gpt-4o"]            # 平衡质量
      hard: ["claude-3-sonnet"]                # 复杂问题
```

**规则**：
- `auto` 策略 → 使用 `medium` 列表的第一个模型
- `speed/cost` 策略 → 使用对应列表的第一个模型
- `quality` 策略 → 使用对应列表的最后一个模型

---

## 📝 自定义分类规则

在 `classification_rules` 中添加正则表达式：

```yaml
classification_rules:
  # 自定义：当提到 "优化性能" 时，识别为 code_review + hard
  - pattern: '(?i)(优化性能|性能瓶颈|复杂度|算法优化|o(n)|时间复杂)'
    task_type: code_review
    difficulty: hard

  # 自定义：当提到 "小红书" 时，识别为 writing
  - pattern: '(?i)(小红书|文案|爆款|种草|笔记风格)'
    task_type: writing
    difficulty: medium
```

**正则语法**：
- `(?i)` - 忽略大小写
- `|` - 或
- `.*` - 匹配任意字符

---

## 🔄 Fallback 降级策略

当首选模型失败时，自动尝试备用模型：

```yaml
fallback_chain:
  kimi-k2: ["minimax-m2", "gpt-4o"]        # Kimi 失败 → 尝试 MiniMax → 再尝试 GPT-4o
  gpt-4o: ["kimi-k2", "claude-3-sonnet"]    # GPT-4o 失败 → 尝试 Kimi → 再尝试 Claude
  deepseek-chat: ["kimi-k2", "gpt-4o"]
```

---

## 🚀 实战示例

### 示例 1：编程助手配置
```yaml
# 让代码审查用 Claude，普通编程问题用 Kimi
stage_routing:
  code_review:
    medium: ["claude-3-sonnet"]      # CR 用 Claude（最强）
    hard: ["claude-3-opus"]
  
  chat:
    medium: ["kimi-k2"]               # 普通问题用 Kimi（快且便宜）
    hard: ["claude-3-sonnet"]
```

### 示例 2：写作助手配置
```yaml
# 不同写作场景用不同模型
stage_routing:
  writing:
    easy: ["minimax-m2"]              # 短文用 MiniMax（最快）
    medium: ["kimi-k2"]               # 一般文章用 Kimi（性价比高）
    hard: ["claude-3-sonnet"]         # 专业写作用 Claude（质量最高）
```

### 示例 3：数学/科研配置
```yaml
# 推理任务优先用 DeepSeek
stage_routing:
  reasoning:
    easy: ["gpt-4o"]
    medium: ["deepseek-chat"]         # 一般数学题
    hard: ["deepseek-r1"]             # 复杂推理用 R1
```

---

## 🛠️ 调试技巧

### 1. 查看路由决策
```bash
smart-router dry-run "你的输入文本"
```

### 2. 验证配置
```bash
smart-router validate
```

### 3. 查看日志
```bash
smart-router logs -f
```

### 4. 测试不同策略
```bash
smart-router dry-run --strategy quality "测试文本"
smart-router dry-run --strategy speed "测试文本"
```

---

## 📊 当前配置总览

查看完整的 `smart-router.yaml` 了解当前配置：
- 11 个模型配置（OpenAI、Claude、Kimi、MiniMax、DeepSeek、Qwen、GLM）
- 5 个任务类型（chat、writing、code_review、reasoning、brainstorming）
- 4 种策略（auto、speed、cost、quality）
- 自定义分类规则（中文关键词优化）

---

## 💡 最佳实践

1. **日常使用**: 依赖自动识别，无需修改配置
2. **精确控制**: 使用 `[stage:xxx]` 标记
3. **质量优先**: 设置 `default_strategy: quality`
4. **速度优先**: 设置 `default_strategy: speed`
5. **自定义场景**: 添加 `classification_rules` 正则规则
