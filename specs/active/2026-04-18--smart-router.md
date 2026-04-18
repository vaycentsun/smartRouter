---
name: smart-router
description: "Use when implementing smart-router CLI tool in aiLab project"
status: implemented
---

# Smart Router — 智能模型路由网关

## 概述

一个基于 LiteLLM Proxy 的本地 CLI 工具，对外暴露统一的 OpenAI API 接口，根据任务类型、难度和阶段标记自动将请求路由到最合适的底层大模型，实现"一个 API Key 走天下"。

## 背景与动机

用户在日常使用多个大模型 API（OpenAI、Claude、Qwen、Kimi、MiniMax、GLM 等）时面临以下痛点：
- 每个客户端需要配置多个 API Key 和 base_url
- 手动选择模型效率低，难以根据任务特性做最优选择
- 复杂任务需要拆分多步骤，希望不同步骤用不同模型
- 小模型搞不定的任务需要自动升级到更强模型

## 目标

- 提供单一本地入口，统一管理和路由多个服务商的模型
- 根据任务内容自动分类（coding / writing / reasoning / brainstorming / chat）并预估难度
- 支持用户在 prompt 中显式标记阶段 `[stage:xxx]`，直接路由到预设模型
- 支持多种路由策略：speed-first / cost-first / quality-first / auto（默认）
- 实现双层 Fallback：硬性失败（超时/报错）和软性失败（截断/空输出）自动升级模型重试
- 作为 LiteLLM 插件加载，不改动 LiteLLM 源码

## 非目标

- 不实现复杂的单请求内自动多步骤拆分编排（如先 plan 再 draft 再 review），此功能可通过显式阶段标记分多次调用实现
- 不提供 Web UI 管理后台，纯 CLI 工具
- 不做用量统计和计费功能（LiteLLM 自带，本项目不重复造轮子）
- 不涉及模型微调或模型训练

## 设计方案

### 架构概述

```
用户客户端 (Cursor / Claude Code / 自定义脚本)
    │  OpenAI API 格式, base_url = http://localhost:4000
    ▼
LiteLLM Proxy Server (端口 4000)
    │
    ├── 自定义 SmartRouter 插件 (继承 litellm.router.Router)
    │   ├── 阶段标记解析器 → 命中则直接路由
    │   ├── 任务分类器 (L1 规则引擎 + L2 Embedding 匹配)
    │   ├── 模型选择器 (策略: auto / speed / cost / quality)
    │   └── Fallback 管理器 (硬性/软性失败自动升级)
    │
    └── LiteLLM 原生模型池适配层
            │
    ┌───────┼───────┬──────────┐
    ▼       ▼       ▼          ▼
OpenAI  Anthropic  DashScope  Moonshot
              MiniMax  Zhipu(GLM兼容)
```

### 组件设计

#### 组件 1: CLI 入口 (smart_router/cli.py)

**职责**: 提供命令行接口，处理配置初始化和服务器启动

**接口**:
```python
# smart-router init → 生成默认 smart-router.yaml
# smart-router serve [--config path] → 启动代理服务
# smart-router dry-run "prompt" → 测试路由决策
# smart-router validate → 验证配置和模型连通性
```

**依赖**:
- Typer (CLI 框架)
- Rich (终端输出)

#### 组件 2: SmartRouter 插件 (smart_router/plugin.py)

**职责**: 继承 LiteLLM 的 Router 类，重写 `get_available_deployment` 方法注入智能路由逻辑

**接口**:
```python
class SmartRouter(Router):
    async def get_available_deployment(self, model, messages, request_kwargs):
        # 1. 解析阶段标记
        # 2. 若无标记，调用分类器
        # 3. 根据策略选择模型
        # 4. 调用父类完成实际路由
        pass
```

**依赖**:
- litellm (Router 基类)
- 阶段标记解析器
- 任务分类器
- 模型选择器

#### 组件 3: 阶段标记解析器 (smart_router/utils/markers.py)

**职责**: 从消息内容中提取 `[stage:xxx]` 和 `[difficulty:xxx]` 标记

