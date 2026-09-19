# Implementation Plan — AI Document Assistant

Each phase should be independently runnable/testable before moving to the
next. Phases 0–7 deliver all core requirements; 8–9 are testing and docs;
optional enhancements (Phase 10) only happen if 0–9 are solid.

> This file describes the original implementation plan, largely followed
> as written for the pipeline (Phases 1–6) and testing (Phase 8). The UI
> (Phase 7) has since been rebuilt twice — first from a plain form into a
> Streamlit chat interface, then from Streamlit into a FastAPI backend
> with a static HTML/CSS/JS frontend — see `DECISIONS.md` for both and
> why. References to `app.py`/`streamlit run` below are historical.

## Phase 0 — Project Setup
- `requirements.txt` (originally streamlit, pymupdf, sentence-transformers, faiss-cpu, requests, python-dotenv, numpy — streamlit was later replaced by fastapi/uvicorn/python-multipart, see `DECISIONS.md`).
- `.env.example` documenting `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.
- Folder skeleton: `app.py`, `pdf_loader.py`, `chunker.py`, `embedder.py`, `vector_store.py`, `llm_client.py`, `pipeline.py`, `tests/` (manual test notes), `sample_docs/`.
- **Test**: `pip install -r requirements.txt` succeeds; `streamlit run app.py` opens a blank page without errors.
- **Depends on**: nothing.

## Phase 1 — Document Loader (`pdf_loader.py`)
- Function: open PDF bytes/path with PyMuPDF, return `[(page_num, text), ...]`.
- Handle empty PDF / zero extractable text as an explicit empty result, not an exception leak.
- **Test**: run against a real multi-page PDF and confirm page count + spot-checked text; run against an empty/corrupt PDF and confirm a clean empty result rather than a crash.
- **Depends on**: Phase 0.

## Phase 2 — Chunker (`chunker.py`)
- Function: given `[(page_num, text), ...]`, `chunk_size`, `chunk_overlap` → `[{"text", "page"}, ...]`.
- Character-based sliding window per page (simple, predictable, easy to explain — appropriate for a small, single-document RAG tool).
- **Test**: unit-check chunk count and overlap behavior on a known string; confirm every chunk carries the correct page number.
- **Depends on**: Phase 1 (consumes its output format).

## Phase 3 — Embedder (`embedder.py`)
- Load `all-MiniLM-L6-v2` once (cached via `st.cache_resource` in the app layer).
- Function: `embed(texts: list[str]) -> np.ndarray`.
- **Test**: embed a few sample sentences, confirm output shape `(n, 384)` and that similar sentences score higher cosine similarity than dissimilar ones (quick manual sanity check).
- **Depends on**: Phase 0 only (independent of chunker).

## Phase 4 — Vector Store (`vector_store.py`)
- Build a FAISS `IndexFlatIP` from normalized chunk embeddings.
- Function: `search(query_embedding, top_k) -> [(chunk_index, score), ...]`, resolved back to `{text, page, score}` via a parallel metadata list.
- **Test**: build an index from a handful of known chunks, run a query whose answer is obviously in one chunk, confirm that chunk ranks first.
- **Depends on**: Phase 2 (chunk format) + Phase 3 (embeddings).

## Phase 5 — LLM Client (`llm_client.py`)
- Minimal OpenAI-compatible chat completion call via `requests`, config from env vars.
- Grounding prompt template: system instruction ("answer only from the provided passages; if they don't contain the answer, say so explicitly") + numbered passages with page labels + question.
- Raise a clear, caught-upstream error if `LLM_API_KEY` is unset.
- **Test**: call with a small fixed context + question with a known answer; call with context that doesn't contain the answer and confirm the model says so; call with the API key unset and confirm a clean error, not a stack trace to the user.
- **Depends on**: Phase 0 only.

## Phase 6 — Pipeline (`pipeline.py`)
- `ingest(pdf_bytes, chunk_size, chunk_overlap) -> index_state`
- `answer(question, index_state, top_k) -> {answer, sources: [{page, text, score}]}`
- Wires Phases 1–5 together.
- **Test**: end-to-end call against a real PDF with a known-answerable question; confirm sources returned match where the answer actually is.
- **Depends on**: Phases 1–5.

## Phase 7 — Streamlit UI (`app.py`)
> Note: this describes the original plan. The UI was later rebuilt as a
> chat interface (message history, per-answer sources popover, sidebar
> document card) — see `DECISIONS.md` for that change and its rationale.
- Upload widget → calls `pipeline.ingest`.
- Sidebar: chunk size, chunk overlap, top-k sliders (defaults + ability to change and re-ingest).
- Question input → calls `pipeline.answer` → renders answer, then an expandable "Sources" section per result showing page number + passage text (+ similarity score).
- Error states surfaced as `st.error(...)`, not raw tracebacks.
- **Test**: manual click-through in browser — upload, ask, see answer + sources; trigger each error state (empty PDF, missing key) and confirm graceful messages.
- **Depends on**: Phase 6.

## Phase 8 — Testing
- Run ≥5 questions against a real document, recorded with actual answers/sources (not fabricated).
- Include ≥1 question intentionally unanswerable from the document; confirm the assistant declines rather than hallucinates.
- Run the same question set under **two** chunking/retrieval configurations (e.g. small chunks/low top-k vs. larger chunks/higher top-k); record observed differences in `DECISIONS.md`.
- Also exercise: invalid/empty PDF, missing API key.
- **Depends on**: Phase 7 (needs the full app running).

## Phase 9 — README + Final Review
- Write `README.md`: overview, architecture summary, setup, how to run, usage, testing/results, limitations.
- Cross-check every mandatory requirement in `PROJECT_SPEC.md` against the actual running app.
- **Depends on**: Phase 8 (results must be real before documenting them).

## Phase 10 — Optional Enhancements (only if 0–9 are complete and solid)
- Multiple documents (extend ingestion to merge multiple sources, tag chunks with doc name + page).
- Conversation history (chat-style message list in Streamlit session state, prior turns optionally included in prompt).
- Short document summary (one extra LLM call over a sample of chunks or full text if small enough).

## Testing Strategy Summary
- Each phase (1–6) gets a quick manual/functional check before moving on — no formal test framework needed at this scope, but checks must actually be run, not assumed.
- Phase 8 is the authoritative test pass against this project's own requirements (`PROJECT_SPEC.md`) and is what gets written up in `DECISIONS.md`/`README.md`.
- No test result is recorded anywhere unless it was actually observed from a real run.
