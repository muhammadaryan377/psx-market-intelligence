from agents.graph import SimplePSXGraph


def test_simple_agent_graph_invoke_surface(monkeypatch):
    import agents.graph as graph_module

    def add_news(state):
        state["retrieved_news"] = []
        return state

    def add_sentiment(state):
        state["sentiment_label"] = "Neutral"
        state["sentiment_score"] = 0.0
        state["sentiment_confidence"] = 0.0
        return state

    def add_explanation(state):
        state["rag_explanation"] = "Week 2 baseline explanation."
        return state

    def add_decision(state):
        state["decision"] = "HOLD"
        state["confidence"] = 0.3
        state["decision_reason"] = "Smoke-test decision."
        return state

    monkeypatch.setattr(graph_module, "news_agent_node", add_news)
    monkeypatch.setattr(graph_module, "sentiment_agent_node", add_sentiment)
    monkeypatch.setattr(graph_module, "rag_agent_node", add_explanation)
    monkeypatch.setattr(graph_module, "decision_agent_node", add_decision)

    graph = SimplePSXGraph()
    final_state = graph.invoke(
        {
            "symbol": "HBL",
            "event_date": "2026-05-08",
            "event_type": "price_down",
            "trend": "DOWN",
        }
    )

    assert final_state["decision"] == "HOLD"
    assert final_state["rag_explanation"]
