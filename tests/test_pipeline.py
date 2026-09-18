import os

import pytest

import pipeline

requires_api_key = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set; skipping tests that call a real LLM API",
)


def test_ingest_invalid_pdf_returns_none():
    assert pipeline.ingest(b"not a real pdf") is None


def test_ingest_valid_pdf_returns_populated_index_state(sample_pdf_bytes):
    state = pipeline.ingest(sample_pdf_bytes)
    assert state.num_pages == 4
    assert state.num_chunks > 0


@requires_api_key
def test_answer_end_to_end_is_grounded_and_cites_the_right_page(sample_pdf_bytes):
    state = pipeline.ingest(sample_pdf_bytes)
    result = pipeline.answer("What is Jupiter known for?", state)
    assert "jupiter" in result["answer"].lower()
    assert result["sources"]
    assert result["sources"][0]["page"] == 3
