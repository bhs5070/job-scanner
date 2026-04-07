from langchain_core.messages import AIMessage, HumanMessage

from src.agents.state import AgentState


def respond(state: AgentState) -> dict:
    """Append the final response to message history.

    This is the common exit node that all agent paths converge to.
    """
    messages = list(state.get("messages", []))

    # Add user input to history if not already there
    last = messages[-1] if messages else None
    if not last or not isinstance(last, HumanMessage) or last.content != state["user_input"]:
        messages.append(HumanMessage(content=state["user_input"]))

    # Add AI response to history
    response_text = state.get("final_response") or "응답을 생성하지 못했습니다."
    messages.append(AIMessage(content=response_text))

    return {"messages": messages}
