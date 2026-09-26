"""Loader for the three ChromaDB-backed indexes (baseline / corrupted / repaired).

Reuses ``LocalEmbeddingIndex.load`` from ``src/retrieval/index.py`` and
caches the result for the lifetime of the Streamlit session.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from core.config import Settings, load_settings
from core.utils import read_json
from retrieval.embeddings import MiniLMEmbeddings


STATES: tuple[str, ...] = ("baseline", "corrupted", "repaired")

# Nhãn tiếng Việt hiển thị trên UI — đồng bộ giữa dashboard, compare và sidebar.
STATE_LABELS_VI: dict[str, str] = {
    "baseline": "Sạch (Baseline)",
    "corrupted": "Lỗi (Corrupted)",
    "repaired": "Phục hồi (Repaired)",
}

STATE_COLORS: dict[str, str] = {
    "baseline": "#16a34a",
    "corrupted": "#dc2626",
    "repaired": "#2563eb",
}


def _embeddings_path(settings: Settings, state: str):
    mapping = {
        "baseline": settings.paths.embeddings_json,
        "corrupted": settings.paths.corrupted_embeddings_json,
        "repaired": settings.paths.repaired_embeddings_json,
    }
    return mapping[state]


def _manifest_path(state: str) -> Path:
    """Path to the embeddings manifest that mirrors the in-memory documents list.

    The manifest is written by ``LocalEmbeddingIndex.build`` and contains the
    full documents array, so reading it gives us the same corpus without
    opening a Chroma PersistentClient (which can fail on Unicode paths).
    """
    return _embeddings_path(load_settings(), state)


@st.cache_resource(show_spinner="Đang tải 3 ChromaDB indexes…")
def load_all_indexes(file_versions: tuple[int, int, int]) -> dict[str, Any]:
    """Load three index wrappers — one per pipeline state.

    Each value is the raw manifest dict (backend, model, collection, documents).
    This avoids touching Chroma's Rust bindings, which can fail to create its
    internal directory tree on paths with non-ASCII characters.
    """
    settings = load_settings()
    out: dict[str, Any] = {}
    for state in STATES:
        manifest = read_json(_embeddings_path(settings, state))
        out[state] = {
            "manifest": manifest,
            "documents": manifest["documents"],
            "collection_name": manifest["collection_name"],
            "embedding_model": manifest["embedding_model"],
        }
    return out


def get_manifest(state: str) -> dict[str, Any]:
    if state not in STATES:
        raise ValueError(f"Unknown state '{state}'. Expected one of {STATES}.")
    settings = load_settings()
    paths = tuple(_embeddings_path(settings, name) for name in STATES)
    return load_all_indexes(tuple(path.stat().st_mtime_ns for path in paths))[state]


def active_state() -> str:
    """Return the quality-approved state selected by the pipeline."""
    path = load_settings().paths.active_state
    if not path.exists():
        return "baseline"
    payload = read_json(path)
    state = payload.get("state")
    return state if payload.get("quality_success") and state in STATES else "baseline"


def list_documents(state: str) -> list[dict[str, Any]]:
    """In-memory documents of a state. No vector DB required."""
    return get_manifest(state)["documents"]


def embedding_model() -> MiniLMEmbeddings:
    """Singleton MiniLM embedder used for in-process cosine search."""
    settings = load_settings()
    return MiniLMEmbeddings(settings.embedding_model)


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    den_a = sum(x * x for x in a) ** 0.5
    den_b = sum(x * x for x in b) ** 0.5
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def semantic_search(state: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Compute cosine similarity over the in-memory manifest embeddings.

    ``LocalEmbeddingIndex`` already writes the computed embedding of each
    document's ``content`` into the manifest (encoded inside the Chroma
    collection). Here we re-embed the query and rank against the stored
    vectors we can derive directly via the embedder to keep this layer free
    of the Chroma PersistentClient.
    """
    docs = list_documents(state)
    embedder = embedding_model()
    query_vec = embedder.embed_query(query)

    # The manifest documents do not carry the precomputed embedding vector;
    # we re-embed their text on demand (24 docs × ~1 chunk ≈ instant).
    doc_texts = [doc["content"] for doc in docs]
    doc_vecs = embedder.embed_documents(doc_texts)
    scored = [
        {
            "paper_id": doc["paper_id"],
            "title": doc["title"],
            "score": _cosine(query_vec, doc_vec),
            "content": doc["content"],
            "metadata": doc.get("metadata", {}),
        }
        for doc, doc_vec in zip(docs, doc_vecs, strict=False)
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def lookup(state: str, value: str) -> dict[str, Any] | None:
    needle = value.strip().lower()
    for doc in list_documents(state):
        if doc["paper_id"].lower() == needle or doc["title"].lower() == needle:
            return doc
    return None
