# AI Usage — AI Document Assistant

Honest, running record of how AI assistance (Claude Code) was used while
building this project. Updated as work progresses — not written once at
the end.

## Planning Phase

- Claude Code was used to draft the initial planning documents
  (`PROJECT_SPEC.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`,
  `DECISIONS.md`, this file) from a set of functional requirements the
  user defined up front (single-document PDF QA, page-aware chunking,
  grounded retrieval-augmented answers, source citations, and a
  reproducible two-configuration chunking/retrieval comparison).
- The user directed the workflow (planning before coding, phase
  structure, what stack to use — all specified up front) and reviewed
  each planning document before implementation began.
- Architectural choices (e.g. not using LangChain, model/library
  selection) were proposed by Claude Code with stated reasoning, for the
  user to accept, reject, or change before implementation began.

## Implementation Phase

- All source files (`pdf_loader.py`, `chunker.py`, `embedder.py`,
  `vector_store.py`, `llm_client.py`, `pipeline.py`, `app.py`,
  `evaluate.py`) were drafted by Claude Code directly from the approved
  `PROJECT_SPEC.md`/`ARCHITECTURE.md`/`IMPLEMENTATION_PLAN.md`, then
  actually run and tested (see `DECISIONS.md`'s development log) rather
  than assumed to work.
- The user made two explicit implementation-affecting decisions during
  this phase: (1) keep chunk_size/chunk_overlap/top_k configurable but
  collapse them into an "Advanced settings" expander so the default UI
  stays simple; (2) require a dedicated `evaluate.py` script for the
  two-config comparison instead of relying only on manual UI clicking, so
  the comparison is reproducible.
- The user supplied real API credentials (OpenAI, then Groq after the
  OpenAI key turned out to have no billing credits) directly in chat for
  Claude Code to place into a local, gitignored `.env` file. Keys were
  never printed back, hardcoded into source, or committed.
- No AI-suggested approach has been rejected; the OpenAI→Groq switch was
  caused by an account billing issue, not a design change.

## Testing Phase

- Claude Code selected and downloaded a real public PDF (a well-known
  arXiv paper) to validate the pipeline on realistic document structure
  beyond the bundled minimal demo PDF, read its actual extracted content
  before writing test questions (rather than guessing), and ran a real
  two-configuration comparison via `evaluate.py`. All answers, sources,
  and chunk/config counts recorded in `DECISIONS.md` are the actual
  script output from that run — none were written from assumption.
- Mid-run, the evaluation hit a genuine Groq API rate limit (429, TPM
  exceeded). This was diagnosed with a direct API probe before being
  treated as a bug, then fixed with retry/backoff logic in
  `llm_client.py`. The fix and the reasoning behind it are logged in
  `DECISIONS.md`'s development log, not hidden.
- A later console warning (`ModuleNotFoundError: No module named
  'torchvision'`) was diagnosed the same way: reproduced first, root
  cause traced to Streamlit's own file-watcher code (not this project's
  code), and fixed with a targeted Streamlit config change rather than
  installing an unused dependency to mask the symptom.

## Generalization Pass

- The project was later converted into a standalone, general-purpose
  portfolio project. Claude Code performed a repository-wide audit for
  organization- and context-specific references and removed or reworded
  them across the UI, README, planning docs, and code comments, while
  explicitly preserving every technically meaningful decision and finding
  (the chunking/retrieval comparison results, the rate-limit
  retry/backoff fix, the file-watcher fix) rather than deleting them.
- No RAG architecture, pipeline behavior, or dependency was changed as
  part of this pass — it was a documentation/presentation change,
  verified by re-running the full test suite afterward (see
  `DECISIONS.md`).

## Review and Hardening Pass

- Claude Code ran a project-wide review (architecture, RAG correctness,
  security, PDF handling, state management, UI/UX, deployment,
  dependencies, documentation) and fixed the issues it found. The full
  list, including what was actually broken and how each fix was
  verified, is in `DECISIONS.md`.
- Findings were verified rather than assumed: the `Retry-After` parsing
  fix was unit-tested across nine header forms, the prompt-injection
  defense was tested against a purpose-built malicious PDF, and the
  error-state fix was confirmed in a real browser.
- After hardening the system prompt, the full two-configuration
  evaluation was re-run to confirm the previously documented findings
  were still accurate rather than silently invalidated.

## Autonomous Maintenance Pass

- Claude Code was authorized to act as an autonomous maintainer: inspect
  the repository, fix genuine issues on its own judgment, and document
  what changed, without asking permission for each individual fix.
- It re-read every source file directly rather than relying on earlier
  context, and found three real, previously-unnoticed gaps (unhandled
  exceptions on the ingestion/query paths, a missing-API-key crash in
  `evaluate.py`, a stale README placeholder) — all fixed and tested; see
  `DECISIONS.md` for specifics.
- It also identified that all prior test verification in this project
  existed only as throwaway scripts in a temp directory, never committed
  — a real gap given `CONTRIBUTING.md` itself calls out the missing test
  suite as desirable — and added a genuine, committed `pytest` suite plus
  a credential-free CI workflow to close it, rather than leaving that
  gap unaddressed because it wasn't explicitly requested this time.
- While verifying the new test suite, it caught its own mistake — a
  fixture that silently skipped every LLM-dependent test even with a
  valid key configured, because `.env` wasn't being loaded — rather than
  reporting the misleading "6 skipped" result as if it were success.

## UI/Architecture Migration

- Claude Code was authorized to independently choose and implement a
  replacement for the Streamlit UI, whose mobile experience was the
  motivating problem. It evaluated staying on Streamlit, a full SPA
  framework, and a minimal FastAPI + static-frontend approach, and chose
  the last one; the reasoning is in `DECISIONS.md`, not just the outcome.
- It deliberately left the entire RAG pipeline (`pdf_loader.py` through
  `pipeline.py`) untouched, confirming this was possible before starting
  by checking that `evaluate.py` and the `tests/` suite only import the
  pipeline modules, never the UI layer — so the migration couldn't
  silently change retrieval or grounding behavior.
- It found and fixed three real bugs in its own new code before calling
  the work done: a CSS specificity bug that would have broken the
  document-view's hide/show logic, a chat input that didn't stay pinned
  to the screen bottom with few messages, and a devcontainer config
  (added by the user in an earlier, unrelated commit) that would have
  launched a command referencing a file this migration deleted. None of
  these were requested explicitly — they were caught by actually running
  and looking at the result, not assumed to be fine because the code
  looked reasonable.
- A visual "this doesn't look centered" impression from a screenshot was
  checked against actual computed CSS values before being treated as a
  bug — it wasn't one (the layout was already correct; the impression
  came from a small element in a wide, empty viewport). This is recorded
  so a "found and fixed N issues" summary doesn't imply every impression
  during review turned out to be a real problem.

## Principles followed

- No fabricated test results, decisions, or requirements — ever.
- Every AI-authored planning document is explicitly reviewed against the
  project's actual requirements before implementation proceeds.
- This file is updated alongside the work, not reconstructed after the
  fact.
