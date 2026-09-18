"""Phase 5: minimal OpenAI-compatible chat completion client + grounding prompt.

Deliberately not using the `openai` SDK or LangChain — a single `requests`
POST is enough for one chat-completion call, and keeps the dependency
footprint and the amount of "magic" small (see DECISIONS.md).
"""

import os
import time

import requests

MAX_RETRIES = 3

SYSTEM_PROMPT = (
    "You are a document question-answering assistant. Answer the user's "
    "question using ONLY the passages provided below, taken from the "
    "source document. Each passage is labeled with its page number.\n\n"
    "Rules:\n"
    "- If the passages do not contain enough information to answer, "
    'respond exactly with: "I could not find the answer to this question '
    'in the document." Do not guess or use outside knowledge.\n'
    "- When you do answer, be concise and, where useful, mention the page "
    "number(s) your answer comes from.\n"
)


class LLMConfigError(RuntimeError):
    """Raised when required LLM configuration (e.g. API key) is missing."""


class LLMRequestError(RuntimeError):
    """Raised when the LLM API call itself fails."""


def _config():
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise LLMConfigError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add your API key."
        )
    base_url = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")
    return api_key, base_url, model


def build_prompt(question: str, passages: list[dict]) -> str:
    """Build the user-turn content: labeled passages + the question."""
    if not passages:
        passage_block = "(no passages retrieved)"
    else:
        passage_block = "\n\n".join(
            f"[Page {p['page']}] {p['text']}" for p in passages
        )
    return f"Passages:\n{passage_block}\n\nQuestion: {question}"


def ask(question: str, passages: list[dict], timeout: int = 30) -> str:
    """Call the configured LLM with a grounding prompt and return the answer text."""
    api_key, base_url, model = _config()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, passages)},
        ],
        "temperature": 0.0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                f"{base_url}/chat/completions", json=payload, headers=headers, timeout=timeout
            )
            if response.status_code == 429 and attempt < MAX_RETRIES:
                time.sleep(float(response.headers.get("retry-after", 5)))
                continue
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            raise LLMRequestError(f"LLM API call failed: {exc}") from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMRequestError(f"Unexpected LLM API response shape: {data}") from exc
