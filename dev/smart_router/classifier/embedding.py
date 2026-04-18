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
