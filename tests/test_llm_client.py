"""Tests marked with `requires_api_key` make a real call to the configured
LLM API and are skipped automatically when LLM_API_KEY isn't set (e.g. in
CI, which has no secret configured)."""

import os

import pytest

from llm_client import LLMConfigError, ask

requires_api_key = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set; skipping tests that call a real LLM API",
)


def test_missing_api_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(LLMConfigError):
        ask("does this raise?", [])


@requires_api_key
def test_answers_from_the_provided_passages():
    passages = [
        {"page": 3, "text": "Jupiter is the largest planet in the Solar System.", "score": 0.9}
    ]
    answer = ask("Which planet is the largest?", passages)
    assert "jupiter" in answer.lower()


@requires_api_key
def test_refuses_when_passages_dont_support_an_answer():
    passages = [
        {"page": 3, "text": "Jupiter is the largest planet in the Solar System.", "score": 0.9}
    ]
    answer = ask("What is the capital of France?", passages)
    assert "could not find" in answer.lower()
