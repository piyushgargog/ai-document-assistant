"""Phase 2: page-aware chunking with configurable size/overlap."""


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[dict]:
    """Split each page's text into overlapping character-window chunks.

    Each chunk keeps a reference to the page it came from. Returns a list
    of {"text": str, "page": int} dicts, in document order.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

    chunks = []
    step = chunk_size - chunk_overlap
    for page_num, text in pages:
        if len(text) <= chunk_size:
            chunks.append({"text": text, "page": page_num})
            continue
        start = 0
        while start < len(text):
            piece = text[start : start + chunk_size]
            if piece.strip():
                chunks.append({"text": piece, "page": page_num})
            if start + chunk_size >= len(text):
                break
            start += step
    return chunks
