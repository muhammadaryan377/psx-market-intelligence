from datetime import datetime
from typing import Any, Optional

from agents.state import PSXAgentState


LOW_CONFIDENCE_THRESHOLD = 0.45
HIGH_CONFIDENCE_THRESHOLD = 0.80


class DecisionAgent:
    """
    Safe academic decision-support agent.

    Produces BUY/SELL/HOLD labels for analysis only. It does not execute trades
    and must not be treated as financial advice.
    """

    def _as_float(self, value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _is_market_data_missing(self, state: PSXAgentState) -> bool:
        required_fields = [
            "symbol",
            "event_date",
            "trend",
            "event_type",
            "price",
            "volume",
            "moving_average",
        ]

        return any(state.get(field) in [None, ""] for field in required_fields)

    def _base_confidence(
        self,
        sentiment_confidence: float,
        confidence_hint: Optional[float],
        news_count: int,
    ) -> float:
        confidence_parts = []

        if sentiment_confidence > 0:
            confidence_parts.append(sentiment_confidence)

        if confidence_hint is not None:
            confidence_parts.append(confidence_hint)

        if news_count > 0:
            confidence_parts.append(min(0.75, 0.45 + (news_count * 0.06)))

        if not confidence_parts:
            return 0.25

        return round(sum(confidence_parts) / len(confidence_parts), 4)

    def run(self, state: PSXAgentState) -> PSXAgentState:
        if "audit_log" not in state:
            state["audit_log"] = []

        symbol = state.get("symbol", "Unknown")
        trend = str(state.get("trend", "UNKNOWN")).upper()
        sentiment_label = str(state.get("sentiment_label", "neutral")).lower()
        sentiment_score = self._as_float(state.get("sentiment_score")) or 0.0
        sentiment_confidence = self._as_float(state.get("sentiment_confidence")) or 0.0
        confidence_hint = self._as_float(state.get("confidence_hint"))
        news_count = len(state.get("retrieved_news", []))

        confidence = self._base_confidence(
            sentiment_confidence=sentiment_confidence,
            confidence_hint=confidence_hint,
            news_count=news_count,
        )

        decision = "HOLD"

        if self._is_market_data_missing(state):
            reason = (
                "HOLD because required market event fields are missing. "
                "This is academic decision support only, not financial advice."
            )
            confidence = min(confidence, 0.30)

        elif sentiment_confidence < LOW_CONFIDENCE_THRESHOLD:
            reason = (
                f"HOLD because sentiment confidence is low ({sentiment_confidence}). "
                "The system needs stronger evidence before assigning a directional decision. "
                "This is academic decision support only, not financial advice."
            )
            confidence = min(confidence, 0.40)

        elif trend == "UP" and sentiment_label == "positive":
            decision = "BUY"
            reason = (
                f"BUY because {symbol} has an UP trend and positive news sentiment. "
                "This means market movement and retrieved news are directionally aligned. "
                "This is academic decision support only, not financial advice."
            )

        elif trend == "DOWN" and sentiment_label == "negative":
            if (
                sentiment_confidence >= HIGH_CONFIDENCE_THRESHOLD
                and sentiment_score <= -0.50
                and news_count >= 3
            ):
                decision = "SELL"
                reason = (
                    f"SELL because {symbol} has a DOWN trend, negative sentiment, "
                    "high sentiment confidence, and multiple supporting news items. "
                    "This is academic decision support only, not financial advice."
                )
                confidence = max(confidence, 0.75)
            else:
                reason = (
                    f"HOLD because {symbol} has a DOWN trend and negative sentiment, "
                    "but evidence is not strong enough for a high-confidence SELL label. "
                    "This is academic decision support only, not financial advice."
                )

        elif trend == "UP" and sentiment_label == "negative":
            reason = (
                f"HOLD because {symbol} has an UP trend but negative news sentiment. "
                "The signal is mixed, so the safer academic label is HOLD. "
                "This is academic decision support only, not financial advice."
            )

        elif trend == "DOWN" and sentiment_label == "positive":
            reason = (
                f"HOLD because {symbol} has a DOWN trend but positive news sentiment. "
                "The signal is mixed, so the safer academic label is HOLD. "
                "This is academic decision support only, not financial advice."
            )

        elif trend == "STABLE":
            reason = (
                f"HOLD because {symbol} trend is STABLE. "
                "This is academic decision support only, not financial advice."
            )

        else:
            reason = (
                f"HOLD because the trend/sentiment combination is neutral or unclear "
                f"(trend={trend}, sentiment={sentiment_label}). "
                "This is academic decision support only, not financial advice."
            )

        state["decision"] = decision
        state["confidence"] = round(max(0.0, min(1.0, confidence)), 4)
        state["decision_reason"] = reason

        state["audit_log"].append({
            "agent": "DecisionAgent",
            "status": "success",
            "decision": state["decision"],
            "confidence": state["confidence"],
            "timestamp": datetime.now().isoformat(),
        })

        return state


decision_agent_instance = DecisionAgent()


def decision_agent_node(state: PSXAgentState) -> PSXAgentState:
    return decision_agent_instance.run(state)
