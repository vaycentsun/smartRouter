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


def test_case_insensitive():
    messages = [{"role": "user", "content": "[STAGE:CODE_REVIEW] 审查"}]
    result = parse_markers(messages)
    assert result.stage == "code_review"


def test_multiple_messages():
    messages = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "[stage:writing] 写报告"}
    ]
    result = parse_markers(messages)
    assert result.stage == "writing"


class TestStripMarkers:
    """strip_markers 函数测试"""

    def test_strip_single_stage_marker(self):
        text = "[stage:writing] 写邮件"
        assert strip_markers(text) == "写邮件"

    def test_strip_single_difficulty_marker(self):
        text = "[difficulty:hard] 证明定理"
        assert strip_markers(text) == "证明定理"

    def test_strip_both_markers(self):
        text = "[stage:code_review] [difficulty:hard] 审查代码"
        assert strip_markers(text) == "审查代码"

    def test_strip_no_markers(self):
        text = "普通问题没有标记"
        assert strip_markers(text) == "普通问题没有标记"

    def test_strip_marker_in_middle(self):
        text = "请帮我 [stage:writing] 写一篇文章"
        result = strip_markers(text)
        assert "请帮我" in result
        assert "写一篇文章" in result

    def test_strip_multiple_same_markers(self):
        text = "[stage:writing] 写 [stage:review] 审查"
        result = strip_markers(text)
        assert "写" in result
        assert "审查" in result

    def test_strip_marker_preserves_spacing(self):
        text = "[stage:chat]  你好  世界"
        result = strip_markers(text)
        assert "你好" in result
        assert "世界" in result

    def test_strip_case_insensitive(self):
        text = "[STAGE:WRITING] 写文章 [DIFFICULTY:EASY] 简单的"
        result = strip_markers(text)
        assert "写文章" in result
        assert "简单的" in result

    def test_strip_empty_string(self):
        assert strip_markers("") == ""

    def test_strip_only_markers(self):
        text = "[stage:chat] [difficulty:easy]"
        assert strip_markers(text).strip() == ""
