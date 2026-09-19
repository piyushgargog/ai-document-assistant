# Security Policy

## Supported versions

This is a single-branch project — there are no maintained release
branches or version tags. Only the latest commit on `main` is supported.
Security fixes, if needed, will land there.

## What this project already does

For context before reporting an issue, see the "Security notes" section of
`README.md`. In short:

- Retrieved document passages are fenced in the LLM prompt and declared
  untrusted data, so instructions embedded in an uploaded document should not
  be obeyed as instructions (verified against injection payloads — see
  `DECISIONS.md`).
- The LLM API key is read only from the environment (`LLM_API_KEY`), never
  logged, rendered, or committed. `.env` is gitignored; only `.env.example`
  (placeholders) is tracked.
- Uploads are capped at 25MB and questions at 1000 characters.
- Document text is rendered literally in the UI, never as markdown or HTML.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security vulnerability.

GitHub's private vulnerability reporting is not currently enabled on this
repository, so please report privately by contacting one of the maintainers
directly via GitHub —
[@piyushgargog](https://github.com/piyushgargog) or
[@vaibhavparmarog](https://github.com/vaibhavparmarog) — instead of filing a
public issue.

Please include:
- A description of the issue and its potential impact.
- Steps to reproduce, or a minimal example (a crafted PDF or prompt, for
  example — not real personal data).
- Which part of the app is affected (ingestion, retrieval, the LLM call, the
  UI, etc.).

## Scope

In scope: this application's own code — prompt construction and grounding,
handling of uploaded files, secret handling, the FastAPI backend
(`main.py`), and the frontend (`static/`).

Out of scope: the underlying third-party LLM provider's model behavior or
infrastructure (e.g. Groq, OpenAI, or any other OpenAI-compatible endpoint
you configure). Report those directly to the provider.

## Response expectations

This is a small project maintained in spare time — there's no guaranteed
response time or SLA, but security reports will be prioritized over feature
requests and general bugs.
