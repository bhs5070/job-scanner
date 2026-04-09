"""Unit tests for src/agents/search.py — pure helper functions."""

from unittest.mock import MagicMock, patch

from src.agents.search import (
    _deduplicate_results,
    _format_results_for_llm,
    search,
)
from src.agents.state import AgentState
from src.indexing.retriever import SearchResult


def _make_result(job_id: str, distance: float = 0.2, chunk_type: str = "full") -> SearchResult:
    return SearchResult(
        job_id=job_id,
        chunk_type=chunk_type,
        document=f"Job description for {job_id}",
        metadata={
            "job_id": job_id,
            "title": f"Engineer {job_id}",
            "company": f"Company {job_id}",
            "source_site": "wanted",
            "source_url": f"https://wanted.co.kr/wd/{job_id}",
            "chunk_type": chunk_type,
            "is_active": True,
        },
        distance=distance,
    )


def _make_state(**kwargs) -> AgentState:
    defaults: AgentState = {
        "messages": [],
        "user_input": "AI 엔지니어 공고",
        "intent": "job_search",
        "intent_confidence": 0.9,
        "search_results": None,
        "final_response": None,
        "error": None,
    }
    defaults.update(kwargs)
    return defaults


class TestDeduplicateResults:
    def test_keeps_single_best_per_job_id(self) -> None:
        results = [
            _make_result("job-1", distance=0.3, chunk_type="full"),
            _make_result("job-1", distance=0.1, chunk_type="requirements"),  # better
            _make_result("job-2", distance=0.2),
        ]
        deduped = _deduplicate_results(results)

        assert len(deduped) == 2
        job1 = next(r for r in deduped if r.job_id == "job-1")
        assert job1.distance == 0.1  # best (lowest) distance kept

    def test_empty_input_returns_empty(self) -> None:
        assert _deduplicate_results([]) == []

    def test_no_duplicates_unchanged(self) -> None:
        results = [_make_result("job-1"), _make_result("job-2"), _make_result("job-3")]
        deduped = _deduplicate_results(results)
        assert len(deduped) == 3


class TestFormatResultsForLlm:
    def test_empty_returns_placeholder(self) -> None:
        result = _format_results_for_llm([])
        assert "(검색 결과 없음)" in result

    def test_formats_result_fields(self) -> None:
        results = [_make_result("abc-123", distance=0.15)]
        formatted = _format_results_for_llm(results)

        assert "Engineer abc-123" in formatted
        assert "Company abc-123" in formatted
        assert "wanted" in formatted

    def test_score_is_1_minus_distance(self) -> None:
        results = [_make_result("x", distance=0.2)]
        formatted = _format_results_for_llm(results)
        # score = 1 - 0.2 = 0.8
        assert "0.8" in formatted

    def test_document_preview_truncated_at_300(self) -> None:
        long_doc = "A" * 500
        result = SearchResult(
            job_id="j1",
            chunk_type="full",
            document=long_doc,
            metadata={"title": "T", "company": "C", "source_site": "s", "source_url": "u"},
            distance=0.1,
        )
        formatted = _format_results_for_llm([result])
        # Preview should not exceed 300 chars from the document
        assert "A" * 300 in formatted
        assert "A" * 301 not in formatted

    def test_multiple_results_numbered(self) -> None:
        results = [_make_result(f"job-{i}") for i in range(3)]
        formatted = _format_results_for_llm(results)
        assert "[공고 1]" in formatted
        assert "[공고 2]" in formatted
        assert "[공고 3]" in formatted


class TestSearchAgent:
    @patch("src.agents.search.load_prompt", return_value="search prompt {search_results} {user_input}")
    @patch("src.agents.search.search_jobs")
    @patch("src.agents.search.ChatOpenAI")
    def test_search_sets_final_response(
        self,
        mock_chat_cls: MagicMock,
        mock_search_jobs: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        # Mock query rewrite + response LLM calls
        rewrite_response = MagicMock()
        rewrite_response.content = '{"query": "AI engineer", "chunk_type": "full"}'
        final_response = MagicMock()
        final_response.content = "검색 결과입니다."

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [rewrite_response, final_response]
        mock_chat_cls.return_value = mock_llm

        mock_search_jobs.return_value = [_make_result("job-1", distance=0.1)]

        state = _make_state(user_input="AI 엔지니어 채용")
        result = search(state)

        assert result["final_response"] == "검색 결과입니다."
        assert result["search_results"] is not None
        assert len(result["search_results"]) == 1

    @patch("src.agents.search.load_prompt", return_value="search prompt {search_results} {user_input}")
    @patch("src.agents.search.search_jobs")
    @patch("src.agents.search.ChatOpenAI")
    def test_search_handles_error_gracefully(
        self,
        mock_chat_cls: MagicMock,
        mock_search_jobs: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        mock_search_jobs.side_effect = Exception("ChromaDB unavailable")
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM fail")
        mock_chat_cls.return_value = mock_llm

        state = _make_state()
        result = search(state)

        assert result["error"] is not None
        assert "오류" in result["final_response"]
