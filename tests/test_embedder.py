"""Downloads/loads the real sentence-transformers model on first run, same as
the app itself does — no network mocking, since the point is to verify the
actual embedding behavior, not a stand-in for it."""

import numpy as np

from embedder import embed


def test_embed_returns_normalized_384_dim_vectors():
    vectors = embed(["hello world", "another sentence"])
    assert vectors.shape == (2, 384)
    assert vectors.dtype == np.float32
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_related_sentences_score_higher_than_unrelated():
    vectors = embed(
        [
            "Jupiter is the largest planet in the Solar System.",
            "Saturn has a famous ring system.",
            "Bananas are a good source of potassium.",
        ]
    )
    sim_related = float(np.dot(vectors[0], vectors[1]))
    sim_unrelated = float(np.dot(vectors[0], vectors[2]))
    assert sim_related > sim_unrelated
