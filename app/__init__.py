"""UI layer for Day 10 RAG observability demo.

Reuses every pipeline artifact in ``src/`` and ``data/``; this layer only
wraps them for Streamlit rendering. Touching ``src/`` is out of scope.
"""

__all__ = ["main", "state", "chat", "dashboard", "compare", "ui_components"]
