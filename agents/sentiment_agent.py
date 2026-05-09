from datetime import datetime

from agents.state import PSXAgentState
from sentiment_layer.sentiment_service import SentimentService


class SentimentAgent:
    """
    Sentiment Agent:
    - retrieved_news leta hai
    - FinBERT sentiment run karta hai
    - aggregate sentiment state mein save karta hai
    """

    def __init__(self):
        self.service = SentimentService()

    def run(self, state: PSXAgentState) -> PSXAgentState:
        if "audit_log" not in state:
            state["audit_log"] = []

        news_items = state.get("retrieved_news", [])

        sentiment_result = self.service.analyze_news_list(news_items)

        state["sentiment_label"] = sentiment_result.get("sentiment_label", "neutral")
        state["sentiment_score"] = sentiment_result.get("sentiment_score", 0.0)
        state["sentiment_confidence"] = sentiment_result.get("sentiment_confidence", 0.0)
        state["article_sentiments"] = sentiment_result.get("article_sentiments", [])

        state["audit_log"].append({
            "agent": "SentimentAgent",
            "status": sentiment_result.get("sentiment_status", "unknown"),
            "sentiment_label": state.get("sentiment_label"),
            "sentiment_score": state.get("sentiment_score"),
            "timestamp": datetime.now().isoformat(),
        })

        return state


sentiment_agent_instance = SentimentAgent()


def sentiment_agent_node(state: PSXAgentState) -> PSXAgentState:
    return sentiment_agent_instance.run(state)