**接口**:
```python
def parse_markers(messages: List[Dict]) -> Optional[MarkerResult]:
    """
    返回: {stage: str|None, difficulty: str|None}
    """
```

**依赖**: 无

#### 组件 4: 任务分类器 (smart_router/classifier/)

**职责**: 无显式标记时，自动判断任务类型和难度

**子组件**:
- `rule_engine.py`: L1 正则关键词匹配，<1ms，零成本
- `embedding.py`: L2 预定义任务类型 Embedding 相似度匹配，~10ms

**接口**:
```python
async def classify(messages: List[Dict]) -> ClassificationResult:
    """
    返回: {task_type: str, estimated_difficulty: str, confidence: float, source: str}
    """
```

**依赖**:
- 内置任务类型定义和 embedding 缓存
- 可选: sentence-transformers (本地 embedding，无网络调用)

#### 组件 5: 模型选择器 (smart_router/selector/strategies.py)

**职责**: 根据分类结果和策略从模型池中选择目标模型

**接口**:
```python
def select_model(
    task_type: str,
    difficulty: str,
    strategy: str,  # auto | speed | cost | quality
    routing_rules: Dict
) -> str:
    """返回选中的 model_name"""
```

**依赖**: 配置加载器提供的路由规则表

#### 组件 6: 配置加载器 (smart_router/config/)

**职责**: 加载和验证 `smart-router.yaml`，转换为 LiteLLM 兼容格式 + 自定义路由配置

**接口**:
```python
class Config:
    model_list: List[LiteLLMModelConfig]  # 原生格式
    smart_router: SmartRouterConfig       # 自定义配置域

def load_config(path: str) -> Config:
    """YAML → Pydantic 验证 → Config 对象"""
```

**依赖**:
- PyYAML
- Pydantic (配置验证)

### 数据流

```
用户请求 (OpenAI /v1/chat/completions 格式)
    │
    ▼
LiteLLM Proxy 接收请求
    │
    ▼
SmartRouter.get_available_deployment()
    │
    ├──→ parse_markers(messages)
    │    ├── 命中 stage? → 直接查 stage_routing 表 → 返回 model_name
    │    └── 未命中 → 继续
    │
    ├──→ classify(messages)
    │    ├── L1 rule_engine: 正则匹配 → 若有高置信命中，返回结果
    │    └── L2 embedding: 计算与预定义类型的相似度 → 返回 Top-1
    │
    ├──→ select_model(task_type, difficulty, strategy, rules)
    │    └── 根据策略查 routing_rules 映射表 → 返回 model_name
    │
    ├──→ 调用 LiteLLM 父类路由到目标模型
    │    └── 实际发送请求到对应服务商
    │
    └──→ Fallback 监控
         ├── 硬性失败? → 查 fallback_chain → 升级模型重试（最多2次）
         ├── 软性失败? → 同上
         └── 全部成功 → 返回响应 + X-Smart-Router-Model-Used 头
```

### 错误处理

- **配置错误**（启动时）: Pydantic 验证失败，打印具体错误位置，进程退出码 1
- **模型不可达**（启动时 `validate`）: `smart-router validate` 逐个测试模型池连通性，输出不通的模型列表
- **单次请求失败**: 按 fallback_chain 重试，全部失败后返回标准 OpenAI 错误格式，附加 `smart_router_meta` 调试信息
- **分类器失败**: 降级到默认模型（如 gpt-4o），不阻断请求

### 安全考虑

- 所有服务商 API Key 只通过环境变量引用，配置文件中不出现明文 Key
- master_key 用于客户端认证，建议用户设置强随机字符串
- 本地运行，默认只绑定 127.0.0.1，不暴露到公网
- 不收集任何遥测数据

## 验收标准

