from langgraph.graph import END, START, StateGraph

from agents.state import PSXAgentState
from agents.news_agent import news_agent_node
from agents.sentiment_agent import sentiment_agent_node
from agents.rag_agent import rag_agent_node


def route_after_news(state: PSXAgentState) -> str:
    """
    Agar news mil jaye to sentiment agent chalega.
    Agar news na mile to direct RAG Agent fallback explanation banayega.
    """
    retrieved_news = state.get("retrieved_news", [])

    if retrieved_news:
        return "sentiment_agent"

    return "rag_agent"


def build_psx_graph():
    graph = StateGraph(PSXAgentState)

    graph.add_node("news_agent", news_agent_node)
    graph.add_node("sentiment_agent", sentiment_agent_node)
    graph.add_node("rag_agent", rag_agent_node)

    graph.add_edge(START, "news_agent")

    graph.add_conditional_edges(
        "news_agent",
        route_after_news,
        {
            "sentiment_agent": "sentiment_agent",
            "rag_agent": "rag_agent",
        },
    )

    graph.add_edge("sentiment_agent", "rag_agent")
    graph.add_edge("rag_agent", END)

    return graph.compile()


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

    print("\n================ LANGGRAPH FINAL OUTPUT ================")
    print("Symbol:", final_state.get("symbol"))
    print("Company:", final_state.get("company"))
    print("Trend:", final_state.get("trend"))
    print("News Count:", len(final_state.get("retrieved_news", [])))
    print("Sentiment Label:", final_state.get("sentiment_label"))
    print("Sentiment Score:", final_state.get("sentiment_score"))

    print("\n================ RAG EXPLANATION ================")
    print(final_state.get("rag_explanation"))

    print("\n================ AUDIT LOG ================")
    for log in final_state.get("audit_log", []):
        print(log)