"""Unit tests for src/agents/respond.py — no LLM, pure state manipulation."""

from langchain_core.messages import AIMessage, HumanMessage

from src.agents.respond import respond
from src.agents.state import AgentState


def _make_state(**kwargs) -> AgentState:
    defaults: AgentState = {
        "messages": [],
        "user_input": "안녕하세요",
        "intent": "chitchat",
        "intent_confidence": 0.9,
        "search_results": None,
        "final_response": "안녕하세요! 반갑습니다.",
        "error": None,
    }
    defaults.update(kwargs)
    return defaults


class TestRespond:
    def test_appends_human_and_ai_messages(self) -> None:
        state = _make_state()
        result = respond(state)

        messages = result["messages"]
        assert len(messages) == 2
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "안녕하세요"
        assert isinstance(messages[1], AIMessage)
        assert messages[1].content == "안녕하세요! 반갑습니다."

    def test_does_not_duplicate_existing_human_message(self) -> None:
        """If messages already ends with user_input, don't add it again."""
        state = _make_state(
            messages=[HumanMessage(content="안녕하세요")],
        )
        result = respond(state)

        human_msgs = [m for m in result["messages"] if isinstance(m, HumanMessage)]
        assert len(human_msgs) == 1

    def test_fallback_when_final_response_is_none(self) -> None:
        state = _make_state(final_response=None)
        result = respond(state)

        ai_msgs = [m for m in result["messages"] if isinstance(m, AIMessage)]
        assert len(ai_msgs) == 1
        assert "응답을 생성하지 못했습니다" in ai_msgs[0].content

    def test_fallback_when_final_response_is_empty_string(self) -> None:
        state = _make_state(final_response="")
        result = respond(state)

        ai_msgs = [m for m in result["messages"] if isinstance(m, AIMessage)]
        assert "응답을 생성하지 못했습니다" in ai_msgs[0].content

    def test_preserves_existing_message_history(self) -> None:
        existing = [
            HumanMessage(content="이전 질문"),
            AIMessage(content="이전 답변"),
        ]
        state = _make_state(messages=list(existing))
        result = respond(state)

        # Existing messages preserved, 2 new ones added
        assert len(result["messages"]) == 4
        assert result["messages"][0].content == "이전 질문"
        assert result["messages"][1].content == "이전 답변"
