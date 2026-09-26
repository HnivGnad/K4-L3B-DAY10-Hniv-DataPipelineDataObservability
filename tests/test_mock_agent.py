"""The offline QA paths must answer from retrieval without tool-calling LLM support."""

from dataclasses import replace
from unittest.mock import patch

from app.chat import RetrievalHit, stream_answer
from core.config import load_settings
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import SearchResult


def test_mock_agent_answers_from_local_index() -> None:
    settings = replace(load_settings(), llm_provider="mock")

    class LocalIndex:
        def lookup(self, value: str):
            return None

        def search(self, query: str, top_k: int | None = None):
            return [SearchResult(
                paper_id="10.1234/1",
                title="A paper",
                score=0.9,
                content="Summary: A grounded finding.",
                metadata={"summary": "A grounded finding. More detail."},
            )]

    agent = build_agent(settings, LocalIndex())
    assert run_agent_question(agent, "Summarize the paper") == "A grounded finding."


def test_mock_chat_stream_uses_retrieved_context() -> None:
    settings = replace(load_settings(), llm_provider="mock")
    hits = [RetrievalHit("10.1234/1", "A paper", 0.9, "Summary: A grounded finding.")]
    with patch("app.chat.retrieve", return_value=hits):
        returned_hits, chunks = stream_answer("Summarize the paper", "baseline", settings)
    assert returned_hits == hits
    assert "".join(chunks) == "A grounded finding."
