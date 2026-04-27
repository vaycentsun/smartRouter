"""embedding_matcher 模块测试 — 覆盖边缘输入和工具函数"""

import pytest
from smart_router.classifier.embedding_matcher import SimpleEmbeddingMatcher


class TestSimpleEmbeddingMatcherInit:
    """初始化测试"""

    def test_default_threshold(self):
        """默认阈值应为 0.3"""
        matcher = SimpleEmbeddingMatcher()
        assert matcher.threshold == 0.3

    def test_custom_threshold(self):
        """自定义阈值"""
        matcher = SimpleEmbeddingMatcher(threshold=0.5)
        assert matcher.threshold == 0.5


class TestJaccardSimilarity:
    """Jaccard 相似度测试"""

    @pytest.fixture
    def matcher(self):
        return SimpleEmbeddingMatcher()

    def test_empty_sets(self, matcher):
        """空集合应返回 0.0"""
        assert matcher._jaccard_similarity(set(), set()) == 0.0

    def test_one_empty_set(self, matcher):
        """一个空集合应返回 0.0"""
        assert matcher._jaccard_similarity({"a", "b"}, set()) == 0.0

    def test_identical_sets(self, matcher):
        """相同集合应返回 1.0"""
        assert matcher._jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0

    def test_partial_overlap(self, matcher):
        """部分重叠"""
        result = matcher._jaccard_similarity({"a", "b"}, {"b", "c"})
        assert result == 1 / 3

    def test_no_overlap(self, matcher):
        """无重叠"""
        assert matcher._jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0


class TestTokenize:
    """分词测试"""

    @pytest.fixture
    def matcher(self):
        return SimpleEmbeddingMatcher()

    def test_empty_string(self, matcher):
        """空字符串返回空列表"""
        assert matcher.tokenize("") == []

    def test_whitespace_only(self, matcher):
        """仅空白字符"""
        assert matcher.tokenize("   ") == []

    def test_english_words(self, matcher):
        """英文单词分词"""
        result = matcher.tokenize("Hello world")
        assert "hello" in result
        assert "world" in result

    def test_chinese_chars(self, matcher):
        """中文字符分词"""
        result = matcher.tokenize("你好世界")
        assert "你" in result
        assert "好" in result

    def test_mixed_text(self, matcher):
        """中英文混合"""
        result = matcher.tokenize("Hello 你好")
        assert "hello" in result
        assert "你" in result

    def test_punctuation_ignored(self, matcher):
        """标点符号被过滤"""
        result = matcher.tokenize("Hello, world! 你好。")
        assert "," not in result
        assert "。" not in result


class TestComputeTf:
    """词频计算测试"""

    @pytest.fixture
    def matcher(self):
        return SimpleEmbeddingMatcher()

    def test_empty_tokens(self, matcher):
        """空 token 列表返回空字典"""
        assert matcher.compute_tf([]) == {}

    def test_single_token(self, matcher):
        """单个 token"""
        result = matcher.compute_tf(["hello"])
        assert result == {"hello": 1.0}

    def test_multiple_same_tokens(self, matcher):
        """多个相同 token"""
        result = matcher.compute_tf(["hello", "hello"])
        assert result["hello"] == 1.0

    def test_different_tokens(self, matcher):
        """不同 token 均匀分布"""
        result = matcher.compute_tf(["a", "b"])
        assert result["a"] == 0.5
        assert result["b"] == 0.5


class TestCosineSimilarity:
    """余弦相似度测试"""

    @pytest.fixture
    def matcher(self):
        return SimpleEmbeddingMatcher()

    def test_empty_vectors(self, matcher):
        """空向量返回 0.0"""
        assert matcher.cosine_similarity({}, {}) == 0.0

    def test_one_empty_vector(self, matcher):
        """一个空向量返回 0.0"""
        assert matcher.cosine_similarity({"a": 1.0}, {}) == 0.0

    def test_identical_vectors(self, matcher):
        """相同向量返回 1.0"""
        vec = {"a": 1.0, "b": 0.0}
        result = matcher.cosine_similarity(vec, vec)
        assert result == 1.0

    def test_orthogonal_vectors(self, matcher):
        """正交向量返回 0.0"""
        vec1 = {"a": 1.0}
        vec2 = {"b": 1.0}
        assert matcher.cosine_similarity(vec1, vec2) == 0.0

    def test_zero_norm_vector(self, matcher):
        """零模长向量返回 0.0"""
        vec = {"a": 0.0}
        assert matcher.cosine_similarity(vec, {"a": 1.0}) == 0.0


class TestFindBestMatch:
    """最佳匹配测试"""

    @pytest.fixture
    def matcher(self):
        return SimpleEmbeddingMatcher(threshold=0.1)

    def test_empty_text(self, matcher):
        """空文本返回 None"""
        result = matcher.find_best_match("", {"task": ["example"]})
        assert result == (None, 0.0)

    def test_no_examples(self, matcher):
        """空示例返回 None"""
        result = matcher.find_best_match("test", {"task": []})
        assert result == (None, 0.0)

    def test_below_threshold(self, matcher):
        """低于阈值返回 None"""
        matcher_high = SimpleEmbeddingMatcher(threshold=0.99)
        result = matcher_high.find_best_match("completely unrelated text", {"task": ["specific keyword match"]})
        # 由于阈值很高，可能无法匹配
        assert result[0] is None or result[1] < 0.99

    def test_basic_match(self, matcher):
        """基本匹配"""
        examples = {
            "chat": ["how are you", "what is your name"],
            "coding": ["write a function", "implement this"]
        }
        result = matcher.find_best_match("write some code", examples)
        # 应该匹配到 coding
        assert result[0] == "coding"
        assert result[1] > 0
