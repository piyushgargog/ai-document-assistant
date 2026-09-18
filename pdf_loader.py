"""Phase 1: page-aware PDF text extraction (PyMuPDF)."""

import pymupdf


def load_pdf_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Extract text per page from PDF bytes.

    Returns a list of (page_number, page_text) pairs, 1-indexed.
    Pages with no extractable text are skipped. Returns an empty list
    for an invalid, corrupt, or fully-empty PDF instead of raising.
    """
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return []

    pages = []
    for page_index in range(doc.page_count):
        text = doc[page_index].get_text().strip()
        if text:
            pages.append((page_index + 1, text))
    doc.close()
    return pages
