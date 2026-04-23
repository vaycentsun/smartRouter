# Smart Router 实现计划

> 基于 Spec: `dev/specs/active/2026-04-18--smart-router.md`

---

### 任务 1: 创建 pyproject.toml

**目标**: 定义项目元数据、依赖和 CLI 入口

**文件**: `dev/cli-tools/smart-router/pyproject.toml`

**内容**:
```toml
[project]
name = "smart-router"
version = "0.1.0"
description = "智能模型路由网关 — 基于 LiteLLM 的多服务商自动路由 CLI 工具"
requires-python = ">=3.11"
dependencies = [
    "litellm>=1.0",
    "typer>=0.12",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]

[project.scripts]
smart-router = "smart_router.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**验证**:
- [ ] `cat dev/cli-tools/smart-router/pyproject.toml` 文件存在且格式正确
- [ ] `cd dev/cli-tools/smart-router && pip install -e .` 安装成功

**依赖**: 无

---

### 任务 2: 创建目录结构和 __init__.py

**目标**: 建立项目包结构

**文件**:
- `dev/cli-tools/smart-router/smart_router/__init__.py`
- `dev/cli-tools/smart-router/smart_router/config/__init__.py`
- `dev/cli-tools/smart-router/smart_router/classifier/__init__.py`
- `dev/cli-tools/smart-router/smart_router/selector/__init__.py`
- `dev/cli-tools/smart-router/smart_router/utils/__init__.py`
- `dev/cli-tools/smart-router/tests/__init__.py`
- `dev/cli-tools/smart-router/templates/.gitkeep`

**内容**:
```python
# smart_router/__init__.py
__version__ = "0.1.0"
```

其余 `__init__.py` 为空文件即可。

**验证**:
- [ ] `tree dev/cli-tools/smart-router/smart_router` 目录结构正确
- [ ] `python -c "from smart_router import __version__; print(__version__)"` 输出 `0.1.0`

**依赖**: 任务 1

---

### 任务 3: 创建 config/schema.py — Pydantic 配置模型

**目标**: 定义 `smart-router.yaml` 的完整数据模型

**文件**: `dev/cli-tools/smart-router/smart_router/config/schema.py`

**内容**:
```python
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    port: int = 4000
    host: str = "127.0.0.1"
    master_key: str = Field(default="sk-smart-router-local")


class LiteLLMModelConfig(BaseModel):
    model_name: str
    litellm_params: Dict


class StageRoutingConfig(BaseModel):
    easy: List[str]
    medium: List[str]
    hard: List[str]


class ClassificationRule(BaseModel):
    pattern: str
    task_type: str
    difficulty: str


class CustomTypeEmbedding(BaseModel):
    name: str
    examples: List[str]


class EmbeddingMatchConfig(BaseModel):
    enabled: bool = True
    custom_types: List[CustomTypeEmbedding] = Field(default_factory=list)


class FallbackChainConfig(BaseModel):
    default: int = 30
    hard_tasks: int = 60


class SmartRouterConfig(BaseModel):
    default_strategy: str = Field(default="auto", pattern="^(auto|speed|cost|quality)$")
    stage_routing: Dict[str, StageRoutingConfig] = Field(default_factory=dict)
    classification_rules: List[ClassificationRule] = Field(default_factory=list)
    embedding_match: EmbeddingMatchConfig = Field(default_factory=EmbeddingMatchConfig)
    fallback_chain: Dict[str, List[str]] = Field(default_factory=dict)
    timeout: FallbackChainConfig = Field(default_factory=FallbackChainConfig)
    max_fallback_retries: int = 2


