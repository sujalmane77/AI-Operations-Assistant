"""
Query interface over the persistent ChromaDB collection built by ingest.py.
"""
import os

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "none")

import chromadb
from chromadb.config import Settings

from app.config import config
from app.rag.embeddings import embed_texts

CHROMA_DIR = config.chroma_db
CHROMA_COLLECTION = config.chroma_collection


def retrieve(query: str, k: int = 4) -> list[dict]:
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        collection = client.get_collection(CHROMA_COLLECTION)
    except Exception as e:
        raise RuntimeError(
            f"Collection '{CHROMA_COLLECTION}' not found. Run "
            f"`python -m app.rag.ingest` first. ({e})"
        )

    query_vec = embed_texts([query])[0]
    results = collection.query(query_embeddings=[query_vec], n_results=k)

    out = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for text, meta, dist in zip(docs, metas, dists):
        out.append({
            "text": text,
            "source_section": meta.get("source_section", "Unknown"),
            "score": 1 - dist,  # convert distance to a similarity-ish score
        })
    return out


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What is the leave policy?"
    for r in retrieve(q):
        print(f"[{r['score']:.3f}] ({r['source_section']}) {r['text'][:120]}...")
