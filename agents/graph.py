from copy import deepcopy

from agents.decision_agent import decision_agent_node
from agents.news_agent import news_agent_node
from agents.rag_agent import rag_agent_node
from agents.sentiment_agent import sentiment_agent_node
from agents.state import PSXAgentState


class SimplePSXGraph:
    """
    Week 2 sequential adapter.

    TODO Week 3: replace this with the final LangGraph workflow once the
    streaming, RAG, and sentiment baselines are stable.
    """

    def invoke(self, state: PSXAgentState) -> PSXAgentState:
        current_state: PSXAgentState = deepcopy(state)
        current_state = news_agent_node(current_state)
        current_state = sentiment_agent_node(current_state)
        current_state = rag_agent_node(current_state)
        current_state = decision_agent_node(current_state)
        return current_state


def build_psx_graph() -> SimplePSXGraph:
    return SimplePSXGraph()


psx_graph = build_psx_graph()


if __name__ == "__main__":
    input_state: PSXAgentState = {
        "symbol": "HBL",
        "company": "Habib Bank Limited",
        "sector": "Banking",
        "event_date": "2026-05-08",
        "event_type": "price_down",
        "trend": "DOWN",
        "price": 145.5,
        "volume": 250000,
        "moving_average": 148.2,
    }

    final_state = psx_graph.invoke(input_state)
    print("\n================ AGENT BASELINE OUTPUT ================")
    print("Symbol:", final_state.get("symbol"))
    print("Trend:", final_state.get("trend"))
    print("News Count:", len(final_state.get("retrieved_news", [])))
    print("Sentiment Label:", final_state.get("sentiment_label"))
    print("Decision:", final_state.get("decision"))
    print("Decision Reason:", final_state.get("decision_reason"))
