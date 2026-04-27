"""token_counter 单元测试 — 补充边界条件"""

import pytest
from smart_router.utils.token_counter import estimate_tokens, estimate_messages_tokens


class TestEstimateTokens:
    """estimate_tokens 边界条件测试"""

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_single_char(self):
        assert estimate_tokens("a") == 1

    def test_single_chinese_char(self):
        assert estimate_tokens("你") == 1

    def test_whitespace_only(self):
        assert estimate_tokens("   ") >= 1

    def test_pure_english_short(self):
        result = estimate_tokens("Hello")
        assert 1 <= result <= 3

    def test_pure_english_long(self):
        text = "The quick brown fox jumps over the lazy dog."
        result = estimate_tokens(text)
        assert result >= 5

    def test_pure_chinese_short(self):
        result = estimate_tokens("你好")
        assert result >= 1

    def test_pure_chinese_long(self):
        text = "这是一段用于测试中文文本token估算的较长文本内容包含了多个中文字符"
        result = estimate_tokens(text)
        assert result >= 5

    def test_mixed_chinese_english(self):
        result = estimate_tokens("Hello世界")
        assert result >= 2

    def test_mixed_with_numbers(self):
        result = estimate_tokens("Python 3.9 版本发布")
        assert result >= 3

    def test_mixed_with_punctuation(self):
        result = estimate_tokens("你好！Hello, world.")
        assert result >= 3

    def test_very_long_text(self):
        text = "a" * 10000
        result = estimate_tokens(text)
        assert result >= 2000

    def test_emoji_text(self):
        result = estimate_tokens("你好👍🎉")
        assert result >= 2

    def test_code_snippet(self):
        text = "def hello(): print('world')"
        result = estimate_tokens(text)
        assert result >= 3

    def test_tab_and_newline(self):
        text = "line1\nline2\tline3"
        result = estimate_tokens(text)
        assert result >= 2


class TestEstimateMessagesTokens:
    """estimate_messages_tokens 边界条件测试"""

    def test_none_messages(self):
        assert estimate_messages_tokens(None) == 0

    def test_empty_list(self):
        assert estimate_messages_tokens([]) == 0

    def test_single_message_with_content(self):
        messages = [{"role": "user", "content": "Hello world"}]
        result = estimate_messages_tokens(messages)
        assert result >= 7

    def test_single_message_empty_content(self):
        messages = [{"role": "user", "content": ""}]
        result = estimate_messages_tokens(messages)
        assert result == 7

    def test_message_missing_content_key(self):
        messages = [{"role": "user"}]
        result = estimate_messages_tokens(messages)
        assert result == 7

    def test_message_with_none_content(self):
        messages = [{"role": "user", "content": None}]
        result = estimate_messages_tokens(messages)
        assert result >= 7

    def test_message_with_non_string_content(self):
        messages = [{"role": "user", "content": 12345}]
        result = estimate_messages_tokens(messages)
        assert result >= 7

    def test_non_dict_message_skipped(self):
        messages = ["invalid_message"]
        result = estimate_messages_tokens(messages)
        assert result == 3

    def test_system_plus_user_messages(self):
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "你好"},
        ]
        result = estimate_messages_tokens(messages)
        assert result >= 15

    def test_long_conversation(self):
        messages = [
            {"role": "user", "content": "问题" + str(i)}
            for i in range(20)
        ]
        result = estimate_messages_tokens(messages)
        assert result >= 20 * 4 + 3

    def test_chinese_content_only(self):
        messages = [{"role": "user", "content": "这是一段纯中文内容"}]
        result = estimate_messages_tokens(messages)
        assert result >= 4 + 4 + 3