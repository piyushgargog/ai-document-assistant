# AI Document Assistant

A Retrieval-Augmented Generation (RAG) tool that answers questions about
any PDF you upload — grounded strictly in that document's content, with
the exact source page shown for every answer.

## What it does

Upload a PDF, ask a question in plain language, and get back an answer
built only from the parts of the document that are actually relevant —
along with the page number(s) and passage text the answer came from. If
the document doesn't contain the answer, the assistant says so instead
of guessing.

## Problem it solves

Reading a long document to find one answer is slow, and keyword search
doesn't handle paraphrased questions. A plain LLM call without the
document, on the other hand, will confidently answer with information
that isn't actually in the source (hallucination). This project combines
retrieval (find the relevant passages) with generation (answer from only
those passages) so answers stay traceable back to the source text.

## Key features

- Upload any PDF and ask questions about it — no document-specific setup.
- Chat-style interface that keeps the conversation visible for the
  current session, so you can work through a document question by
  question.
- Page-aware text extraction, so every retrieved passage keeps its
  source page number.
- Answers are grounded: the LLM is instructed to answer only from
  retrieved passages, and to say so explicitly when they don't contain
  the answer.
- Every answer carries its own sources panel showing the supporting page
  number(s), similarity scores, and passage text, so you can verify it
  against the original document.
