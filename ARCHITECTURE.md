# Architecture — AI Document Assistant

## Overview

A single-process Streamlit app implementing a classic Retrieval-Augmented
Generation (RAG) pipeline, built from explicit, individually-inspectable
steps rather than a framework's black-box chain. This is a deliberate
design choice (see `DECISIONS.md`): each pipeline stage is a plain
function you can point to and explain, rather than logic hidden behind a
framework's abstraction.

## Components

1. **UI layer** (`app.py`, Streamlit)
   Handles file upload, question input, settings (chunk size / overlap /
   top-k), and renders the answer + source passages.

2. **Document loader** (`pdf_loader.py`)
   Uses PyMuPDF (`fitz`) to open the PDF and extract text page by page.
   Output: a list of `(page_number, page_text)` pairs. Handles empty/invalid
   PDFs by returning an empty list (caught upstream as an error state).

3. **Chunker** (`chunker.py`)
   Splits each page's text into overlapping character-window chunks
   (configurable `chunk_size`, `chunk_overlap`). Each chunk keeps a
   reference to its source page number. Output: list of
   `{"text": ..., "page": ...}` dicts.

4. **Embedder** (`embedder.py`)
   Wraps a `sentence-transformers` model (`all-MiniLM-L6-v2`) to turn chunk
   text and questions into vectors.

5. **Vector store / retriever** (`vector_store.py`)
   Wraps a FAISS `IndexFlatIP` (cosine similarity via normalized vectors).
   Builds the index from chunk embeddings; given a query embedding, returns
   the top-k most similar chunks with their page numbers and similarity
   scores.

6. **LLM client** (`llm_client.py`)
   Thin wrapper around one LLM API, selected and configured entirely via
   environment variables (`LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`) so the
   provider can be swapped without touching code. Builds a strict grounding
   prompt: system instruction + retrieved passages + question, with an
   explicit instruction to say the document doesn't contain the answer if
   the passages don't support one.

7. **Orchestration** (`pipeline.py`)
   Ties the above together: `load → chunk → embed → index` at
   ingestion time, and `embed_query → retrieve → build_prompt → call_llm →
   return(answer, sources)` per question.

## Data Flow

```
PDF file
   │  PyMuPDF
   ▼
[(page_num, page_text), ...]
   │  chunker (size, overlap)
   ▼
[{text, page}, ...]  ──────────────► sentence-transformers ──► chunk embeddings
   │                                                                  │
   │                                                                  ▼
   │                                                         FAISS index (in memory)
   │
User question
   │  sentence-transformers
   ▼
question embedding ──► FAISS similarity search ──► top-k {text, page, score}
                                                          │
                                                          ▼
                                     prompt = system + top-k passages + question
                                                          │
                                                          ▼
                                                     LLM API call
                                                          │
                                                          ▼
                                        answer text  +  source list (page, passage)
                                                          │
                                                          ▼
                                                  Streamlit renders both
```

## RAG Pipeline (detail)

1. **Ingestion (once per uploaded document)**
   - Extract text per page (PyMuPDF).
   - Chunk each page's text with overlap so answers spanning a chunk
     boundary aren't lost.
   - Embed all chunks; build a FAISS index; keep a parallel Python list
     mapping index position → `{text, page}` for lookup after search.

2. **Query (once per question)**
   - Embed the question with the same model (required — mismatched models
     would produce meaningless similarity scores).
   - Retrieve top-k chunks by cosine similarity.
   - Construct a grounding prompt that includes the retrieved passages
     (each labeled with its page number) and instructs the LLM to answer
     **only** from them, and to say so explicitly if they don't contain the
     answer.
   - Call the LLM; return the answer text alongside the source chunks used,
     so the UI can display page/passage provenance independent of whether
     the LLM cites them correctly.

## Technology Choices

| Choice | Why |
|--------|-----|
| **Streamlit** | Fastest way to get a usable, interactive UI for a small tool with no frontend build step. |
| **PyMuPDF (fitz)** | Reliable page-level text extraction, handles most real-world PDFs, fast, no external binary dependency. |
| **sentence-transformers (`all-MiniLM-L6-v2`)** | Small (~80MB), fast on CPU, well-established baseline for semantic similarity — appropriate for a single-document tool at this scale. |
| **FAISS (`IndexFlatIP`)** | Exact (non-approximate) search is fine at this scale (one document, low thousands of chunks at most), simple to reason about, no external service to run. |
| **Configurable LLM API (env vars)** | NFR2 requires no hardcoded provider. A minimal `requests`-based OpenAI-compatible client is the default (works with OpenAI, Groq, or any OpenAI-compatible endpoint by changing `LLM_BASE_URL`), keeping the dependency footprint small. |
| **No LangChain/LangGraph** | Considered but deliberately not used — see `DECISIONS.md`. A hand-rolled pipeline better demonstrates pipeline understanding and keeps the code small and readable (NFR1), which a framework's abstractions would work against at this scale. |

## Chunking / Retrieval Configurability

`chunk_size`, `chunk_overlap`, and `top_k` are exposed as Streamlit sidebar
controls (with sensible defaults) rather than hardcoded, so FR8 (comparing
two configurations) can be done live in the running app and the observed
difference recorded in `DECISIONS.md` during the testing phase.

## Failure Handling

- **Invalid/empty PDF**: loader returns no pages → UI shows an explicit
  error, ingestion is blocked (no empty index built).
- **Missing API key**: LLM client raises a clear configuration error on
  first call, caught by the UI and shown as a message — not a stack trace.
- **No relevant chunks found** (e.g. off-topic question): retrieval still
  returns its top-k (FAISS always returns *something*), but similarity
  scores will be low; the prompt's grounding instruction handles the
  "answer not in document" case at the LLM level — see `DECISIONS.md` for
  the actual evaluation of this behavior against a real document.
