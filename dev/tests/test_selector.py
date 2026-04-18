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


def test_select_speed():
    selector = ModelSelector(
        routing_rules={"code_review": {"medium": ["gpt-4o", "claude-3-sonnet"]}},
        fallback_chain={}
    )
    selected = selector.select("code_review", "medium", "speed", ["gpt-4o", "claude-3-sonnet"])
    assert selected == "gpt-4o"


def test_select_cost():
    selector = ModelSelector(
        routing_rules={"code_review": {"medium": ["gpt-4o", "claude-3-sonnet"]}},
        fallback_chain={}
    )
    selected = selector.select("code_review", "medium", "cost", ["gpt-4o", "claude-3-sonnet"])
    assert selected == "gpt-4o"


def test_select_empty_candidates():
    selector = ModelSelector(routing_rules={}, fallback_chain={})
    selected = selector.select("unknown", "easy", "auto", ["gpt-4o"])
    assert selected == "gpt-4o"


def test_select_filter_unavailable_models():
    selector = ModelSelector(
        routing_rules={"code_review": {"medium": ["gpt-4o", "claude-3-sonnet", "qwen-max"]}},
        fallback_chain={}
    )
    selected = selector.select("code_review", "medium", "auto", ["gpt-4o"])
    assert selected == "gpt-4o"


def test_select_difficulty_fallback():
    selector = ModelSelector(
        routing_rules={"code_review": {"easy": ["gpt-4o-mini"], "medium": ["gpt-4o"]}},
        fallback_chain={}
    )
    selected = selector.select("code_review", "hard", "auto", ["gpt-4o-mini", "gpt-4o"])
    assert selected == "gpt-4o"


def test_get_fallback_chain():
    selector = ModelSelector(
        routing_rules={},
        fallback_chain={"gpt-4o": ["gpt-4o-mini", "claude-3-sonnet"]}
    )
    chain = selector.get_fallback_chain("gpt-4o")
    assert chain == ["gpt-4o-mini", "claude-3-sonnet"]


def test_get_fallback_chain_empty():
    selector = ModelSelector(routing_rules={}, fallback_chain={})
    chain = selector.get_fallback_chain("unknown-model")
    assert chain == []
