# Project Specification — AI Document Assistant

This document defines the requirements this project is built to satisfy:
a small, self-contained RAG (Retrieval-Augmented Generation) tool for
asking grounded questions about a single uploaded document.

## Problem

A user has a single document (PDF or text) and wants to ask natural-language
questions about its contents without reading the whole thing. Plain keyword
search doesn't handle paraphrased questions, and a raw LLM call without the
document will hallucinate answers not actually present in the source.

## Objective

Build a document question-answering tool that:
- Ingests one document supplied by the user at runtime.
- Answers user questions using only information retrieved from that document.
- Shows the user exactly which page/passage the answer came from.
- Correctly refuses to answer when the document doesn't contain the answer.

## Scope

### In scope (core requirements)
- Single document upload (PDF, with text fallback).
- Page-aware text extraction and chunking.
- Embedding-based retrieval of relevant passages per question.
- Grounded answer generation (LLM restricted to retrieved context).
- Source page/passage display alongside every answer.
- Manual test set of ≥5 questions, including ≥1 unanswerable-from-document question.
- Two chunking/retrieval configurations compared, with results recorded in `DECISIONS.md`.

### Out of scope for the core build (future enhancements, only after core requirements work)
- Multiple simultaneous documents.
- Conversational context: the UI keeps the session's questions and
  answers visible, but each question is answered independently from the
  document — prior turns are not fed back into the model, so follow-ups
  are not resolved against earlier answers.
- Automatic document summary on load.

### Explicitly not building
- User accounts, persistence across sessions, or a database beyond the in-memory/on-disk FAISS index for the current document.
- Fine-tuning any model.
- Any UI beyond a single Streamlit app.

## Functional Requirements

| ID | Requirement | Rationale |
|----|-------------|--------|
| FR1 | Load one PDF (or .txt) document supplied by the user. | Core input to the whole pipeline. |
| FR2 | Extract text per page and split into searchable chunks, retaining page numbers. | Page-level provenance is required for source citations (FR6). |
| FR3 | Embed chunks and index them for similarity search. | Enables semantic (not just keyword) retrieval. |
| FR4 | Given a question, retrieve the top-k most relevant chunks. | Standard RAG retrieval step. |
| FR5 | Generate an answer using an LLM, constrained to only the retrieved chunks as context. | Grounding — prevents hallucinated answers. |
| FR6 | Display the source page number(s) and/or the exact passage text used for each answer. | Lets the user verify the answer against the original document. |
| FR7 | If no retrieved chunk supports an answer, the assistant must say so rather than guessing. | Grounding failure mode — a conservative refusal beats a confident wrong answer. |
| FR8 | Support switching between at least two chunking/retrieval configurations (e.g. chunk size, overlap, top-k) without code changes. | Chunking/retrieval parameters materially affect answer quality (see DECISIONS.md) and should be easy to experiment with. |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR1 | Code must be small, clean, and readable — this is a portfolio/demonstration project prioritizing clarity over premature production hardening. |
| NFR2 | LLM provider/model/API key must be configurable via environment variables, not hardcoded. |
| NFR3 | The app must run locally via `streamlit run app.py` with a documented setup (`README.md`). |
| NFR4 | The app must degrade gracefully (clear error message, not a crash) when: the API key is missing, the PDF is invalid/empty, or retrieval finds nothing useful. |
| NFR5 | No fabricated test results — all testing in `DECISIONS.md`/README must reflect actual runs. |

## Acceptance Criteria

These are the quality dimensions a document QA/RAG tool should be judged on:

- **Document processing** — PDF loads, text is extracted per page, chunks retain page metadata. Verified with a valid PDF and an invalid/empty PDF.
- **Retrieval quality** — For on-topic questions, retrieved chunks are topically relevant to the question (spot-checked manually across both tested configurations).
- **Grounding** — Answers only use retrieved content; the unanswerable test question produces an explicit "not found in document" style response, not a hallucinated one.
- **Source handling** — Every answer is displayed with its supporting page number(s) and passage text.
- **Understanding of the AI pipeline** — Pipeline stages (extraction → chunking → embedding → retrieval → generation) are implemented as distinct, inspectable, documented steps rather than hidden behind an opaque framework call; `ARCHITECTURE.md` and code comments show this understanding.

## Constraints

- Single document only for the core build (multi-document support is a possible future enhancement).
- Must use: Python, Streamlit, PyMuPDF, sentence-transformers, FAISS, and a configurable LLM API.
- Must actually run and be tested before being called done — no untested claims.
