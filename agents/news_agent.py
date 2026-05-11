from datetime import datetime
from typing import Optional

from agents.state import PSXAgentState
from rag_layer.retriever import RAGRetriever


class NewsAgent:
    """
    News Agent:
    - symbol, event_date, trend, event_type state se leta hai
    - RAGRetriever ko call karta hai
    - retrieved_news state mein save karta hai
    """

    def __init__(self):
        self._retriever: Optional[RAGRetriever] = None

    @property
    def retriever(self) -> RAGRetriever:
        if self._retriever is None:
            self._retriever = RAGRetriever()

        return self._retriever

    def run(self, state: PSXAgentState) -> PSXAgentState:
        if "audit_log" not in state:
            state["audit_log"] = []

        symbol = state.get("symbol")
        event_date = state.get("event_date")
        event_type = state.get("event_type", "market_movement")
        trend = state.get("trend", "UNKNOWN")
        sector = state.get("sector")

        if not symbol or not event_date:
            state["retrieved_news"] = []
            state["error_message"] = "NewsAgent requires symbol and event_date."

            state["audit_log"].append({
                "agent": "NewsAgent",
                "status": "failed",
                "reason": "missing_symbol_or_event_date",
                "timestamp": datetime.now().isoformat(),
            })

            return state

        try:
            news_items = self.retriever.retrieve(
                symbol=symbol,
                event_date=event_date,
                event_type=event_type,
                trend=trend,
                sector=sector,
                top_k=5,
                lookback_days=7,
            )
        except Exception as exc:
            news_items = []
            state["error_message"] = f"News retrieval failed: {exc}"

            state["audit_log"].append({
                "agent": "NewsAgent",
                "status": "failed",
                "reason": "news_retrieval_error",
                "error": str(exc),
                "timestamp": datetime.now().isoformat(),
            })

            state["retrieved_news"] = news_items
            return state

        state["retrieved_news"] = news_items

        state["audit_log"].append({
            "agent": "NewsAgent",
            "status": "success" if news_items else "no_news_found",
            "symbol": symbol,
            "event_date": event_date,
            "news_count": len(news_items),
            "timestamp": datetime.now().isoformat(),
        })

        return state


news_agent_instance: Optional[NewsAgent] = None


def news_agent_node(state: PSXAgentState) -> PSXAgentState:
    global news_agent_instance

    if news_agent_instance is None:
        news_agent_instance = NewsAgent()

    return news_agent_instance.run(state)
