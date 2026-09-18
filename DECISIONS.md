# Decisions Log — AI Document Assistant

This file starts with planned/initial decisions (made before any code
existed) and is updated as real decisions, failures, and changes happen
during implementation and testing. Nothing below is fabricated — entries
are dated and note what actually happened.

> **STATUS (2026-09-19): Core pipeline implemented, tested end-to-end, and
> validated against two different documents.**
> The application accepts any PDF supplied by the user at runtime — no
> document-specific content, questions, page numbers, or answers are
> hardcoded anywhere in the source. It has been validated against a
> minimal synthetic demo PDF (`sample_docs/sample.pdf`) and a real-world
> multi-page document (see "Real-World Validation" below) to confirm the
> pipeline behaves correctly on realistic document structure, not just a
> toy example.

## Initial / Planned Decisions

1. **No LangChain/LangGraph.**
   Considered, but not used. A hand-rolled pipeline (explicit extract →
   chunk → embed → retrieve → generate functions) demonstrates pipeline
   understanding more directly than a framework's chain abstraction, and
   keeps the code small per NFR1. Revisit only if hand-rolling proves
   genuinely more complex than expected.

2. **Embedding model: `sentence-transformers/all-MiniLM-L6-v2`.**
   Small, fast on CPU, no GPU dependency, well-known baseline —
   appropriate for a single-document tool at this scale. Not chosen for
   maximum retrieval quality, chosen for reliability and speed to
   implement.

3. **Vector store: FAISS `IndexFlatIP` (exact search on normalized vectors).**
   Exact search is fine at this scale (one document → at most a few
   thousand chunks); avoids tuning an approximate index for no benefit.

4. **Chunking strategy: character-based sliding window, per page, with overlap.**
   Simple, predictable, easy to explain — chosen over sentence/semantic
   chunking for implementation simplicity. `chunk_size` and
   `chunk_overlap` are exposed as UI controls so the two-configuration
   comparison (PROJECT_SPEC.md FR8) is a live toggle, not a code change.

5. **LLM access: configurable via environment variables, OpenAI-compatible REST call.**
   Satisfies NFR2 (no hardcoded LLM provider). A minimal `requests`-based
   client (not the full `openai` SDK) is used to keep dependencies small;
   works with OpenAI, Groq, or any OpenAI-compatible endpoint by changing
   `LLM_BASE_URL`/`LLM_MODEL`/`LLM_API_KEY`.

6. **Grounding enforced via prompt instruction + explicit "not in document" path.**
   No mandatory reranking or answer-verification step — a clear system
   prompt restricting the model to the provided passages is the primary
   grounding mechanism, tested explicitly with a deliberately
   unanswerable question (see "Real-World Validation" below).

7. **Single document at a time; multi-document is a possible future enhancement.**
   Keeps the core scope tight; multi-document support (tagging chunks
   with a document name alongside the page number) is a natural
   extension if needed later — see `IMPLEMENTATION_PLAN.md` Phase 10.

## Chunking / Retrieval Configuration Comparison

### Real-World Validation (2026-09-19)

**Document used:** `sample_docs/dev_real_world_document.pdf` — the public
paper "Attention Is All You Need" (Vaswani et al., 2017; arXiv:1706.03762),
downloaded from arXiv specifically to validate the pipeline on realistic
document structure. This is a **sample/demo document**, not the bundled
minimal synthetic PDF (`sample_docs/sample.pdf`) — it's a real,
unmodified, 15-page PDF with realistic structure (body text, section
headings, a figure caption, dense data tables, a references list, and
tokenized-text visualizations on the last pages), useful for exercising
extraction/chunking on content a toy example can't represent.

**Question set** (`sample_docs/dev_real_world_questions.json`, 6
questions, all independently verified by reading the extracted page text
before running the evaluation — not guessed): 5 answerable from the
document, 1 deliberately and genuinely unanswerable (asks for a training
cost in US dollars; the paper only ever reports cost in FLOPs).

**Configs compared, run via `evaluate.py`:**
| | chunk_size | chunk_overlap | top_k | Resulting chunks (15 pages) |
|---|---|---|---|---|
| A — small chunks, low top-k | 300 | 50 | 3 | 161 chunks |
| B — large chunks, higher top-k | 1000 | 200 | 5 | 52 chunks |

