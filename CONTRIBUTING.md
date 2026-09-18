# Contributing to AI Document Assistant

Thanks for your interest in this project. It's a personal/portfolio project
maintained by one person in spare time, so please set expectations
accordingly — issues and PRs are welcome, but there's no guaranteed response
time and no dedicated review team.

## Before you start

Read `README.md` for what the app does and `ARCHITECTURE.md` for how the RAG
pipeline is structured. `DECISIONS.md` records the real engineering decisions
made on this project (including things that were tried and rejected, like
LangChain) — worth checking before proposing a significant design change, so
you're not re-litigating something already decided for a documented reason.

## Development setup

```bash
git clone https://github.com/piyushgargog/ai-document-assistant.git
cd ai-document-assistant
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # then fill in LLM_API_KEY
```

Run the app locally with:

```bash
streamlit run app.py
```

## Project structure

Each pipeline stage is its own small module — keep that separation when
making changes rather than merging responsibilities:

| File | Responsibility |
|---|---|
| `pdf_loader.py` | Page-aware PDF text extraction |
| `chunker.py` | Splitting page text into chunks |
| `embedder.py` | Text -> vector embeddings |
| `vector_store.py` | FAISS similarity search |
| `llm_client.py` | LLM API call + grounding prompt |
| `pipeline.py` | Orchestrates the above (ingest / answer) |
| `app.py` | Streamlit UI only |
| `evaluate.py` | Reproducible chunking/retrieval comparison |

The project deliberately avoids heavyweight frameworks (see `DECISIONS.md`
for why LangChain/LangGraph aren't used) in favor of small, explicit,
readable functions. Please keep new dependencies to a minimum, and justify
any addition to the pipeline in the PR description.

## Testing your changes

There's no CI pipeline or automated test suite committed to this repo yet, so
changes need to be verified manually before opening a PR:

- Run `streamlit run app.py`, upload `sample_docs/sample.pdf`, and confirm
  the full flow works: upload, indexing, an answerable question with correct
  source citations, and a clearly unanswerable question.
- If your change touches retrieval, chunking, or the prompt, run
  `evaluate.py` against a document and question set and check the comparison
  report for regressions:
  ```bash
  python evaluate.py --pdf sample_docs/sample.pdf --questions sample_docs/dev_eval_questions.json
  ```
- Never commit `.env`, an API key, or any other secret. `.env` is gitignored
  — if your diff touches it, something is wrong.

A proper automated test suite (e.g. pytest) would be a welcome contribution
in its own right.

## Documentation

If a change affects user-facing behavior, update `README.md`. If it changes
the pipeline or a design decision, update `ARCHITECTURE.md` and add a dated
entry to `DECISIONS.md` describing what changed and why — this project keeps
an honest, real-time decision log rather than reconstructing rationale after
the fact, and PRs are expected to keep that practice going.

## Submitting a pull request

- Use the PR template.
- Keep PRs focused — one concern per PR is easier to review than a large
  mixed change.
- Describe how you tested the change (see above).

## Reporting bugs or requesting features

Use the issue templates. For anything security-related, do **not** open a
public issue — see `SECURITY.md`.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). Please read
it before participating.