- [ ] `smart-router init` 能在当前目录生成可运行的默认配置文件
- [ ] `smart-router serve` 能成功启动 LiteLLM Proxy 并加载 SmartRouter 插件
- [ ] 使用标准 OpenAI SDK 调用 localhost:4000，能被正确路由到配置中的模型
- [ ] 在 prompt 中嵌入 `[stage:code_review]`，能跳过分类器直接路由到 code_review 预设模型
- [ ] 当首选模型返回 429 / 超时时，能自动按 fallback_chain 升级模型并重试
- [ ] `smart-router dry-run "写一段 Python 快速排序"` 能正确输出分类结果和选中的模型
- [ ] 响应头中包含 `X-Smart-Router-Model-Used`，标明实际使用的模型
- [ ] 支持 Qwen、Kimi、MiniMax、GLM 四家国内服务商（通过 LiteLLM 原生 provider 或 openai-compatible）

## 实现任务（概览）

> 详细任务将由 ailab-writing-specs Skill 制定

1. 项目脚手架：创建 `dev/cli-tools/smart-router/` 目录结构，配置 pyproject.toml
2. 配置系统：Pydantic 配置模型 + YAML 加载器 + 默认模板
3. 阶段标记解析器：正则提取 `[stage:xxx]` 和 `[difficulty:xxx]`
4. 任务分类器：L1 规则引擎 + L2 Embedding 匹配
5. 模型选择器：auto / speed / cost / quality 四种策略实现
6. SmartRouter 插件：继承 LiteLLM Router，集成上述组件
7. CLI 命令：init / serve / dry-run / validate
8. Fallback 管理器：硬性/软性失败检测 + 升级重试逻辑
9. 集成测试：模拟多服务商调用，验证路由和 fallback
10. 文档：README + 使用示例 + 配置说明

## 技术栈

- Python 3.11+
- LiteLLM (MIT License，作为基础代理层)
- Typer (CLI 框架)
- Pydantic (配置验证)
- PyYAML (配置解析)
- Rich (终端富文本输出)
- sentence-transformers 或 numpy + 预计算 embedding (本地相似度匹配，可选)
- pytest (测试)

## 依赖

### 外部依赖
- `litellm>=1.0` (核心代理层)
- `typer`
- `pydantic>=2.0`
- `pyyaml`
- `rich`

### 内部依赖
- aiLab 项目规范（AGENTS.md）
- dev/cli-tools/ 目录约定

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LiteLLM 插件接口 breaking change | 中 | 路由算法独立封装，只通过公开 Router API 交互；pin 兼容版本 |
| Embedding 模型首次加载慢 | 低 | 使用轻量本地模型（如 all-MiniLM-L6-v2，约 80MB）；或预计算缓存 |
| 分类器误判导致选错模型 | 中 | 用户可通过 `[stage:xxx]` 显式覆盖；fallback 机制兜底 |
| 国内服务商 API 格式变动 | 低 | LiteLLM 负责适配，本项目不直接对接服务商 API |
| 个人/内部工具无合规风险，未来若产品化需重新评估 | 低 | 当前定位明确为本地个人工具，不涉及数据出境/算法备案 |

## 附录

### 参考文档
- [LiteLLM Proxy 文档](https://docs.litellm.ai/docs/proxy/proxy)
- [LiteLLM Router 文档](https://docs.litellm.ai/docs/routing)
- [LiteLLM 自定义回调](https://docs.litellm.ai/docs/proxy/callbacks)

### 决策记录

**决策**: 基于 LiteLLM 做插件扩展（方案 C），而非自研代理（方案 A）
**原因**: LiteLLM 已解决多服务商适配、流式转换、重试等基础设施问题，且 MIT 许可证允许商用；自研代理需重复造轮子，且对用户当前 4-5 家服务商的场景没有明显优势
**替代方案**: 方案 A（自研轻量代理），已否决，理由见上

**决策**: 任务分类器只用 L1（规则）+ L2（Embedding），不引入 L3（轻量模型分类）
**原因**: 用户确认两层足够；L3 增加额外延迟和成本，对本地个人工具性价比不高
**替代方案**: L3 轻量模型分类，保留为未来可选增强

**决策**: 单请求内自动多步骤拆分编排（如 plan→draft→review）不纳入 MVP
**原因**: 在 LiteLLM 插件架构下实现复杂，且用户可通过多次显式标记 `[stage:plan]` `[stage:draft]` 达成类似效果
**替代方案**: 未来在 callback 层扩展多步骤编排