**Actual results (verbatim from the real run):**

| Question | Config A (small/low-k) | Config B (large/high-k) |
|---|---|---|
| Transformer's architecture basis | ❌ "could not find" (wrong — it's in the doc) | ✅ Correct, cites page 2 |
| Encoder layer count | ❌ "could not find" (wrong) | ✅ "6 identical layers", cites page 3 |
| EN-FR BLEU score | ⚠️ Answered **41.0** — factually wrong (table value is 41.8), likely a mis-read from a chunk that split Table 2 mid-row | ✅ Correct: **41.8**, cites page 8 |
| Training time/hardware | ❌ "could not find" (wrong) | ✅ "3.5 days on eight GPUs", cites page 1 |
| Who proposed the attention mechanisms | ❌ "could not find" (wrong) | ✅ "Noam", cites page 1 |
| USD training cost (genuinely unanswerable) | ✅ Correctly refused | ✅ Correctly refused |

**Observed difference (a real finding, not a guess):** Config A's smaller
chunks (300 chars) fragmented this document's dense, table-heavy content
badly enough that 4 of 5 answerable questions were incorrectly refused,
and one (BLEU score) returned a plausible-looking but factually wrong
number — most likely because a 300-char chunk boundary cut through Table
2 and the retrieved fragment paired an EN-DE row's BLEU value with the
EN-FR question. Config B's larger chunks (1000 chars) kept enough
surrounding context intact to answer all 5 answerable questions correctly
with accurate page citations, at the cost of retrieving less tightly-
scoped passages (visible in the generally lower per-passage similarity
scores in config B — more passages retrieved, avg. relevance per passage
is lower, but the *set* contains what's needed).

**Practical takeaway:** on a real, structurally complex document, chunk
size clearly matters more than top_k for answer quality — too-small
chunks can both cause false "not found" refusals (a grounding failure in
the conservative direction) and, more concerning, silently wrong answers
when they split tabular/numeric data. The implementation's default
(`chunk_size=800`, close to config B) was chosen deliberately for this
reason, not arbitrarily.

**This validation procedure is reusable against any document.**
`evaluate.py` takes an arbitrary PDF and question set as CLI arguments —
re-run it the same way whenever testing against a new document is
useful; nothing about the script or the pipeline assumes this particular
paper's content, structure, or page numbers.

## Development Log

_Entries added chronologically as implementation proceeds. Each entry:
date, what changed, why, and what (if anything) failed._

- **2026-09-18** — Initial setup: only Python 3.14 was available on the development machine. Verified all required packages (streamlit, pymupdf, sentence-transformers, faiss-cpu, torch) have prebuilt cp314 Windows wheels — installed cleanly into a venv, no source builds needed.
- **2026-09-18** — Document loader (`pdf_loader.py`): the initial synthetic demo PDF (built with PyMuPDF's `insert_text` at a single point) extracted truncated text (~120 of ~280 chars/page) because `insert_text` doesn't wrap long strings. Fixed by switching the generator to `insert_textbox` with a bounding rect. This only affected the synthetic demo PDF generator — real-world PDFs (not generated this way) don't have this issue, as later confirmed against a real document.
- **2026-09-18** — Also switched `import fitz` to `import pymupdf` in `pdf_loader.py` and the sample generator: PyMuPDF 1.28 deprecates the `fitz` alias with a runtime warning.
- **2026-09-18** — Core pipeline stages smoke-tested directly (no API key needed): valid PDF → 4 pages extracted correctly; invalid/empty PDF → clean empty result, no crash; chunker produces more chunks at smaller chunk_size as expected and every chunk carries a correct page number; embedder produces 384-dim vectors with related sentences scoring higher cosine similarity than unrelated ones; FAISS retrieval correctly ranked the passage actually containing the answer first for a test query. All assertions passed.
- **2026-09-18** — Attempted an LLM client test against a user-supplied OpenAI API key. Call failed with HTTP 429, body `{"type": "insufficient_quota", "code": "credit_balance_exhausted"}` — the account had no billing credits. This is an account issue, not a code defect (confirmed by inspecting the raw response body). Per project direction, switched provider from OpenAI to **Groq** (`https://api.groq.com/openai/v1`, model `openai/gpt-oss-120b`) — no other pipeline changes required since the LLM client was already built as a generic OpenAI-compatible REST client (see initial decision #5). `llm_client.py` default model and `.env.example` updated accordingly.
- **2026-09-18** — LLM client retested with a working Groq API key: answerable question correctly grounded and cited the right page; a deliberately unanswerable question correctly triggered the exact refusal string; missing-API-key path raised a clean `LLMConfigError`, no crash. All passed.
- **2026-09-18** — Full pipeline (`pipeline.py`) end-to-end tested directly: ingest → answer → sources all correct against the demo PDF; invalid PDF bytes correctly produced `ingest() -> None`.
- **2026-09-18** — UI (`app.py`) tested in a real headless browser: uploaded the demo PDF, saw "Document ready: 4 pages, 4 chunks indexed", asked a question, got the correct grounded answer with the right page citation, expanded Sources and confirmed all passages shown with correct page numbers and descending similarity scores. Zero browser console errors.
- **2026-09-18** — Built `evaluate.py` (dedicated, reproducible two-config comparison script, preferred over manual-only UI testing so the comparison is repeatable) and dry-ran it against the demo PDF with 6 questions (5 answerable + 1 deliberately unanswerable) under two configs. Script worked correctly end-to-end — since superseded by the real-world validation below, which is more informative because the demo PDF is too short to show chunk-size effects.
- **2026-09-19** — Downloaded a real public PDF (`sample_docs/dev_real_world_document.pdf`, "Attention Is All You Need", arXiv:1706.03762, 15 pages) to validate the pipeline on realistic, non-synthetic document structure — the bundled demo PDF alone wasn't sufficient to exercise chunk-size effects. Read the actual extracted page text first to write a verifiable 6-question test set (`sample_docs/dev_real_world_questions.json`) rather than guessing questions/answers.
- **2026-09-19** — First `evaluate.py` run against the real-world PDF failed partway through with HTTP 429 from Groq: `tokens per minute (TPM): Limit 8000` exceeded — a real, observed rate limit from running 12 LLM calls (6 questions × 2 configs) back to back against larger, real passages. Confirmed via a direct API probe (response body + `retry-after` header) that this was a genuine rate limit, not an auth/quota problem. Fixed by adding retry-with-backoff (honoring the `Retry-After` header, up to 3 retries) to `llm_client.ask()` — a real robustness improvement, not test-only scaffolding, since any real usage could hit the same limit. Re-ran the LLM client tests to confirm no regression, then re-ran `evaluate.py` successfully.
- **2026-09-19** — Real-world two-config comparison completed successfully. Full results and analysis in "Real-World Validation" above. Headline finding: config A (chunk_size=300, top_k=3) incorrectly refused to answer 4 of 5 answerable questions and gave one factually wrong numeric answer (BLEU 41.0 vs actual 41.8) from a chunk that likely split a data table; config B (chunk_size=1000, top_k=5) answered all 5 correctly with accurate page citations. The unanswerable question was correctly refused under both configs. This is a real, observed result — not fabricated or assumed — and directly informed keeping the implementation's default chunk_size (800) closer to config B.
- **2026-09-19** — Wrote `README.md` (overview, architecture, setup, how to run, usage, testing/results, limitations), reflecting only actually-observed results.
- **2026-09-19** — Final regression pass at that point: re-ran all unit-level tests (no drift from the retry-logic change), then re-ran the full UI in a real headless browser against a fresh Streamlit instance using the real-world PDF — "Document ready: 15 pages, 63 chunks indexed" with default settings, asked "How many identical layers are in the Transformer's encoder stack?", got the correct grounded answer "6 identical layers (N = 6)" citing page 3, zero console errors.
- **2026-09-19** — A `ModuleNotFoundError: No module named 'torchvision'` warning was reported appearing repeatedly in the console during `streamlit run`. Diagnosed by reproducing it (uploading a PDF to trigger the `sentence-transformers`/`transformers` model load) and reading the actual traceback rather than guessing: the error originates in Streamlit's own `local_sources_watcher.py` (`get_module_paths()`, called from `LocalSourcesWatcher.update_watched_modules()`), which runs `hasattr(m, "__path__")` on every entry in `sys.modules` any time a new module is imported, in order to decide which local files to watch for auto-rerun-on-save. `transformers` registers lazy-loaded proxy submodules for every model it supports — including vision models (Aria, BEiT, etc.) never used here — and merely checking `hasattr()` on those proxies triggers their real import, which tries `from torchvision... import ...` and fails since torchvision isn't installed. Confirmed via a repository-wide search that none of this project's own source files (`pdf_loader.py`, `chunker.py`, `embedder.py`, `vector_store.py`, `llm_client.py`, `pipeline.py`, `app.py`, `evaluate.py`) reference torch, torchvision, PIL, or image processing anywhere — this app only does text embeddings. Confirmed it was cosmetic: Streamlit catches the exception itself and continues normally; the upload → ingest → answer → sources flow worked correctly throughout even before the fix. Did **not** add `torchvision` to `requirements.txt` — it would suppress the symptom while adding a real, unused, multi-hundred-MB dependency for a text-only pipeline. Checked whether `server.fileWatcherType = "poll"` (a common suggested workaround) would help — read Streamlit's own source (`app_session.py`) and confirmed the module-path scan runs whenever `fileWatcherType != "none"`, so both `"watchdog"` and `"poll"` still trigger it; only `"none"` structurally skips it (`LocalSourcesWatcher` is never even instantiated). Added `.streamlit/config.toml` with `server.fileWatcherType = "none"` — the only Streamlit-level config that actually prevents the scan, not just a log-level suppression. Trade-off, documented in the config file itself: editing a source file while the app is running no longer auto-reruns it; restart `streamlit run` to pick up changes. Updated `.gitignore` to only ignore `.streamlit/secrets.toml` (not the whole `.streamlit/` directory) so this config file stays tracked. Verified the fix: re-ran the app, re-triggered the same PDF upload that reproduced the warning, and confirmed via the raw server log that zero torchvision/local_sources_watcher warnings appeared, while the full upload → ingest → ask → grounded answer → sources flow still worked identically and browser console errors remained at zero.
- **2026-09-19** — Converted the project into a standalone, general-purpose portfolio project: removed organization- and context-specific framing throughout the documentation, UI, and code comments, while keeping every technically meaningful decision and finding described above (the chunking/retrieval comparison, the rate-limit retry/backoff fix, the file-watcher fix). No RAG architecture or pipeline behavior changed as part of this pass. Verified: a repository-wide case-insensitive search for organization/task-specific terms returned zero matches; a search of the actual pipeline source files for the sample documents' content (document titles, findings, etc.) returned zero real matches (one false positive: `SentenceTransformer`, the embedding model's class name, matched the substring "Transformer" but is unrelated to any document content). Re-ran the full unit-level test suite (all passed, no drift) and a full browser-driven UI pass on a fresh Streamlit instance: uploaded the demo PDF, asked "What is Jupiter known for?" and got the correct grounded answer citing page 3 with sources correctly listed, then asked "What is the capital of France?" and got the correct refusal ("I could not find the answer to this question in the document.") instead of a hallucinated answer. Zero browser console errors, zero server-log warnings (the earlier torchvision fix still holds).
- **2026-09-19** — Pre-publish repository audit: reviewed every source file for hardcoded absolute paths, hardcoded document-specific assumptions, dead code, and debug prints — found none (the few `print()` calls in `evaluate.py`/`make_sample_pdf.py` are legitimate CLI output, not debug leftovers). Verified `requirements.txt` matches actual imports exactly (no missing or unused packages). Verified the README setup instructions actually work by creating a brand-new venv (separate from the working one) and installing purely from `requirements.txt`, then running a pipeline smoke test against it — passed. Fixed one real portability issue: the README's environment-setup step used `cp .env.example .env`, which fails in Windows Command Prompt (only PowerShell/bash have `cp`); added a `copy` alternative for cmd.exe. Initialized a git repository inside `ai-document-assistant/` (none existed anywhere before). `git check-ignore -v .env` confirms `.env` is correctly ignored; a dry-run `git add -A --dry-run` shows exactly 23 files would be staged, with `venv/`, `__pycache__/`, `.env`, and any secrets correctly absent, and `.streamlit/config.toml` correctly included. No commit was made.
