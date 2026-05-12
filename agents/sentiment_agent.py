from datetime import datetime
from pathlib import Path
import sys
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
        self._service: Optional[SentimentService] = None

    @property
    def service(self) -> SentimentService:
        if self._service is None:
            self._service = SentimentService()

        return self._service

    def run(self, state: PSXAgentState) -> PSXAgentState:
        if "audit_log" not in state:
            state["audit_log"] = []

        news_items = state.get("retrieved_news", [])

        try:
            sentiment_result = self.service.analyze_news_list(news_items)
        except Exception as exc:
            sentiment_result = {
                "sentiment_label": "neutral",
                "sentiment_score": 0.0,
                "sentiment_confidence": 0.0,
                "article_sentiments": [],
                "sentiment_status": "failed",
            }
            state["error_message"] = f"Sentiment analysis failed: {exc}"

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


sentiment_agent_instance: Optional[SentimentAgent] = None


def sentiment_agent_node(state: PSXAgentState) -> PSXAgentState:
    global sentiment_agent_instance

    if sentiment_agent_instance is None:
        sentiment_agent_instance = SentimentAgent()

    return sentiment_agent_instance.run(state)
