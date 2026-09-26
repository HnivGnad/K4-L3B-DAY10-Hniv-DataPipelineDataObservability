"""Chat layer that combines retrieval (in-app) with Gemini through the existing LLM factory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from core.config import Settings, load_settings
from core.utils import first_sentence
from retrieval.llm import build_llm

from app.state import STATES, semantic_search, lookup


@dataclass(frozen=True)
class RetrievalHit:
    paper_id: str
    title: str
    score: float
    content: str


def retrieve(question: str, state: str, top_k: int = 4) -> list[RetrievalHit]:
    """Semantic search wrapper that always returns the in-app top-k for ``state``."""
    raw = semantic_search(state, question, top_k=top_k)
    return [
        RetrievalHit(
            paper_id=hit["paper_id"],
            title=hit["title"],
            score=float(hit["score"]),
            content=hit["content"],
        )
        for hit in raw
    ]


def _format_context(hits: list[RetrievalHit]) -> str:
    """Render retrieved hits as a labelled context block for the prompt."""
    if not hits:
        return "(no documents retrieved)"
    blocks: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{idx}] paper_id: {hit.paper_id}\n"
            f"    title: {hit.title}\n"
            f"    score: {hit.score:.4f}\n"
            f"    {hit.content}"
        )
    return "\n\n".join(blocks)


def build_prompt(question: str, hits: list[RetrievalHit]) -> str:
    """RAG prompt that constrains the model to the indexed corpus."""
    ctx = _format_context(hits)
    return (
        "You are a research assistant answering questions about a scholarly paper corpus.\n"
        "Use ONLY the context below. If the answer is not supported, say so clearly.\n\n"
        f"CONTEXT:\n{ctx}\n\n"
        f"QUESTION: {question}\n"
        "ANSWER (be concise; cite sources like [1], [2] when relevant):"
    )


def _llm(settings: Settings):
    """Build the configured Gemini chat model via the existing factory."""
    return build_llm(settings=settings, temperature=0.0)


def stream_answer(question: str, state: str, settings: Settings | None = None) -> tuple[list[RetrievalHit], Iterator[str]]:
    """Return the retrieved hits and a streaming iterator of Gemini response chunks."""
    if state not in STATES:
        raise ValueError(f"Unknown state '{state}'. Expected one of {STATES}.")
    settings = settings or load_settings()
    hits = retrieve(question, state)
    prompt = build_prompt(question, hits)
    llm = _llm(settings)

    def _chunks() -> Iterator[str]:
        try:
            for chunk in llm.stream(prompt):
                content = getattr(chunk, "content", None)
                if content:
                    yield content
        except Exception as exc:  # noqa: BLE001 - surface the error in the UI
            yield f"\n\n⚠️ LLM call failed: {exc}"

    return hits, _chunks()


def quick_extract_answer(question: str, state: str) -> str:
    """Extract a one-shot answer using the same heuristic rules as src/retrieval/qa.py.

    Used for the deterministic side-by-side comparison; not the streamed Gemini path.
    """
    hits = retrieve(question, state, top_k=1)
    if not hits:
        return "I don't know from the indexed corpus."
    top = hits[0]
    metadata = top.content  # content already encodes title/authors/date/categories
    lowered = question.lower()
    if "who authored" in lowered or "list the authors" in lowered:
        for line in metadata.splitlines():
            if line.startswith("Authors:"):
                return line.replace("Authors:", "").strip()
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        for line in metadata.splitlines():
            if line.startswith("Published:"):
                return line.replace("Published:", "").strip()
    if "what categories" in lowered:
        for line in metadata.splitlines():
            if line.startswith("Categories:"):
                return line.replace("Categories:", "").strip()
    summary_line = next(
        (line for line in metadata.splitlines() if line.startswith("Summary:")),
        "",
    )
    return first_sentence(summary_line.replace("Summary:", "").strip())
