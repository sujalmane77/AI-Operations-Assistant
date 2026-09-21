"""
Local embeddings via sentence-transformers. No API calls, no rate limits.
"""
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import config


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(config.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    vectors = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()
