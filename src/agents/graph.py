"""LangGraph StateGraph assembly.

Connects all agent nodes and defines routing edges.
"""

from langgraph.graph import END, StateGraph

from src.agents.chitchat import chitchat
from src.agents.gap import gap
from src.agents.interview import interview
from src.agents.match import match
from src.agents.respond import respond
from src.agents.router import route, route_by_intent
from src.agents.search import search
from src.agents.state import AgentState
from src.agents.trend import trend


def build_graph() -> StateGraph:
    """Build the agent state graph with all nodes and edges."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("route", route)
    graph.add_node("search", search)
    graph.add_node("match", match)
    graph.add_node("gap", gap)
    graph.add_node("trend", trend)
    graph.add_node("chitchat", chitchat)
    graph.add_node("interview", interview)
    graph.add_node("respond", respond)

    # Entry point
    graph.set_entry_point("route")

    # Conditional routing from router
    graph.add_conditional_edges(
        "route",
        route_by_intent,
        {
            "search": "search",
            "match": "match",
            "gap": "gap",
            "trend": "trend",
            "interview": "interview",
            "chitchat": "chitchat",
        },
    )

    # All agents converge to respond
    graph.add_edge("search", "respond")
    graph.add_edge("match", "respond")
    graph.add_edge("gap", "respond")
    graph.add_edge("trend", "respond")
    graph.add_edge("chitchat", "respond")
    graph.add_edge("interview", "respond")

    # Respond exits the graph
    graph.add_edge("respond", END)

    return graph


def compile_graph() -> "CompiledStateGraph":
    """Compile the graph for execution."""
    from langgraph.graph.state import CompiledStateGraph  # noqa: F811
    return build_graph().compile()
