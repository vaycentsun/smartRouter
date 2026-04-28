"""Simple Embedding Matcher - 基于词袋的相似度匹配

无需外部依赖，使用简单的词频向量和余弦相似度。
支持中英文混合文本。
"""

import re
import math
from typing import Dict, List, Tuple, Optional


class SimpleEmbeddingMatcher:
    """简单 Embedding 匹配器
    
    使用 TF（词频）向量和余弦相似度进行文本匹配。
    适合小规模的示例匹配场景。
    """
    
    def __init__(self, threshold: float = 0.3):
        """
        Args:
            threshold: 相似度阈值，超过此值认为匹配
        """
        self.threshold = threshold
    
    def _jaccard_similarity(self, set1: set, set2: set) -> float:
        """计算两个集合的 Jaccard 相似度"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        if union == 0:
            return 0.0
        return intersection / union
    
    def tokenize(self, text: str) -> List[str]:
        """分词：支持中英文
        
        - 英文：按空格和标点分词
        - 中文：按字符分词（简化处理）
        """
        text = text.lower().strip()
        if not text:
            return []
        
        # 提取英文单词
        english_words = re.findall(r'[a-z]+', text)
        
        # 提取中文字符（过滤掉标点和空格）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        
        return english_words + chinese_chars
    
    def compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """计算词频（TF）向量"""
        if not tokens:
            return {}
        
        freq = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1
        
        # 归一化
        total = len(tokens)
        return {k: v / total for k, v in freq.items()}
    
    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算两个向量的余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        # 计算点积
        dot_product = 0.0
        for key in vec1:
            if key in vec2:
                dot_product += vec1[key] * vec2[key]
        
        # 计算模长
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_best_match(
        self,
        text: str,
        examples_map: Dict[str, List[str]]
    ) -> Tuple[Optional[str], float]:
        """找到与输入文本最相似的示例类别
        
        使用余弦相似度和 Jaccard 相似度的加权组合，
        对短中文文本更鲁棒。
        
        Args:
            text: 输入文本
            examples_map: {task_type: [example1, example2, ...]}
            
        Returns:
            (最佳匹配的 task_type, 相似度分数)
            如果没有超过阈值的匹配，返回 (None, 0.0)
        """
        input_tokens = self.tokenize(text)
        input_set = set(input_tokens)
        input_vec = self.compute_tf(input_tokens)
        
        if not input_vec:
            return None, 0.0
        
        best_type = None
        best_score = 0.0
        
        for task_type, examples in examples_map.items():
            # 计算与所有示例的最大相似度（取最佳匹配）
            max_score = 0.0
            for example in examples:
                example_tokens = self.tokenize(example)
                example_vec = self.compute_tf(example_tokens)
                
                if example_vec:
                    # 组合余弦相似度和 Jaccard 相似度
                    cos_sim = self.cosine_similarity(input_vec, example_vec)
                    jac_sim = self._jaccard_similarity(input_set, set(example_tokens))
                    # 加权组合：余弦相似度权重 0.6，Jaccard 权重 0.4
                    combined = cos_sim * 0.6 + jac_sim * 0.4
                    max_score = max(max_score, combined)
            
            if max_score > best_score:
                best_score = max_score
                best_type = task_type
        
        if best_score >= self.threshold:
            return best_type, best_score
        
        return None, best_score
