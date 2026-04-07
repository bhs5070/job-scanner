import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.state import AgentState
from src.agents.utils import get_llm
from src.common.prompts import load_prompt

logger = logging.getLogger(__name__)

VALID_INTENTS = {"job_search", "resume_match", "skill_gap", "trend", "chitchat"}


def route(state: AgentState) -> dict:
    """Classify user intent and set routing fields in state."""
    llm = get_llm(temperature=0)
    system_prompt = load_prompt("router")

    # Use last 3 messages for context
    messages = state.get("messages", [])
    recent = messages[-3:] if len(messages) > 3 else messages
    context = "\n".join(
        f"{'사용자' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
        for m in recent
    )

    user_msg = f"대화 맥락:\n{context}\n\n현재 입력: {state['user_input']}"

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg),
        ])

        # Strip markdown code blocks if present
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(raw)
        intent = result.get("intent", "chitchat")
        confidence = float(result.get("confidence", 0.0))

        if intent not in VALID_INTENTS:
            intent = "chitchat"
            confidence = 0.5

        if confidence < 0.6:
            intent = "chitchat"

        logger.info(f"Router: intent={intent}, confidence={confidence}")

    except Exception as e:
        logger.warning(f"Router classification failed: {e}")
        intent = "chitchat"
        confidence = 0.0

    return {"intent": intent, "intent_confidence": confidence}


def route_by_intent(state: AgentState) -> str:
    """Conditional edge function: return next node name based on intent."""
    intent = state.get("intent", "chitchat")

    intent_to_node = {
        "job_search": "search",
        "resume_match": "match",
        "skill_gap": "gap",
        "trend": "trend",
        "chitchat": "chitchat",
    }

    return intent_to_node.get(intent, "chitchat")
