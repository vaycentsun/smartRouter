# Smart Router v2 架构说明

## 🎯 概述

Smart Router v2 采用**模型声明式绑定架构**，将任务分类、难度评估、模型选择三个环节解耦，提供更灵活的路由控制。

---

## 🏗️ 架构对比

### v1 架构（旧）

```
用户输入 → 分类规则(task+difficulty) → stage_routing[stage][difficulty] → 模型
```

**问题**：
- 分类和难度耦合在一起
- 模型分配不够灵活
- 难以理解模型能力边界

### v2 架构（新）

```
用户输入 → 任务分类(task) → 难度评估(difficulty) → model_pool[capability] → 模型
         └─ Layer 1 ─┘    └─ Layer 2 ────┘      └─ Layer 3 ──────┘
```

**优势**：
- 三层解耦，独立调整
- 模型能力声明式定义
- 更清晰的路由逻辑

---

## 📋 配置说明

### 1. 任务类型定义（`task_types`）

仅定义任务类型的关键词，不涉及难度：

```yaml
task_types:
  writing:
    keywords: ["写", "文章", "邮件", "报告"]
    description: "写作任务"
    
  code_review:
    keywords: ["review", "审查", "代码"]
    description: "代码审查"
```

### 2. 难度评估规则（`difficulty_rules`）

独立评估难度：

```yaml
difficulty_rules:
  # 基于长度
  - condition: "length < 30"
    difficulty: easy
    description: "短文本"
    
  # 基于关键词
  - condition: "keyword:简单|快速|简述"
    difficulty: easy
    description: "用户要求简单"
    
  # 特定任务类型
  - condition: "keyword:架构|设计模式"
    difficulty: hard
    applies_to: ["code_review"]  # 仅对代码审查生效
```

### 3. 模型能力声明（`model_pool`）

**核心**：模型声明自己能做什么

```yaml
model_pool:
  default_model: "gpt-4o"
  
  capabilities:
    qwen3-122b:
      difficulties: [easy, medium]  # 只做 easy/medium
      task_types: [writing, chat, code_review]  # 只做这些任务
      priority: 1  # 优先级（数字小优先）
      
    claude-3-opus:
      difficulties: [hard]
      task_types: [writing, code_review, reasoning]
      priority: 1
      
    deepseek-r1:
      difficulties: [hard]
      task_types: [reasoning]  # 只做推理
      priority: 1
```

---

## 🚀 使用示例

### 启动 v2 架构

```bash
# 使用 v2 配置文件
smart-router start --config smart-router-v2.yaml
```

### 测试路由决策

```bash
# 查看详细路由过程
smart-router dry-run "帮我写一篇文章" --config smart-router-v2.yaml

# 显示所有候选模型
smart-router dry-run "帮我写篇文章" --config smart-router-v2.yaml --all
```

### 输出示例

```
架构版本: v2 (模型声明式)

路由决策详情
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 步骤        ┃ 结果       ┃ 详情                    ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1. 任务分类 │ writing    │ 置信度: 0.18 (keyword)  │
│ 2. 难度评估 │ easy       │ 规则: 非常短的文本      │
│ 3. 模型选择 │ qwen3-122b │ 优先级最高 (priority=1) │
└─────────────┴────────────┴─────────────────────────┘

所有候选模型 (3 个): qwen-turbo, qwen3-122b, gpt-4o

决策流程:
用户输入 → 任务分类(writing) → 难度评估(easy) → 模型选择(qwen3-122b)
```

---

## 🎨 模型能力配置建议

### 场景 1：成本优先

```yaml
model_pool:
  capabilities:
    minimax-m2:
      difficulties: [easy]
      task_types: [chat]
      priority: 1
      
    qwen-turbo:
      difficulties: [easy, medium]
      task_types: [writing, chat]
      priority: 2
      
    gpt-4o:
      difficulties: [hard]
      task_types: [writing, reasoning]
      priority: 1
```

### 场景 2：质量优先

```yaml
model_pool:
  capabilities:
    claude-3-opus:
      difficulties: [medium, hard]
      task_types: [writing, code_review, reasoning]
      priority: 1
      
    qwen3-122b:
      difficulties: [easy]
      task_types: [chat, brainstorming]
      priority: 1
```

### 场景 3：任务专精

```yaml
model_pool:
  capabilities:
    deepseek-r1:
      difficulties: [hard]
      task_types: [reasoning]  # 只做推理
      priority: 1
      
    claude-3-sonnet:
      difficulties: [medium, hard]
      task_types: [code_review]  # 专精代码
      priority: 1
      
    qwen3-122b:
      difficulties: [easy, medium]
      task_types: [writing, chat]  # 专精写作
      priority: 1
```

---

## 🔄 与 v1 架构共存

v2 架构完全向后兼容：

```yaml
smart_router:
  architecture_version: "v2"  # 设为 v1 使用旧架构
  
  # v2 配置
  task_types: {...}
  difficulty_rules: [...]
  model_pool: {...}
  
  # v1 配置（仍然有效）
  stage_routing: {...}
  classification_rules: [...]
```

---

## 📊 路由决策流程

```
┌─────────────────────────────────────────────┐
│ 1. 任务分类 (TaskTypeClassifier)             │
│    - 匹配 keywords                          │
│    - 输出: task_type                        │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 2. 难度评估 (DifficultyClassifier)           │
│    - 评估文本长度                           │
│    - 匹配关键词规则                         │
│    - 考虑任务类型上下文                     │
│    - 输出: difficulty                       │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│ 3. 模型选择 (ModelSelectorV2)                │
│    - 筛选支持该难度的模型                   │
│    - 筛选支持该任务类型的模型               │
│    - 按 priority 排序                       │
│    - 输出: model_name                       │
└─────────────────────────────────────────────┘
```

---

## 💡 最佳实践

1. **模型不要重复覆盖**：一个难度下优先选一个主力模型
2. **设置合理的 priority**：主力模型 priority=1，备选模型 priority=2
3. **限制 task_types**：避免模型做不擅长的任务
4. **利用 applies_to**：为特定任务类型设置特殊难度规则

---

## 🆚 版本选择

| 场景 | 推荐版本 |
|------|----------|
| 简单使用 | v1（stage_routing 简单直观） |
| 精细控制 | v2（模型声明式） |
| 多模型管理 | v2（能力一目了然） |
| 快速迁移 | v1 → v2（逐步迁移） |