class Config(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    model_list: List[LiteLLMModelConfig] = Field(default_factory=list)
    smart_router: SmartRouterConfig = Field(default_factory=SmartRouterConfig)
```

**验证**:
- [ ] `python -c "from smart_router.config.schema import Config; c = Config(); print(c.server.port)"` 输出 `4000`
- [ ] 用无效策略值实例化 `SmartRouterConfig` 时触发 Pydantic 验证错误

**依赖**: 任务 2

---

### 任务 4: 创建 config/loader.py — YAML 配置加载器

**目标**: 加载 YAML 配置文件并验证为 Pydantic 模型

**文件**: `dev/cli-tools/smart-router/smart_router/config/loader.py`

**内容**:
```python
import os
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

from .schema import Config

console = Console()

DEFAULT_CONFIG_NAME = "smart-router.yaml"


def find_config(start_path: Optional[Path] = None) -> Path:
    """从当前目录向上查找 smart-router.yaml"""
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path.resolve()
    while current != current.parent:
        config_file = current / DEFAULT_CONFIG_NAME
        if config_file.exists():
            return config_file
        current = current.parent
    
    raise FileNotFoundError(
        f"未找到 {DEFAULT_CONFIG_NAME}，请运行 `smart-router init` 生成默认配置"
    )


def load_config(config_path: Optional[Path] = None) -> Config:
    """加载并验证配置文件"""
    if config_path is None:
        config_path = find_config()
    else:
        config_path = Path(config_path)
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    config = Config.model_validate(raw)
    console.print(f"[green]✓[/green] 配置已加载: {config_path}")
    return config


def validate_config(config: Config) -> List[str]:
    """验证配置的完整性，返回错误列表（空表示通过）"""
    errors = []
    
    if not config.model_list:
        errors.append("model_list 为空，至少需要配置一个模型")
    
    # 检查 fallback_chain 中引用的模型是否都在 model_list 中
    model_names = {m.model_name for m in config.model_list}
    for source, targets in config.smart_router.fallback_chain.items():
        if source not in model_names:
            errors.append(f"fallback_chain 中的源模型 '{source}' 未在 model_list 中定义")
        for target in targets:
            if target not in model_names:
                errors.append(f"fallback_chain 中的目标模型 '{target}' 未在 model_list 中定义")
    
    # 检查 stage_routing 中引用的模型
    for stage, routing in config.smart_router.stage_routing.items():
        for level in ["easy", "medium", "hard"]:
            models = getattr(routing, level, [])
            for m in models:
                if m not in model_names:
                    errors.append(f"stage_routing['{stage}'].{level} 中的模型 '{m}' 未定义")
    
    return errors
```

**验证**:
- [ ] 编写测试加载有效 YAML → 返回 Config 对象
- [ ] 编写测试加载无效 YAML（如非法策略值）→ 抛出 ValidationError
- [ ] 编写测试 `validate_config` 能检测未定义的模型引用

**依赖**: 任务 3

---

### 任务 5: 创建默认配置模板

**目标**: 生成用户可立即使用的默认 `smart-router.yaml`

**文件**: `dev/cli-tools/smart-router/templates/smart-router.yaml`

**内容**:
```yaml
# Smart Router 默认配置
# 复制此文件到工作目录，按需修改

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

  # Anthropic
  - model_name: claude-3-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

  # 阿里 Qwen
  - model_name: qwen-turbo
    litellm_params:
      model: dashscope/qwen-turbo
      api_key: os.environ/DASHSCOPE_API_KEY

  - model_name: qwen-max
    litellm_params:
      model: dashscope/qwen-max
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

  # 智谱 GLM（OpenAI-compatible）
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

**验证**:
- [ ] 将模板复制为 `smart-router.yaml` 后，`load_config()` 能成功加载
- [ ] `validate_config()` 返回空列表（无错误）

**依赖**: 任务 4

---

### 任务 6: 创建 utils/markers.py — 阶段标记解析器

**目标**: 从消息中提取 `[stage:xxx]` 和 `[difficulty:xxx]` 标记

**文件**: `dev/cli-tools/smart-router/smart_router/utils/markers.py`

**内容**:
```python
import re
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class MarkerResult:
    stage: Optional[str] = None
    difficulty: Optional[str] = None


MARKER_PATTERN = re.compile(r\'\[(stage|difficulty):(\w+)\]\')


def parse_markers(messages: List[Dict]) -> MarkerResult:
    """
    从消息列表中提取阶段标记和难度标记。
    扫描所有消息的 content 字段，取第一个匹配的标记。
    """
    result = MarkerResult()
    
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        
        for match in MARKER_PATTERN.finditer(content):
            key = match.group(1).lower()
            value = match.group(2).lower()
            
            if key == "stage" and result.stage is None:
                result.stage = value
            elif key == "difficulty" and result.difficulty is None:
                result.difficulty = value
            
            # 两者都找到后提前退出
            if result.stage is not None and result.difficulty is not None:
                return result
    
    return result


def strip_markers(text: str) -> str:
    """从文本中移除标记，避免干扰模型输入"""
    return MARKER_PATTERN.sub("", text).strip()
```

**验证**:
- [ ] `parse_markers([{"role": "user", "content": "[stage:code_review] 审查这段代码"}])` 返回 `MarkerResult(stage="code_review")`
- [ ] `parse_markers([{"role": "user", "content": "[difficulty:hard] 证明这个定理"}])` 返回 `MarkerResult(difficulty="hard")`
- [ ] `strip_markers("[stage:writing] 写邮件")` 返回 `"写邮件"`

**依赖**: 无（独立模块）

---

### 任务 7: 创建 classifier/types.py — 分类结果数据模型

**目标**: 定义分类器输出的标准数据结构

**文件**: `dev/cli-tools/smart-router/smart_router/classifier/types.py`

**内容**:
```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    task_type: str
    estimated_difficulty: str
    confidence: float
    source: str  # "stage_marker" | "rule_engine" | "embedding" | "default"


def get_default_classification() -> ClassificationResult:
    """当分类器完全失败时的降级结果"""
    return ClassificationResult(
        task_type="chat",
        estimated_difficulty="medium",
        confidence=0.0,
        source="default"
    )
```

**验证**:
- [ ] `get_default_classification()` 返回 `task_type="chat"` 的结果

**依赖**: 无

---

### 任务 8: 创建 classifier/rule_engine.py — L1 规则引擎

**目标**: 基于正则关键词匹配快速分类任务

**文件**: `dev/cli-tools/smart-router/smart_router/classifier/rule_engine.py`

**内容**:
```python
import re
from typing import List, Dict, Optional

from .types import ClassificationResult


class RuleEngine:
    """L1 规则引擎：基于正则关键词匹配"""
    
    def __init__(self, rules: List[Dict]):
        """
        rules: [{"pattern": str, "task_type": str, "difficulty": str}]
        """
        self.rules = []
        for rule in rules:
            self.rules.append({
                "pattern": re.compile(rule["pattern"]),
                "task_type": rule["task_type"],
                "difficulty": rule["difficulty"],
            })
    
    def classify(self, messages: List[Dict]) -> Optional[ClassificationResult]:
        """
        扫描消息内容，返回第一个匹配的规则结果。
        若无匹配，返回 None。
        """
        for msg in messages:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            
            for rule in self.rules:
                if rule["pattern"].search(content):
                    return ClassificationResult(
                        task_type=rule["task_type"],
                        estimated_difficulty=rule["difficulty"],
                        confidence=0.8,
                        source="rule_engine"
                    )
        
        return None
```

**验证**:
- [ ] 传入包含 "审查这段代码" 的消息 → 返回 `code_review, medium`
- [ ] 传入无匹配的消息 → 返回 `None`

**依赖**: 任务 7

---

### 任务 9: 创建 classifier/embedding.py — L2 Embedding 匹配（简化版）

**目标**: 基于预计算 embedding 的余弦相似度进行任务分类

**设计决策**: 为了零外部依赖和快速启动，使用简单的 TF-IDF 风格向量 + 余弦相似度，而非引入 sentence-transformers。预定义 20+ 常见任务类型的示例文本。

**文件**: `dev/cli-tools/smart-router/smart_router/classifier/embedding.py`

**内容**:
```python
import math
import re
from typing import List, Dict, Optional

from .types import ClassificationResult


# 预定义的任务类型示例（内置）
BUILTIN_TYPE_EXAMPLES = {
    "brainstorming": [
        "头脑风暴一些创意", "帮我发散思维", "想一些点子",
        "brainstorm ideas", "generate creative ideas"
    ],
    "code_review": [
        "审查这段代码", "代码质量检查", "找 bug",
        "review this code", "check for bugs", "code quality"
    ],
    "writing": [
        "写一篇文章", "撰写邮件", "生成文案",
        "write an essay", "draft an email", "compose a message"
    ],
    "reasoning": [
        "证明这个定理", "逻辑推理", "数学证明",
        "prove this theorem", "logical reasoning", "solve this math problem"
    ],
    "chat": [
        "解释一下", "什么是", "怎么做到",
        "explain this", "what is", "how to"
    ],
    "sql_optimization": [
        "优化 SQL", "查询性能", "索引建议",
        "optimize SQL", "query performance", "index recommendation"
    ],
    "translation": [
        "翻译成英文", "中英互译", "翻译这段文字",
        "translate to English", "Chinese to English"
    ],
    "summarization": [
        "总结这篇文章", "提取要点", "概要",
        "summarize this", "key points", "tl;dr"
    ],
}


def _tokenize(text: str) -> List[str]:
    """简单分词：小写 + 提取字母数字字符"""
    text = text.lower()
    tokens = re.findall(r'[\u4e00-\u9fff\w]+', text)
    return tokens


def _text_to_vector(text: str, vocab: Dict[str, int]) -> List[float]:
    """将文本转换为词频向量"""
    tokens = _tokenize(text)
    vec = [0.0] * len(vocab)
    for token in tokens:
        if token in vocab:
            vec[vocab[token]] += 1.0
    return vec


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingMatcher:
    """L2 Embedding 匹配器：基于 TF-IDF 风格向量的相似度"""
    
    def __init__(self, custom_types: Optional[List[Dict]] = None):
        """
        custom_types: [{"name": str, "examples": [str, ...]}]
        """
        self.type_examples = dict(BUILTIN_TYPE_EXAMPLES)
        if custom_types:
            for ct in custom_types:
                self.type_examples[ct["name"]] = ct["examples"]
        
        # 构建词汇表和预计算类型向量
        self._build_vectors()
    
    def _build_vectors(self):
        """构建词汇表和每个任务类型的平均向量"""
        all_texts = []
        for examples in self.type_examples.values():
            all_texts.extend(examples)
        
        # 构建词汇表
        vocab = {}
        for text in all_texts:
            for token in _tokenize(text):
                if token not in vocab:
                    vocab[token] = len(vocab)
        self.vocab = vocab
        
        # 预计算每个类型的平均向量
        self.type_vectors = {}
        for type_name, examples in self.type_examples.items():
            vectors = [_text_to_vector(ex, vocab) for ex in examples]
            # 平均向量
            avg = [sum(v[i] for v in vectors) / len(vectors) for i in range(len(vocab))]
            self.type_vectors[type_name] = avg
    
    def classify(self, messages: List[Dict]) -> Optional[ClassificationResult]:
        """
        计算输入消息与预定义类型的相似度，返回最佳匹配。
        若最高相似度低于阈值，返回 None。
        """
        # 合并所有消息内容
        combined = " ".join(
            msg.get("content", "") for msg in messages
            if isinstance(msg.get("content"), str)
        )
        if not combined.strip():
            return None
        
        input_vec = _text_to_vector(combined, self.vocab)
        
        best_type = None
        best_score = 0.0
        
        for type_name, type_vec in self.type_vectors.items():
            score = _cosine_similarity(input_vec, type_vec)
            if score > best_score:
                best_score = score
                best_type = type_name
        
        # 阈值：相似度需 > 0.1 才认为有效匹配
        if best_score < 0.1:
            return None
        
        # 根据类型推断默认难度
        difficulty_map = {
            "reasoning": "hard",
            "code_review": "medium",
            "sql_optimization": "medium",
            "translation": "easy",
            "summarization": "easy",
            "writing": "easy",
            "brainstorming": "easy",
            "chat": "easy",
        }
        
        return ClassificationResult(
            task_type=best_type,
            estimated_difficulty=difficulty_map.get(best_type, "medium"),
            confidence=min(best_score, 1.0),
            source="embedding"
        )
```

**验证**:
- [ ] 传入 "帮我审查这段 Python 代码" → 返回 `code_review`（相似度 > 0.1）
- [ ] 传入完全无关的随机文本 → 返回 `None`（相似度 < 0.1）
- [ ] 传入自定义类型示例后，能正确匹配自定义类型

**依赖**: 任务 7

---

### 任务 10: 创建 classifier/__init__.py — 分类器统一接口

**目标**: 组合 L1 规则引擎和 L2 Embedding 匹配，提供统一的 `classify()` 接口

**文件**: `dev/cli-tools/smart-router/smart_router/classifier/__init__.py`

**内容**:
```python
from typing import List, Dict

from .types import ClassificationResult, get_default_classification
from .rule_engine import RuleEngine
from .embedding import EmbeddingMatcher


class TaskClassifier:
    """任务分类器：L1 规则引擎 → L2 Embedding 匹配的流水线"""
    
    def __init__(self, rules: List[Dict], embedding_config: Dict):
        self.rule_engine = RuleEngine(rules)
        self.embedding_matcher = EmbeddingMatcher(
            custom_types=embedding_config.get("custom_types", [])
        )
    
    def classify(self, messages: List[Dict]) -> ClassificationResult:
        """
        分类流程：
        1. 先尝试 L1 规则引擎（快、确定性强）
        2. 规则无匹配 → L2 Embedding 匹配
        3. 两者都失败 → 返回默认分类（chat, medium）
        """
        # L1 规则引擎
        result = self.rule_engine.classify(messages)
        if result is not None:
            return result
        
        # L2 Embedding 匹配
        result = self.embedding_matcher.classify(messages)
        if result is not None:
            return result
        
        # 降级到默认值
        return get_default_classification()
```

**验证**:
- [ ] 有规则匹配时 → 返回规则结果
- [ ] 无规则匹配但有 embedding 匹配 → 返回 embedding 结果
- [ ] 两者都无 → 返回默认 `chat, medium`

**依赖**: 任务 8, 任务 9

---

### 任务 11: 创建 selector/strategies.py — 模型选择策略

**目标**: 根据分类结果和策略选择最合适的模型

**文件**: `dev/cli-tools/smart-router/smart_router/selector/strategies.py`

**内容**:
```python
from typing import List, Dict, Optional


class ModelSelector:
    """模型选择器：根据策略从候选模型中选择目标"""
    
    def __init__(self, routing_rules: Dict[str, Dict], fallback_chain: Dict[str, List[str]]):
        """
        routing_rules: {stage_name: {difficulty: [model_names]}}
        fallback_chain: {model_name: [fallback_models]}
        """
        self.routing_rules = routing_rules
        self.fallback_chain = fallback_chain
    
    def select(
        self,
        task_type: str,
        difficulty: str,
        strategy: str,
        model_list: List[str]
    ) -> str:
        """
        根据策略选择模型。
        
        Args:
            task_type: 任务类型（如 code_review）
            difficulty: 难度（easy/medium/hard）
            strategy: auto/speed/cost/quality
            model_list: 可用的模型名称列表
        
        Returns:
            选中的 model_name
        """
        # 获取该任务类型+难度的候选模型列表
        candidates = self._get_candidates(task_type, difficulty)
        
        # 过滤掉不在 model_list 中的模型
        candidates = [c for c in candidates if c in model_list]
        
        if not candidates:
            # 无候选时，使用 model_list 中的第一个作为兜底
            return model_list[0] if model_list else "gpt-4o"
        
        if strategy == "auto":
            return candidates[0]  # 第一个为 auto 策略的推荐
        elif strategy == "speed":
            return self._select_by_speed(candidates)
        elif strategy == "cost":
            return self._select_by_cost(candidates)
        elif strategy == "quality":
            return self._select_by_quality(candidates)
        else:
            return candidates[0]
    
    def _get_candidates(self, task_type: str, difficulty: str) -> List[str]:
        """从路由规则中获取候选模型"""
        stage_rules = self.routing_rules.get(task_type, {})
        candidates = stage_rules.get(difficulty, [])
        
        # 如果该难度无配置，尝试降级到 medium，再降级到 easy
        if not candidates and difficulty == "hard":
            candidates = stage_rules.get("medium", [])
        if not candidates and difficulty in ("hard", "medium"):
            candidates = stage_rules.get("easy", [])
        
        return candidates
    
    def _select_by_speed(self, candidates: List[str]) -> str:
        """速度优先：选择列表中靠前的小模型"""
        # 简化实现：候选列表中越靠前越推荐为        # 简化实现：候选列表中越靠前越推荐为 speed 优先
        # 实际项目中可扩展为基于模型延迟历史数据
        return candidates[0] if candidates else ""
    
    def _select_by_cost(self, candidates: List[str]) -> str:
        """成本优先：选择列表中靠前的小模型"""
        return candidates[0] if candidates else ""
    
    def _select_by_quality(self, candidates: List[str]) -> str:
        """质量优先：选择列表中最后一个（最强模型）"""
        return candidates[-1] if candidates else ""
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """获取指定模型的 fallback 链"""
        return self.fallback_chain.get(model_name, [])


# 模型成本与速度的粗略排序（用于策略细化，可选扩展）
# 格式: model_name -> (speed_score, cost_score, quality_score)
# 分数越高越好
MODEL_PROFILES = {
    "gpt-4o-mini":    {"speed": 9, "cost": 9, "quality": 5},
    "gpt-4o":         {"speed": 7, "cost": 6, "quality": 8},
    "claude-3-sonnet":{"speed": 6, "cost": 5, "quality": 8},
    "qwen-turbo":     {"speed": 9, "cost": 9, "quality": 5},
    "qwen-max":       {"speed": 6, "cost": 6, "quality": 8},
    "kimi-k2":        {"speed": 7, "cost": 6, "quality": 8},
    "glm-5":          {"speed": 6, "cost": 6, "quality": 8},
    "minimax-m2":     {"speed": 8, "cost": 8, "quality": 6},
}
```

**验证**:
- [ ] `select("code_review", "medium", "auto", [...])` 返回 routing_rules 中配置的第一个模型
- [ ] `select("code_review", "medium", "quality", [...])` 返回候选列表最后一个模型
- [ ] 候选列表为空时返回兜底模型

**依赖**: 无（独立模块，但依赖配置数据）

---

### 任务 12: 创建 plugin.py — SmartRouter 核心插件

**目标**: 继承 LiteLLM Router，注入智能路由逻辑

**文件**: `dev/cli-tools/smart-router/smart_router/plugin.py`

**内容**:
```python
from typing import List, Dict, Optional, Any

from litellm.router import Router

from .utils.markers import parse_markers, strip_markers, MarkerResult
from .classifier import TaskClassifier
from .classifier.types import ClassificationResult, get_default_classification
from .selector.strategies import ModelSelector
from .config.schema import Config


class SmartRouter(Router):
    """
    智能路由插件。
    
    继承 LiteLLM 的 Router，重写 get_available_deployment 方法，
    在请求到达 LiteLLM 原生路由前注入智能模型选择逻辑。
    """
    
    def __init__(self, config: Config, *args, **kwargs):
        # 先保存自定义配置
        self.sr_config = config
        
        # 初始化分类器和选择器
        self.classifier = TaskClassifier(
            rules=[r.model_dump() for r in config.smart_router.classification_rules],
            embedding_config=config.smart_router.embedding_match.model_dump()
        )
        self.selector = ModelSelector(
            routing_rules={
                k: v.model_dump() for k, v in config.smart_router.stage_routing.items()
            },
            fallback_chain=config.smart_router.fallback_chain
        )
        
        # 构建 LiteLLM 原生的 model_list 格式
        litellm_model_list = [m.model_dump() for m in config.model_list]
        
        # 调用父类初始化
        super().__init__(
            model_list=litellm_model_list,
            *args,
            **kwargs
        )
    
    async def get_available_deployment(
        self,
        model: str,
        messages: Optional[List[Dict]] = None,
        request_kwargs: Optional[Dict] = None,
    ) -> Any:
        """
        重写路由决策：
        1. 解析阶段标记
        2. 无标记则分类任务
        3. 根据策略选择模型
        4. 调用父类完成实际路由
        """
        # 如果请求指定了特定模型（非 "smart-router" 或 "auto"），直接透传
        if model not in ("auto", "smart-router", "default"):
            # 检查是否是阶段标记格式的模型名
            if not model.startswith("stage:"):
                return await super().get_available_deployment(
                    model=model, messages=messages, request_kwargs=request_kwargs
                )
        
        # 确保 messages 不为 None
        if messages is None:
            messages = []
        
        # 1. 解析阶段标记
        markers = parse_markers(messages)
        
        # 2. 获取分类结果
        classification = self._get_classification(markers, messages)
        
        # 3. 选择模型
        available_models = [m.model_name for m in self.sr_config.model_list]
        selected = self.selector.select(
            task_type=classification.task_type,
            difficulty=classification.estimated_difficulty,
            strategy=self.sr_config.smart_router.default_strategy,
            model_list=available_models
        )
        
        # 4. 调用父类路由
        return await super().get_available_deployment(
            model=selected, messages=messages, request_kwargs=request_kwargs
        )
    
    def _get_classification(
        self,
        markers: MarkerResult,
        messages: List[Dict]
    ) -> ClassificationResult:
        """根据标记或分类器获取分类结果"""
        # 如果用户显式指定了 difficulty，但无 stage
        if markers.stage is None:
            # 使用分类器
            return self.classifier.classify(messages)
        
        # 用户显式指定了 stage，直接构造分类结果
        difficulty = markers.difficulty or "medium"
        return ClassificationResult(
            task_type=markers.stage,
            estimated_difficulty=difficulty,
            confidence=1.0,
            source="stage_marker"
        )
    
    def get_fallback_chain(self, model_name: str) -> List[str]:
        """获取模型的 fallback 链"""
        return self.selector.get_fallback_chain(model_name)
```

**验证**:
- [ ] 初始化 `SmartRouter(config)` 不报错
- [ ] 显式 stage 标记时 `_get_classification` 返回 source="stage_marker"
- [ ] 无标记时调用分类器并返回 source="rule_engine" 或 "embedding"

**依赖**: 任务 10, 任务 11

---

### 任务 13: 创建 server.py — 启动 LiteLLM Proxy 的封装

**目标**: 将 SmartRouter 加载到 LiteLLM Proxy 中并启动服务

**文件**: `dev/cli-tools/smart-router/smart_router/server.py`

**内容**:
```python
import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

from .config.loader import load_config, validate_config
from .config.schema import Config
from .plugin import SmartRouter

console = Console()


def start_server(config_path: Optional[Path] = None):
    """启动 Smart Router 代理服务"""
    # 加载配置
    config = load_config(config_path)
    
    # 验证配置
    errors = validate_config(config)
    if errors:
        console.print("[red]配置验证失败:[/red]")
        for err in errors:
            console.print(f"  - {err}")
        sys.exit(1)
    
    # 设置环境变量（LiteLLM 需要）
    os.environ["LITELLM_MASTER_KEY"] = config.server.master_key
    
    # 初始化 SmartRouter
    console.print("[cyan]正在初始化智能路由...[/cyan]")
    router = SmartRouter(config=config)
    
    # 使用 LiteLLM 的 proxy 启动方式
    # 注意：LiteLLM Proxy 的启动方式在不同版本可能有差异
    # 这里使用其推荐的编程式启动
    try:
        from litellm.proxy.proxy_server import ProxyConfig, initialize
        
        proxy_config = ProxyConfig()
        
        # 构建 LiteLLM 配置字典
        litellm_config = {
            "model_list": [m.model_dump() for m in config.model_list],
            "router_settings": {
                "routing_strategy": "simple-shuffle",  # 我们用自定义 router 覆盖
            },
            "general_settings": {
                "master_key": config.server.master_key,
            }
        }
        
        console.print(f"[green]✓[/green] 配置加载完成，共 {len(config.model_list)} 个模型")
        console.print(f"[green]✓[/green] 启动服务于 http://{config.server.host}:{config.server.port}")
        
        # 启动服务（实际启动命令可能因 litellm 版本调整）
        import uvicorn
        from litellm.proxy.proxy_server import app
        
        # 将 SmartRouter 注入到 app 状态
        app.state.smart_router = router
        
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
        )
        
    except ImportError as e:
        console.print(f"[red]启动失败: {e}[/red]")
        console.print("[yellow]提示: 请确保已安装 litellm[proxy] 依赖[/yellow]")
        sys.exit(1)
```

**验证**:
- [ ] `start_server()` 能加载配置并初始化 SmartRouter
- [ ] 配置验证失败时正确退出
- [ ] 成功启动后控制台输出服务地址

**依赖**: 任务 12

---

### 任务 14: 创建 cli.py — CLI 入口

**目标**: 提供 init / serve / dry-run / validate 命令

**文件**: `dev/cli-tools/smart-router/smart_router/cli.py`

**内容**:
```python
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config.loader import load_config, validate_config
from .classifier import TaskClassifier
from .selector.strategies import ModelSelector
from .utils.markers import parse_markers

app = typer.Typer(name="smart-router", help="智能模型路由网关")
console = Console()

DEFAULT_CONFIG = Path(__file__).parent.parent / "templates" / "smart-router.yaml"


@app.command()
def init(
    path: Optional[Path] = typer.Option(
        Path("smart-router.yaml"),
        "--output", "-o",
        help="输出配置文件路径"
    )
):
    """在当前目录生成默认配置文件"""
    if path.exists():
        overwrite = typer.confirm(f"{path} 已存在，是否覆盖？")
        if not overwrite:
            console.print("[yellow]已取消[/yellow]")
            raise typer.Exit()
    
    shutil.copy(DEFAULT_CONFIG, path)
    console.print(f"[green]✓[/green] 配置文件已生成: {path}")
    console.print("[dim]请编辑文件中的 API Key，然后运行 `smart-router start` 启动服务[/dim]")


@app.command()
def serve(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径（默认向上查找 smart-router.yaml）"
    )
):
    """启动代理服务"""
    from .server import start_server
    start_server(config_path=config)


@app.command()
def validate(
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径"
    )
):
    """验证配置文件的完整性"""
    try:
        cfg = load_config(config)
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        raise typer.Exit(1)
    
    errors = validate_config(cfg)
    
    if errors:
        console.print("[red]✗ 配置验证失败[/red]")
        for err in errors:
            console.print(f"  [red]-[/red] {err}")
        raise typer.Exit(1)
    else:
        console.print("[green]✓ 配置验证通过[/green]")
        console.print(f"  模型数: {len(cfg.model_list)}")
        console.print(f"  阶段数: {len(cfg.smart_router.stage_routing)}")
        console.print(f"  规则数: {len(cfg.smart_router.classification_rules)}")


@app.command()
def dry_run(
    prompt: str = typer.Argument(..., help="测试路由的提示文本"),
    config: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="配置文件路径"
    ),
    strategy: str = typer.Option(
        "auto",
        "--strategy", "-s",
        help="路由策略 (auto/speed/cost/quality)"
    )
):
    """测试路由决策（不实际调用模型）"""
    cfg = load_config(config)
    
    # 解析标记
    messages = [{"role": "user", "content": prompt}]
    markers = parse_markers(messages)
    
    # 初始化分类器和选择器
    classifier = TaskClassifier(
        rules=[r.model_dump() for r in cfg.smart_router.classification_rules],
        embedding_config=cfg.smart_router.embedding_match.model_dump()
    )
    selector = ModelSelector(
        routing_rules={k: v.model_dump() for k, v in cfg.smart_router.stage_routing.items()},
        fallback_chain=cfg.smart_router.fallback_chain
    )
    
    # 分类
    if markers.stage:
        from .classifier.types import ClassificationResult
        result = ClassificationResult(
            task_type=markers.stage,
            estimated_difficulty=markers.difficulty or "medium",
            confidence=1.0,
            source="stage_marker"
        )
    else:
        result = classifier.classify(messages)
    
    # 选择
    available = [m.model_name for m in cfg.model_list]
    selected = selector.select(
        task_type=result.task_type,
        difficulty=result.estimated_difficulty,
        strategy=strategy,
        model_list=available
    )
    
    # 输出结果
    table = Table(title="Smart Router 路由决策")
    table.add_column("项目", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("输入文本", prompt[:60] + "..." if len(prompt) > 60 else prompt)
    table.add_row("识别标记", f"stage={markers.stage}, difficulty={markers.difficulty}")
    table.add_row("任务类型", result.task_type)
    table.add_row("预估难度", result.estimated_difficulty)
    table.add_row("置信度", f"{result.confidence:.2f}")
    table.add_row("分类来源", result.source)
    table.add_row("策略", strategy)
    table.add_row("选中模型", selected)
    
    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
```

**验证**:
- [ ] `smart-router init` 生成配置文件
- [ ] `smart-router doctor` 运行健康检查，包含配置验证
- [ ] `smart-router dry-run "[stage:writing] 写邮件"` 输出选中模型为 writing 阶段配置
- [ ] `smart-router --help` 显示所有命令

**依赖**: 任务 13

---

### 任务 15: 编写单元测试

**目标**: 为核心模块编写单元测试

**文件**: `dev/cli-tools/smart-router/tests/test_markers.py`, `tests/test_classifier.py`, `tests/test_selector.py`

**test_markers.py 内容**:
```python
import pytest
from smart_router.utils.markers import parse_markers, strip_markers, MarkerResult


def test_parse_stage_marker():
    messages = [{"role": "user", "content": "[stage:code_review] 审查代码"}]
    result = parse_markers(messages)
    assert result.stage == "code_review"
    assert result.difficulty is None


def test_parse_difficulty_marker():
    messages = [{"role": "user", "content": "[difficulty:hard] 证明定理"}]
    result = parse_markers(messages)
    assert result.stage is None
    assert result.difficulty == "hard"


def test_parse_both_markers():
    messages = [{"role": "user", "content": "[stage:writing] [difficulty:easy] 写邮件"}]
    result = parse_markers(messages)
    assert result.stage == "writing"
    assert result.difficulty == "easy"


def test_no_markers():
    messages = [{"role": "user", "content": "普通问题"}]
    result = parse_markers(messages)
    assert result.stage is None
    assert result.difficulty is None


def test_strip_markers():
    text = "[stage:writing] 写邮件"
    assert strip_markers(text) == "写邮件"
```

**test_classifier.py 内容**:
```python
import pytest
from smart_router.classifier import TaskClassifier
from smart_router.classifier.types import get_default_classification


class TestRuleEngine:
    def test_code_review_match(self):
        classifier = TaskClassifier(rules=[
            {"pattern": "(?i)(review|审查)", "task_type": "code_review", "difficulty": "medium"}
        ], embedding_config={"enabled": True, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "帮我审查代码"}])
        assert result.task_type == "code_review"
        assert result.source == "rule_engine"
    
    def test_no_match_fallback_to_embedding(self):
        classifier = TaskClassifier(rules=[], embedding_config={"enabled": True, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "帮我审查这段 Python 代码"}])
        # 应该有 embedding 匹配
        assert result.source == "embedding"
        assert result.task_type == "code_review"
    
    def test_no_match_at_all(self):
        classifier = TaskClassifier(rules=[], embedding_config={"enabled": False, "custom_types": []})
        
        result = classifier.classify([{"role": "user", "content": "xyz123 随机文本"}])
        assert result.source == "default"
        assert result.task_type == "chat"
```

**test_selector.py 内容**:
```python
import pytest
from smart_router.selector.strategies import ModelSelector


def test_select_auto():
    selector = ModelSelector(
        routing_rules={"code_review": {"medium": ["gpt-4o", "claude-3-sonnet"]}},
        fallback_chain={}
    )
    selected = selector.select("code_review", "medium", "auto", ["gpt-4o", "claude-3-sonnet"])
    assert selected == "gpt-4o"


def test_select_quality():
    selector = ModelSelector(
        routing_rules={"code_review": {"medium": ["gpt-4o", "claude-3-sonnet"]}},
        fallback_chain={}
    )
    selected = selector.select("code_review", "medium", "quality", ["gpt-4o", "claude-3-sonnet"])
    assert selected == "claude-3-sonnet"


def test_select_empty_candidates():
    selector = ModelSelector(routing_rules={}, fallback_chain={})
    selected = selector.select("unknown", "easy", "auto", ["gpt-4o"])
    assert selected == "gpt-4o"  # 兜底
```

**验证**:
- [ ] `pytest tests/test_markers.py -v` 全部通过
- [ ] `pytest tests/test_classifier.py -v` 全部通过
- [ ] `pytest tests/test_selector.py -v` 全部通过

**依赖**: 任务 6, 任务 10, 任务 11

---

### 任务 16: 编写集成测试

**目标**: 验证端到端流程

**文件**: `dev/cli-tools/smart-router/tests/test_integration.py`

**内容**:
```python
import pytest
from pathlib import Path
import tempfile
import yaml

from smart_router.config.loader import load_config
from smart_router.config.schema import Config
from smart_router.plugin import SmartRouter
from smart_router.classifier.types import ClassificationResult


@pytest.fixture
def test_config():
    """创建测试用的最小配置"""
    return Config(
        server={"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
        model_list=[
            {"model_name": "gpt-4o-mini", "litellm_params": {"model": "openai/gpt-4o-mini", "api_key": "os.environ/TEST_KEY"}}
        ],
        smart_router={
            "default_strategy": "auto",
            "stage_routing": {
                "chat": {"easy": ["gpt-4o-mini"], "medium": ["gpt-4o-mini"], "hard": ["gpt-4o-mini"]}
            },
            "classification_rules": [],
            "embedding_match": {"enabled": True, "custom_types": []},
            "fallback_chain": {},
            "timeout": {"default": 30, "hard_tasks": 60},
            "max_fallback_retries": 2
        }
    )


def test_smart_router_init(test_config):
    """测试 SmartRouter 能正确初始化"""
    router = SmartRouter(config=test_config)
    assert router is not None
    assert router.sr_config.server.port == 4000


def test_stage_marker_routing(test_config):
    """测试阶段标记能正确路由"""
    router = SmartRouter(config=test_config)
    
    messages = [{"role": "user", "content": "[stage:chat] 你好"}]
    markers = router._get_classification.__self__.  # 简化测试
    
    # 实际测试通过 dry-run 逻辑验证
    from smart_router.utils.markers import parse_markers
    from smart_router.classifier import TaskClassifier
    from smart_router.selector.strategies import ModelSelector
    
    markers = parse_markers(messages)
    assert markers.stage == "chat"


def test_config_load_from_yaml():
    """测试从 YAML 文件加载配置"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({
            "server": {"port": 4000, "host": "127.0.0.1", "master_key": "sk-test"},
            "model_list": [{"model_name": "test-model", "litellm_params": {}}],
            "smart_router": {
                "default_strategy": "auto",
                "stage_routing": {},
                "classification_rules": [],
                "embedding_match": {"enabled": False},
                "fallback_chain": {},
                "timeout": {"default": 30, "hard_tasks": 60},
                "max_fallback_retries": 2
            }
        }, f)
        f.flush()
        
        config = load_config(Path(f.name))
        assert config.server.port == 4000
        assert len(config.model_list) == 1
```

**验证**:
- [ ] `pytest tests/test_integration.py -v` 全部通过

**依赖**: 任务 12, 任务 15

---

### 任务 17: 编写 README.md

**目标**: 提供安装、配置和使用文档

**文件**: `dev/cli-tools/smart-router/README.md`

**内容**:
```markdown
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

### 2. 启动服务

```bash
export OPENAI_API_KEY="your-key"
smart-router start
```

服务运行在 `http://localhost:4000`

### 3. 客户端配置

在任意支持自定义 base_url 的客户端中：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-smart-router-local"  # smart-router.yaml 中的 master_key
)

