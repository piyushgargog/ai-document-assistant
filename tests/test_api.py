"""Tests for the FastAPI layer (main.py) itself -- separate from the
pipeline-level tests, which already cover retrieval/grounding correctness.
These just verify the HTTP contract: upload, session handling, and error
shapes.

Each test gets its own TestClient (via the `client` fixture) so that one
test's session cookie can never leak into another -- TestClient behaves like
a real browser session and persists cookies across requests made on the same
instance."""

import os

import pytest
from fastapi.testclient import TestClient

from main import app

requires_api_key = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="LLM_API_KEY not set; skipping tests that call a real LLM API",
)


@pytest.fixture
def client():
    return TestClient(app)


def test_index_page_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Document Assistant" in response.text


def test_ingest_rejects_non_pdf(client):
    response = client.post("/api/ingest", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 400
    assert "PDF" in response.json()["error"]


def test_ingest_valid_pdf_returns_session_cookie(client, sample_pdf_bytes):
    response = client.post("/api/ingest", files={"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")})
    assert response.status_code == 200
    body = response.json()
    assert body["num_pages"] == 4
    assert body["num_chunks"] > 0
    assert "session_id" in response.cookies


def test_ask_without_a_session_returns_400(client):
    response = client.post("/api/ask", json={"question": "anything?"})
    assert response.status_code == 400
    assert "No document is loaded" in response.json()["error"]


def test_ask_empty_question_rejected(client, sample_pdf_bytes):
    client.post("/api/ingest", files={"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")})
    response = client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 400


@requires_api_key
def test_ask_end_to_end_after_ingest(client, sample_pdf_bytes):
    client.post("/api/ingest", files={"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")})
    response = client.post("/api/ask", json={"question": "What is Jupiter known for?"})
    assert response.status_code == 200
    body = response.json()
    assert "jupiter" in body["answer"].lower()
    assert body["sources"][0]["page"] == 3


def test_remove_clears_the_session(client, sample_pdf_bytes):
    client.post("/api/ingest", files={"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")})
    client.post("/api/remove")
    response = client.post("/api/ask", json={"question": "anything?"})
    assert response.status_code == 400