- Retrieved document text is treated as untrusted data: it is fenced in
  the prompt and the model is instructed never to follow instructions
  embedded in a document (see [Security](#security-notes) below).
- Chunk size, chunk overlap, and retrieval top-k are configurable
  (tucked into an "Advanced settings" panel so the default UI stays
  simple) — chunking and retrieval settings measurably affect answer
  quality (see [Evaluation methodology](#evaluation-methodology) below).
- Works with any OpenAI-compatible LLM API (OpenAI, Groq, or a local
  compatible endpoint) via environment variables — no vendor lock-in.

## Architecture / RAG pipeline

A single-process Streamlit app implementing RAG as explicit,
individually-inspectable steps rather than a framework's black-box
chain — no LangChain/LangGraph (see `DECISIONS.md` for why).

```
PDF upload
   │  PyMuPDF (page-aware extraction)
   ▼
[(page_num, page_text), ...]
   │  chunker.py (configurable size / overlap)
   ▼
[{text, page}, ...]  ──► sentence-transformers (all-MiniLM-L6-v2) ──► embeddings
   │                                                                      │
   │                                                                      ▼
   │                                                          FAISS IndexFlatIP
   │
question ──► embed ──► FAISS similarity search ──► top-k {text, page, score}
                                                          │
                                                          ▼
                                prompt = system instruction + passages + question
                                                          │
                                                          ▼
                                    LLM (any OpenAI-compatible API, via env vars)
                                                          │
                                                          ▼
                                     answer text + source pages/passages
                                                          │
                                                          ▼
                                            Streamlit renders both
```

| Component | File | Tech |
|---|---|---|
| PDF loader | `pdf_loader.py` | PyMuPDF |
| Chunker | `chunker.py` | plain Python, character sliding window |
| Embedder | `embedder.py` | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector store | `vector_store.py` | FAISS `IndexFlatIP` |
| LLM client | `llm_client.py` | `requests`, OpenAI-compatible REST |
| Orchestration | `pipeline.py` | ties the above together |
| UI | `app.py` | Streamlit |
| Evaluation | `evaluate.py` | reproducible two-config comparison script |

Full design rationale is in `PROJECT_SPEC.md`, `ARCHITECTURE.md`, and
`IMPLEMENTATION_PLAN.md`. Every real engineering decision, failure, and
test result encountered while building this is logged chronologically in
`DECISIONS.md` — nothing there is fabricated.

## Technology stack

- **Python**
- **Streamlit** — UI, no frontend build step
- **PyMuPDF** — page-aware PDF text extraction
- **sentence-transformers** (`all-MiniLM-L6-v2`) — text embeddings
- **FAISS** — vector similarity search
- Any **OpenAI-compatible LLM API** (OpenAI, Groq, etc.) via a minimal
  `requests`-based client — no heavyweight SDK or agent framework

## How the pipeline works

1. **Ingestion (once per uploaded document):** extract text per page,
   split each page's text into overlapping chunks (keeping track of
   which page each chunk came from), embed all chunks, and build a FAISS
   index over the embeddings.
2. **Query (once per question):** embed the question with the same
   model, retrieve the most similar chunks from the index, and build a
   prompt containing only those chunks (each labeled with its page
   number) plus an instruction to answer strictly from them — or say the
   document doesn't contain the answer.
3. **Response:** the LLM's answer is shown together with the retrieved
   passages and their page numbers, so the answer can always be checked
   against the source.

## Installation

Requires Python 3.10+ (developed and tested on Python 3.14).

```bash
git clone <this-repository-url>
cd ai-document-assistant
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Environment configuration

Copy `.env.example` to `.env` and fill in your LLM API key:

```bash
# Windows (Command Prompt)
copy .env.example .env
# Windows (PowerShell) / macOS / Linux
cp .env.example .env
```

```
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

Any OpenAI-compatible chat completions endpoint works — change
`LLM_BASE_URL`/`LLM_MODEL` to use OpenAI or another compatible provider
instead of Groq. `.env` is gitignored; never commit real API keys.

## How to run

```bash
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`.

## Usage

1. Upload a PDF in the sidebar (25MB limit).
2. Wait for indexing to finish — the sidebar then shows a document card
   with the filename, page count, chunk count, and a **Ready** badge.
3. Ask a question in the chat box at the bottom and press Enter.
4. Read the answer, then open the **Sources** panel attached to that
   answer to see exactly which page(s) and passage(s) it came from, with
   similarity scores.
5. Keep asking follow-up questions — the conversation stays visible for
   the session. Each question is answered independently from the
   document (previous turns are not fed back into the model).
6. Use **Remove document** in the sidebar to clear the document and the
   conversation, then upload a different PDF.
7. (Optional) Open **Advanced settings** in the sidebar to change chunk
   size, chunk overlap, or top-k — the document is re-indexed
   automatically when chunking settings change.

If the document contains no extractable text (empty, corrupt,
password-protected, or image-only without OCR), or the LLM API key is
missing/invalid, the app shows a clear error message instead of
crashing.

### How source citations work

Every retrieved passage is tagged with the page number it came from
during chunking (`chunker.py`). When the LLM answers, the app shows the
top-k retrieved passages alongside that specific answer — independent of
whether the LLM explicitly cites a page in its own text — so you can
always see which parts of the document the answer is (or isn't) actually
grounded in, along with a similarity score for each. Passage text is
rendered literally, never as markdown, so document content cannot inject
formatting into the interface.

## Security notes

This is a document QA tool that feeds untrusted file content into an
LLM, so a few things are handled deliberately:

- **Indirect prompt injection**: retrieved passages are fenced inside
  explicit delimiters and the system prompt instructs the model to treat
  them as quoted data, never as instructions. Verified against a test
  PDF containing injected "ignore all previous instructions" and
  system-prompt-exfiltration payloads — the model reported the injected
  text as document content and refused the exfiltration attempt instead
  of obeying either.
- **Secrets**: the API key is read only from the environment
  (`LLM_API_KEY`). It is never logged, rendered, or committed; `.env` is
  gitignored and only `.env.example` (placeholders) is tracked.
- **Resource limits**: uploads are capped at 25MB and questions at 1000
  characters, since each upload is held in memory and embedded.
- **Rendering**: document text is displayed with Streamlit's literal
  text rendering (no raw HTML, no markdown interpretation).

## Evaluation methodology

Every test result described here was actually run; none is assumed or
fabricated — see `DECISIONS.md` for the full chronological log.

### Unit-level testing
Each pipeline stage was tested directly (no UI) before integration: PDF
extraction on a valid and an invalid/empty PDF, chunking (correct page
attribution, more chunks at smaller `chunk_size`), embeddings (384-dim
vectors, related text scores higher similarity than unrelated text),
FAISS retrieval (correct top match for a known query), the LLM client
(grounded answer, correct refusal on an unanswerable question, clean
error on a missing API key), and the full pipeline end-to-end.

### UI testing
Driven in a real headless browser against the running Streamlit app:
upload → ingest → ask → answer with correct source page → expand sources
→ all passages shown with correct pages and descending similarity
scores, with zero browser console errors.

### Real-world validation
A minimal synthetic PDF is bundled (`sample_docs/sample.pdf`) purely as
a quick demo/smoke-test document. To validate the pipeline on realistic,
non-synthetic document structure, a public real-world PDF — the paper
"Attention Is All You Need" (Vaswani et al., 2017), 15 pages of real
body text, section headings, data tables, and references — was used for
a more thorough evaluation:

- **Question set:** 6 questions independently verified against the
  extracted text before running the test — 5 answerable, 1 genuinely
  unanswerable from the document (asks for a training cost in US
  dollars; the paper only ever reports cost in FLOPs).
- **Two configurations compared** via `evaluate.py`:
  - Config A: chunk_size=300, chunk_overlap=50, top_k=3
  - Config B: chunk_size=1000, chunk_overlap=200, top_k=5

**Result:** Config A incorrectly refused to answer 4 of the 5 answerable
questions, and gave one factually wrong numeric answer (BLEU 41.0
instead of the correct 41.8) — most likely because its 300-character
chunks split a dense results table mid-row. Config B answered all 5
correctly with accurate page citations. Both configs correctly refused
the genuinely unanswerable question. Full per-question results and
analysis are in `DECISIONS.md`. This is why the implementation's default
`chunk_size` (800) is close to config B, not the smaller value.

To run this comparison yourself against any PDF and question set:

```bash
python evaluate.py --pdf <path-to-pdf> --questions <path-to-questions.json> --output results.md
```

where `<path-to-questions.json>` is a JSON file containing a list of
question strings.

## Known limitations

- Single document per session (multi-document support would be a
  natural extension — see `IMPLEMENTATION_PLAN.md`).
- The conversation is displayed for the session but is not used as
  context: each question is answered independently from the document, so
  follow-ups like "and what about that one?" won't resolve against the
  previous turn.
- Session state is per-browser-session and resets on reload.
- Uploads are capped at 25MB, and scanned/image-only PDFs with no
  embedded text layer will not extract any text (no OCR step).
- Chunking is character-based, not sentence/semantic-boundary aware —
  simple and predictable, but can occasionally split content (e.g. a
  table row) across a chunk boundary, as observed during evaluation
  above.
- Retrieval quality depends on the embedding model
  (`all-MiniLM-L6-v2`) — a small, fast, general-purpose model chosen for
  reliability at this project's scale, not maximum retrieval accuracy.
- LLM API rate limits (e.g. Groq's free-tier tokens-per-minute cap) can
  slow down rapid, repeated evaluation runs; `llm_client.py` retries
  automatically with backoff, but very fast bulk evaluation may still be
  gated by provider limits.

## Possible future improvements

- **Multi-document support** — ingest and query across several
  documents at once, tagging chunks with a document identifier alongside
  the page number.
- **Conversation history** — let follow-up questions build on prior
  turns instead of being answered independently.
- **Document summary** — an optional one-shot summary generated on
  upload, before any question is asked.
- **Smarter chunking** — sentence- or section-boundary-aware chunking
  instead of a fixed character window, to reduce the table-splitting
  failure mode observed in evaluation.
- **Reranking** — a lightweight cross-encoder reranking step over the
  initial retrieval results, for higher-precision passage selection on
  larger documents.
