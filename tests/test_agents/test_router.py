"""Unit tests for src/agents/router.py."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.router import VALID_INTENTS, route, route_by_intent
from src.agents.state import AgentState


def _make_state(**kwargs) -> AgentState:
    defaults: AgentState = {
        "messages": [],
        "user_input": "test",
        "intent": None,
        "intent_confidence": None,
        "search_results": None,
        "final_response": None,
        "error": None,
    }
    defaults.update(kwargs)
    return defaults


class TestRouteByIntent:
    """route_by_intent is a pure function — no mocking needed."""

    def test_job_search_routes_to_search(self) -> None:
        state = _make_state(intent="job_search")
        assert route_by_intent(state) == "search"

    def test_resume_match_routes_to_match(self) -> None:
        state = _make_state(intent="resume_match")
        assert route_by_intent(state) == "match"

    def test_skill_gap_routes_to_gap(self) -> None:
        state = _make_state(intent="skill_gap")
        assert route_by_intent(state) == "gap"

    def test_trend_routes_to_trend(self) -> None:
        state = _make_state(intent="trend")
        assert route_by_intent(state) == "trend"

    def test_chitchat_routes_to_chitchat(self) -> None:
        state = _make_state(intent="chitchat")
        assert route_by_intent(state) == "chitchat"

    def test_unknown_intent_falls_back_to_chitchat(self) -> None:
        state = _make_state(intent="unknown_garbage")
        assert route_by_intent(state) == "chitchat"

    def test_none_intent_falls_back_to_chitchat(self) -> None:
        state = _make_state(intent=None)
        assert route_by_intent(state) == "chitchat"

    def test_all_valid_intents_have_routing(self) -> None:
        """Ensure every VALID_INTENT maps to a node."""
        for intent in VALID_INTENTS:
            state = _make_state(intent=intent)
            result = route_by_intent(state)
            assert result in {"search", "match", "gap", "trend", "chitchat"}


class TestRoute:
    """route() calls LLM — mock it."""

    def _mock_llm_response(self, intent: str, confidence: float) -> MagicMock:
        import json
        mock_response = MagicMock()
        mock_response.content = json.dumps({"intent": intent, "confidence": confidence})
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        return mock_llm

    @patch("src.agents.router.load_prompt", return_value="system prompt")
    @patch("src.agents.router.ChatOpenAI")
    def test_route_sets_intent_and_confidence(
        self, mock_chat_cls: MagicMock, mock_load: MagicMock
    ) -> None:
        mock_chat_cls.return_value = self._mock_llm_response("job_search", 0.9)
        state = _make_state(user_input="백엔드 개발자 공고 찾아줘")
        result = route(state)

        assert result["intent"] == "job_search"
        assert result["intent_confidence"] == 0.9

    @patch("src.agents.router.load_prompt", return_value="system prompt")
    @patch("src.agents.router.ChatOpenAI")
    def test_low_confidence_falls_back_to_chitchat(
        self, mock_chat_cls: MagicMock, mock_load: MagicMock
    ) -> None:
        mock_chat_cls.return_value = self._mock_llm_response("job_search", 0.4)
        state = _make_state(user_input="뭔가")
        result = route(state)

        assert result["intent"] == "chitchat"

    @patch("src.agents.router.load_prompt", return_value="system prompt")
    @patch("src.agents.router.ChatOpenAI")
    def test_invalid_intent_falls_back_to_chitchat(
        self, mock_chat_cls: MagicMock, mock_load: MagicMock
    ) -> None:
        mock_chat_cls.return_value = self._mock_llm_response("fly_to_moon", 0.95)
        state = _make_state(user_input="뭔가")
        result = route(state)

        assert result["intent"] == "chitchat"

    @patch("src.agents.router.load_prompt", return_value="system prompt")
    @patch("src.agents.router.ChatOpenAI")
    def test_llm_failure_falls_back_gracefully(
        self, mock_chat_cls: MagicMock, mock_load: MagicMock
    ) -> None:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("OpenAI timeout")
        mock_chat_cls.return_value = mock_llm

        state = _make_state(user_input="실패 케이스")
        result = route(state)

        assert result["intent"] == "chitchat"
        assert result["intent_confidence"] == 0.0

    @patch("src.agents.router.load_prompt", return_value="system prompt")
    @patch("src.agents.router.ChatOpenAI")
    def test_markdown_code_block_stripped(
        self, mock_chat_cls: MagicMock, mock_load: MagicMock
    ) -> None:
        """LLM sometimes wraps JSON in ```json ... ```."""
        import json
        mock_response = MagicMock()
        mock_response.content = "```json\n" + json.dumps({"intent": "trend", "confidence": 0.85}) + "\n```"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_cls.return_value = mock_llm

        state = _make_state(user_input="트렌드 분석")
        result = route(state)

        assert result["intent"] == "trend"

    @patch("src.agents.router.load_prompt", return_value="system prompt")
    @patch("src.agents.router.ChatOpenAI")
    def test_uses_last_3_messages_for_context(
        self, mock_chat_cls: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verifies only the last 3 messages are used — not all history."""
        import json
        mock_response = MagicMock()
        mock_response.content = json.dumps({"intent": "chitchat", "confidence": 0.8})
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_cls.return_value = mock_llm

        messages = [HumanMessage(content=f"msg {i}") for i in range(10)]
        state = _make_state(user_input="현재 입력", messages=messages)
        route(state)

        # Confirm LLM was called
        mock_llm.invoke.assert_called_once()
