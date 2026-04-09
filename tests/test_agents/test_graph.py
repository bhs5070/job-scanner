"""Unit tests for src/agents/graph.py — graph structure validation."""

from langgraph.graph import END, StateGraph

from src.agents.graph import build_graph, compile_graph


class TestBuildGraph:
    def test_returns_state_graph(self) -> None:
        graph = build_graph()
        assert isinstance(graph, StateGraph)

    def test_compile_returns_runnable(self) -> None:
        compiled = compile_graph()
        # LangGraph compiled graph must be invokable
        assert hasattr(compiled, "invoke")

    def test_all_nodes_present(self) -> None:
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        expected = {"route", "search", "match", "gap", "trend", "chitchat", "respond"}
        assert expected.issubset(node_names)

    def test_entry_point_is_route(self) -> None:
        graph = build_graph()
        assert graph.entry_point == "route"
