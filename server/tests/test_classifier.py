"""Classifier tests — behavior assertions, not implementation details."""

import pytest
from app.classifier import classify, load_signatures


@pytest.fixture(autouse=True)
def load():
    load_signatures()


def test_gptbot_is_crawler_training():
    r = classify("GPTBot/1.2")
    assert r.verdict == "crawler_training"
    assert r.confidence >= 0.9
    assert any("openai_gptbot" in e for e in r.evidence)


def test_chatgpt_user_is_assistant_browse():
    r = classify("ChatGPT-User/1.0")
    assert r.verdict == "assistant_browse"
    assert r.confidence >= 0.95


def test_claude_user_is_assistant_browse():
    r = classify("Claude-User/1.0")
    assert r.verdict == "assistant_browse"


def test_claudebot_is_crawler_training():
    r = classify("ClaudeBot/1.0")
    assert r.verdict == "crawler_training"


def test_perplexity_user_is_assistant_browse():
    r = classify("Perplexity-User/1.0")
    assert r.verdict == "assistant_browse"


def test_googlebot_is_crawler_search():
    r = classify("Googlebot/2.1")
    assert r.verdict == "crawler_search"


def test_human_browser_is_human():
    r = classify("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0")
    assert r.verdict == "human"
    assert "ua_human_token" in r.evidence


def test_empty_ua_is_unknown():
    r = classify("")
    assert r.verdict == "unknown"
    assert "ua_empty" in r.evidence


def test_robots_txt_probe_flagged():
    r = classify("Mozilla/5.0 (compatible)", path="/robots.txt")
    assert r.verdict == "automation_other"
    assert any("probe_path" in e for e in r.evidence)


def test_result_always_has_evidence():
    for ua in ["GPTBot/1.0", "Mozilla/5.0", "", "SomeRandomBot/1.0"]:
        r = classify(ua)
        assert len(r.evidence) > 0, f"No evidence for UA: {ua!r}"
