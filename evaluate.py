"""Reproducible comparison of two chunking/retrieval configurations.

Runs a fixed question set against the same document under two named
configurations and writes a Markdown report comparing answers and sources
side by side. This is a script rather than only manual UI clicking, so
the comparison (PROJECT_SPEC.md FR8) can be re-run identically against
any document at any time.

Usage (bundled minimal demo document, for exercising this script itself):
    python evaluate.py --pdf sample_docs/sample.pdf --questions sample_docs/dev_eval_questions.json

Usage (any document + question set):
    python evaluate.py --pdf <document.pdf> --questions <questions.json> --output report.md

`<questions.json>` is just a JSON file containing a list of question
strings — nothing about this script assumes a particular document's
content, structure, or page numbers.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass

from dotenv import load_dotenv

import pipeline
from llm_client import LLMConfigError, LLMRequestError

load_dotenv()


@dataclass
class Config:
    name: str
    chunk_size: int
    chunk_overlap: int
    top_k: int


CONFIG_A = Config(name="A - small chunks, low top-k", chunk_size=300, chunk_overlap=50, top_k=3)
CONFIG_B = Config(name="B - large chunks, higher top-k", chunk_size=1000, chunk_overlap=200, top_k=5)


def run_config(pdf_bytes: bytes, config: Config, questions: list[str], delay: float = 0.0) -> dict:
    state = pipeline.ingest(pdf_bytes, chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)
    if state is None:
        return {"config": config, "error": "ingest failed: no extractable text in PDF"}

    results = []
    for i, q in enumerate(questions):
        if delay and i:
            time.sleep(delay)
        try:
            result = pipeline.answer(q, state, top_k=config.top_k)
            answer_text, sources = result["answer"], result["sources"]
        except LLMRequestError as exc:
            # One rate-limited or failed question shouldn't discard the whole run.
            answer_text, sources = f"[LLM request failed: {exc}]", []
        results.append({"question": q, "answer": answer_text, "sources": sources})
    return {
        "config": config,
        "num_pages": state.num_pages,
        "num_chunks": state.num_chunks,
        "results": results,
    }


def format_report(pdf_path: str, run_a: dict, run_b: dict) -> str:
    lines = ["# Chunking/Retrieval Configuration Comparison\n", f"Document: `{pdf_path}`\n"]

    for run in (run_a, run_b):
        cfg = run["config"]
        lines.append(
            f"## {cfg.name}\n"
            f"chunk_size={cfg.chunk_size}, chunk_overlap={cfg.chunk_overlap}, top_k={cfg.top_k}\n"
        )
        if "error" in run:
            lines.append(f"**ERROR: {run['error']}**\n")
            continue
        lines.append(f"Indexed: {run['num_pages']} pages -> {run['num_chunks']} chunks.\n")

    lines.append("## Per-question comparison\n")
    for qa_a, qa_b in zip(run_a.get("results", []), run_b.get("results", [])):
        q = qa_a["question"]
        lines.append(f"### Q: {q}\n")
        lines.append(f"**{run_a['config'].name}**")
        lines.append(f"- Answer: {qa_a['answer']}")
        src_a = ", ".join(f"p{s['page']}({s['score']:.2f})" for s in qa_a["sources"])
        lines.append(f"- Sources: {src_a or '(none)'}\n")

        lines.append(f"**{run_b['config'].name}**")
        lines.append(f"- Answer: {qa_b['answer']}")
        src_b = ", ".join(f"p{s['page']}({s['score']:.2f})" for s in qa_b["sources"])
        lines.append(f"- Sources: {src_b or '(none)'}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Path to the PDF to evaluate")
    parser.add_argument("--questions", required=True, help="Path to a JSON file: a list of question strings")
    parser.add_argument("--output", default=None, help="Optional path to write the Markdown report")
    parser.add_argument(
        "--delay",
        type=float,
        default=8.0,
        help=(
            "Seconds to pause between questions. Batch runs can otherwise trip a "
            "provider's tokens-per-minute limit; set 0 to disable."
        ),
    )
    args = parser.parse_args()

    with open(args.pdf, "rb") as f:
        pdf_bytes = f.read()
    with open(args.questions, "r", encoding="utf-8") as f:
        questions = json.load(f)

    try:
        print(f"Running config A ({CONFIG_A.name})...")
        run_a = run_config(pdf_bytes, CONFIG_A, questions, delay=args.delay)
        print(f"Running config B ({CONFIG_B.name})...")
        run_b = run_config(pdf_bytes, CONFIG_B, questions, delay=args.delay)
    except LLMConfigError as exc:
        print(f"Cannot run: {exc}", file=sys.stderr)
        return 1

    report = format_report(args.pdf, run_a, run_b)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    sys.exit(main())
