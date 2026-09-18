"""Phase 6: orchestration — wires loader, chunker, embedder, vector store, LLM."""

from dataclasses import dataclass

import embedder
import llm_client
from chunker import chunk_pages
from pdf_loader import load_pdf_pages
from vector_store import VectorStore

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_TOP_K = 4


@dataclass
class IndexState:
    store: VectorStore
    num_pages: int
    num_chunks: int
    chunk_size: int
    chunk_overlap: int


def ingest(
    pdf_bytes: bytes,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> IndexState | None:
    """Run extraction -> chunking -> embedding -> indexing. Returns None if the
    PDF has no extractable text (invalid/empty PDF)."""
    pages = load_pdf_pages(pdf_bytes)
    if not pages:
        return None

    chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        return None

    vectors = embedder.embed([c["text"] for c in chunks])
    store = VectorStore(chunks, vectors)
    return IndexState(
        store=store,
        num_pages=len(pages),
        num_chunks=len(chunks),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def answer(question: str, index_state: IndexState, top_k: int = DEFAULT_TOP_K) -> dict:
    """Retrieve relevant chunks and generate a grounded answer.

    Returns {"answer": str, "sources": [{"page", "text", "score"}, ...]}.
    """
    query_vector = embedder.embed([question])[0]
    sources = index_state.store.search(query_vector, top_k=top_k)
    answer_text = llm_client.ask(question, sources)
    return {"answer": answer_text, "sources": sources}
