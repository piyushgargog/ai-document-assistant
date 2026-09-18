import pytest

from embedder import embed
from vector_store import VectorStore


def test_search_ranks_the_matching_chunk_first():
    chunks = [
        {"text": "Jupiter is the largest planet in the Solar System.", "page": 1},
        {"text": "Bananas are a good source of potassium.", "page": 2},
    ]
    store = VectorStore(chunks, embed([c["text"] for c in chunks]))

    results = store.search(embed(["What is the biggest planet?"])[0], top_k=2)

    assert results[0]["page"] == 1
    assert results[0]["score"] >= results[1]["score"]


def test_top_k_is_capped_at_the_number_of_available_chunks():
    chunks = [{"text": "the only chunk", "page": 1}]
    store = VectorStore(chunks, embed([c["text"] for c in chunks]))

    results = store.search(embed(["a query"])[0], top_k=10)

    assert len(results) == 1


def test_mismatched_chunks_and_embeddings_length_raises():
    vectors = embed(["a", "b"])
    with pytest.raises(ValueError):
        VectorStore([{"text": "a", "page": 1}], vectors)