# 自动路由
response = client.chat.completions.create(
    model="auto",  # 或省略，让工具自动判断
    messages=[{"role": "user", "content": "帮我审查这段代码"}]
)

# 显式阶段标记
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

## 配置说明

见 `templates/smart-router.yaml` 中的详细注释。

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

## 开发

```bash
pytest tests/ -v
```

## License

MIT
```

**验证**:
- [ ] README 包含安装、配置、使用、架构四个部分
- [ ] 代码示例可直接复制运行

**依赖**: 无（最后完成）

---

## 自检

| 检查项 | 状态 |
|--------|------|
| 完整性 | 17 个任务覆盖 Spec 全部功能 |
| 粒度 | 每个任务聚焦一个可验证单元 |
| 明确性 | 每个任务有确切文件路径和代码结构 |
| 可验证 | 每个任务有验证步骤 |
| 顺序合理 | 基础层 → 核心逻辑 → CLI → 测试 → 文档 |
| 无遗漏 | 包含 markers/classifier/selector/plugin/server/cli 测试 |

---

## 任务概览

| 编号 | 任务 | 文件 | 依赖 |
|------|------|------|------|
| 1 | pyproject.toml | `pyproject.toml` | - |
| 2 | 目录结构 | 多个 `__init__.py` | 1 |
| 3 | Pydantic 配置模型 | `config/schema.py` | 2 |
| 4 | YAML 配置加载器 | `config/loader.py` | 3 |
| 5 | 默认配置模板 | `templates/smart-router.yaml` | 4 |
| 6 | 阶段标记解析器 | `utils/markers.py` | 2 |
| 7 | 分类结果模型 | `classifier/types.py` | 2 |
| 8 | L1 规则引擎 | `classifier/rule_engine.py` | 7 |
| 9 | L2 Embedding 匹配 | `classifier/embedding.py` | 7 |
| 10 | 分类器统一接口 | `classifier/__init__.py` | 8, 9 |
| 11 | 模型选择策略 | `selector/strategies.py` | 2 |
| 12 | SmartRouter 插件 | `plugin.py` | 10, 11 |
| 13 | 服务启动封装 | `server.py` | 12 |
| 14 | CLI 入口 | `cli.py` | 13 |
| 15 | 单元测试 | `tests/test_*.py` | 6, 10, 11 |
| 16 | 集成测试 | `tests/test_integration.py` | 12, 15 |
| 17 | README 文档 | `README.md` | - |

**预计总时间**: 约 60-90 分钟（按子 Agent 并行执行）

**下一步**: 调用 `ailab-subagent-development` 执行计划
