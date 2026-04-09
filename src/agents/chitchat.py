import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import AgentState
from src.agents.utils import get_llm
from src.common.prompts import load_prompt

logger = logging.getLogger(__name__)

CHITCHAT_CONTEXT_WINDOW = 10  # Number of recent messages to include in context


def chitchat(state: AgentState) -> dict:
    """Handle general conversation and fallback responses."""
    llm = get_llm(temperature=0.7)
    system_prompt = load_prompt("chitchat")

    messages_list = state.get("messages", [])
    recent = messages_list[-CHITCHAT_CONTEXT_WINDOW:] if len(messages_list) > CHITCHAT_CONTEXT_WINDOW else messages_list

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(recent)
    messages.append(HumanMessage(content=state["user_input"]))

    try:
        response = llm.invoke(messages)
        return {"final_response": response.content}
    except Exception as e:
        logger.error(f"Chitchat failed: {e}")
        return {
            "final_response": "죄송합니다, 일시적으로 응답하기 어렵습니다. 다시 시도해 주세요.",
            "error": str(e),
        }
