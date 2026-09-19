"""FastAPI backend for the AI Document Assistant.

Wraps the existing, unchanged RAG pipeline (pdf_loader -> chunker ->
embedder -> vector_store -> llm_client -> pipeline) with a minimal HTTP API
and serves the static frontend from the same origin (so no CORS setup is
needed). Nothing in this file touches retrieval, chunking, embedding, or
prompt logic -- it only adapts the existing pipeline.ingest()/pipeline.answer()
functions to HTTP.
"""

import secrets
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import pipeline
from llm_client import LLMConfigError, LLMRequestError

load_dotenv()

STATIC_DIR = Path(__file__).parent / "static"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB -- unchanged from the previous UI's limit
MAX_QUESTION_CHARS = 1000  # unchanged from the previous UI's limit
SESSION_TTL_SECONDS = 2 * 60 * 60  # 2 hours of inactivity

app = FastAPI(title="AI Document Assistant")

# In-memory per-session index state: {session_id: (IndexState, last_used_at)}.
# A single-process in-memory store is the simplest sensible choice at this
# project's scale (a personal/portfolio tool, not a multi-instance service).
# Sessions are lost on restart and are not shared across processes -- see
# README "Known limitations".
_sessions: dict[str, tuple[pipeline.IndexState, float]] = {}


def _prune_expired_sessions() -> None:
    now = time.time()
    expired = [sid for sid, (_, last_used) in _sessions.items() if now - last_used > SESSION_TTL_SECONDS]
    for sid in expired:
        del _sessions[sid]


def _get_index_state(request: Request) -> pipeline.IndexState | None:
    session_id = request.cookies.get("session_id")
    if session_id is None or session_id not in _sessions:
        return None
    index_state, _ = _sessions[session_id]
    _sessions[session_id] = (index_state, time.time())
    return index_state


@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...)):
    _prune_expired_sessions()

    if not (file.filename or "").lower().endswith(".pdf"):
        return JSONResponse({"error": "Please upload a PDF file."}, status_code=400)

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "File is too large. The limit is 25MB."}, status_code=413)

    try:
        index_state = pipeline.ingest(pdf_bytes)
    except Exception as e:
        print(f"Unexpected error during ingestion: {e}")
        index_state = None

    if index_state is None:
        return JSONResponse(
            {
                "error": (
                    "Couldn't extract any text from this PDF. It may be empty, "
                    "image-only (scanned without OCR), password-protected, or "
                    "corrupted."
                )
            }
        )

    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = (index_state, time.time())

    response = JSONResponse(
        {
            "filename": file.filename,
            "num_pages": index_state.num_pages,
            "num_chunks": index_state.num_chunks,
        }
    )
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
    )
    return response


@app.post("/api/ask")
async def ask(request: Request):
    _prune_expired_sessions()

    index_state = _get_index_state(request)
    if index_state is None:
        return JSONResponse({"error": "No document is loaded. Please upload a PDF first."}, status_code=400)

    body = await request.json()
    question = (body.get("question") or "").strip()
    if not question:
        return JSONResponse({"error": "Please enter a question."}, status_code=400)
    if len(question) > MAX_QUESTION_CHARS:
        return JSONResponse(
            {"error": f"Question is too long (max {MAX_QUESTION_CHARS} characters)."}, status_code=400
        )

    try:
        result = pipeline.answer(question, index_state)
        return JSONResponse({"answer": result["answer"], "sources": result["sources"]})
    except LLMConfigError as e:
        return JSONResponse({"error": str(e)})
    except LLMRequestError as e:
        return JSONResponse({"error": f"The LLM API request failed: {e}"})
    except Exception as e:
        print(f"Unexpected error while answering: {e}")
        return JSONResponse({"error": "Something went wrong while answering that question. Please try again."})


@app.post("/api/remove")
async def remove(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in _sessions:
        del _sessions[session_id]
    response = JSONResponse({"ok": True})
    response.delete_cookie("session_id")
    return response


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")
