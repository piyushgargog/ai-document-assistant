import pytest

from chunker import chunk_pages


def test_short_page_becomes_a_single_chunk():
    chunks = chunk_pages([(1, "short text")], chunk_size=800, chunk_overlap=150)
    assert chunks == [{"text": "short text", "page": 1}]


def test_long_page_splits_and_keeps_correct_page_numbers():
    pages = [(1, "a" * 500), (2, "b" * 500)]
    chunks = chunk_pages(pages, chunk_size=200, chunk_overlap=40)

    assert len(chunks) > 2
    assert all(c["page"] == 1 for c in chunks if c["text"].startswith("a"))
    assert all(c["page"] == 2 for c in chunks if c["text"].startswith("b"))


def test_smaller_chunk_size_yields_more_chunks():
    pages = [(1, "x" * 1000)]
    small = chunk_pages(pages, chunk_size=100, chunk_overlap=20)
    large = chunk_pages(pages, chunk_size=500, chunk_overlap=100)
    assert len(small) > len(large)


def test_rejects_non_positive_chunk_size():
    with pytest.raises(ValueError):
        chunk_pages([(1, "text")], chunk_size=0, chunk_overlap=0)


def test_rejects_overlap_not_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_pages([(1, "text")], chunk_size=100, chunk_overlap=100)
