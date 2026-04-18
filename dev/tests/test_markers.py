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
