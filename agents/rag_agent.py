from datetime import datetime
from pathlib import Path
import sys
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.state import PSXAgentState


class RAGAgent:
    """
    RAG Agent:
    - retrieved_news + sentiment + trend ko use karta hai
    - stock movement ki natural-language explanation banata hai
    """

    def _shorten(self, text: Any, limit: int = 180) -> str:
        text = " ".join(str(text or "").split())

        if len(text) <= limit:
            return text

        return text[: limit - 3].rstrip() + "..."

    def _is_market_item(self, item: Dict[str, Any]) -> bool:
        symbol = str(item.get("symbol", "")).upper()
        news_type = str(item.get("news_type", "")).lower()
        scope = str(item.get("retrieval_scope", "")).lower()

        return (
            symbol == "KSE100"
            or news_type == "market_news"
            or "market" in scope
        )

    def _has_company_specific_context(
        self,
        news_items: List[Dict[str, Any]],
        symbol: str,
    ) -> bool:
        symbol = str(symbol or "").upper()

        return any(
            str(item.get("symbol", "")).upper() == symbol
            for item in news_items
        )

    def _build_news_context(
        self,
        news_items: List[Dict[str, Any]],
        symbol: str,
    ) -> str:
        supporting_items = news_items[:5]
        has_company_specific = self._has_company_specific_context(
            supporting_items,
            symbol,
        )
        has_market_context = any(
            self._is_market_item(item)
            for item in supporting_items
        )

        lines = []

        if has_market_context and not has_company_specific:
            lines.append(
                "Context note: this explanation is based on market-wide news rather than company-specific news."
            )
        elif has_market_context:
            lines.append(
                "Context note: company-specific items are combined with sector or market-wide news."
            )

        for index, item in enumerate(supporting_items, start=1):
            title = item.get("title", "Untitled")
            source = item.get("source", "Unknown source")
            date = str(item.get("published_date", ""))[:10] or "Unknown date"
            item_symbol = item.get("symbol", "Unknown")
            final_score = item.get("final_score", item.get("similarity_score", ""))
            summary = self._shorten(
                item.get("summary") or item.get("article_text"),
                limit=180,
            )

            lines.append(
                f"{index}. {date} | {item_symbol} | {source} | score={final_score}: {title}. {summary}"
            )

        return "\n".join(lines)

    def run(self, state: PSXAgentState) -> PSXAgentState:
        if "audit_log" not in state:
            state["audit_log"] = []

        symbol = state.get("symbol", "Unknown")
        company = state.get("company", symbol)
        sector = state.get("sector", "Unknown")
        event_date = state.get("event_date", "Unknown")
        event_type = state.get("event_type", "market_movement")
        trend = state.get("trend", "UNKNOWN")

        price = state.get("price")
        moving_average = state.get("moving_average")
        volume = state.get("volume")

        news_items = state.get("retrieved_news", [])
        sentiment_label = state.get("sentiment_label", "neutral")
        sentiment_score = state.get("sentiment_score", 0.0)
        sentiment_confidence = state.get("sentiment_confidence", 0.0)

        if not news_items:
            state.setdefault("sentiment_label", "neutral")
            state.setdefault("sentiment_score", 0.0)
            state.setdefault("sentiment_confidence", 0.0)
            state.setdefault("article_sentiments", [])

            market_data_bits = []

            if price is not None:
                market_data_bits.append(f"price={price}")

            if moving_average is not None:
                market_data_bits.append(f"moving_average={moving_average}")

            if volume is not None:
                market_data_bits.append(f"volume={volume}")

            market_data = ", ".join(market_data_bits) or "market data unavailable"

            state["rag_explanation"] = "\n\n".join([
                "Event Summary\n"
                f"{company} ({symbol}) had a {event_type} event on {event_date}. "
                f"Trend={trend}, sector={sector}, {market_data}.",
                "News Context\n"
                "No high-quality relevant news was retrieved for the event window.",
                "Sentiment Impact\n"
                "No news sentiment was available, so sentiment impact could not be applied.",
                "Final Explanation\n"
                "The movement should be treated as price/volume driven until stronger company, sector, or market news is available.",
            ])

            state["audit_log"].append({
                "agent": "RAGAgent",
                "status": "no_news_found",
                "timestamp": datetime.now().isoformat(),
            })

            return state

        market_data_bits = []

        if price is not None:
            market_data_bits.append(f"price={price}")

        if moving_average is not None:
            market_data_bits.append(f"moving_average={moving_average}")

        if volume is not None:
            market_data_bits.append(f"volume={volume}")

        market_data = ", ".join(market_data_bits) or "market data unavailable"

        trend_upper = str(trend).upper()
        sentiment_lower = str(sentiment_label).lower()

        if trend_upper == "DOWN" and sentiment_lower == "negative":
            final_reason = (
                "The downward move is supported by negative news sentiment. "
                "Retrieved context points to market pressure, weak investor mood, macro concerns, or PSX-wide weakness."
            )
        elif trend_upper == "UP" and sentiment_lower == "positive":
            final_reason = (
                "The upward move is supported by positive news sentiment. "
                "Retrieved context points to buying momentum, market recovery, or improved investor confidence."
            )
        elif trend_upper == "DOWN" and sentiment_lower == "positive":
            final_reason = (
                "News sentiment is positive while the stock trend is down. "
                "The decline may be driven by profit-taking, technical correction, or broader market pressure."
            )
        elif trend_upper == "UP" and sentiment_lower == "negative":
            final_reason = (
                "The stock trend is up while news sentiment is negative. "
                "This can indicate a short-term rebound or technical buying, with sentiment risk still present."
            )
        else:
            final_reason = (
                "Trend and news sentiment are mixed or neutral. "
                "The move likely reflects a blend of market-wide conditions, sector news, and technical factors."
            )

        state["rag_explanation"] = "\n\n".join([
            "Event Summary\n"
            f"{company} ({symbol}) had a {event_type} event on {event_date}. "
            f"Trend={trend}, sector={sector}, {market_data}.",
            "News Context\n"
            f"{self._build_news_context(news_items, symbol)}",
            "Sentiment Impact\n"
            f"Aggregate news sentiment is {sentiment_label} "
            f"(score={sentiment_score}, confidence={sentiment_confidence}).",
            "Final Explanation\n"
            f"{final_reason}",
        ])

        state["audit_log"].append({
            "agent": "RAGAgent",
            "status": "success",
            "news_used": len(news_items),
            "timestamp": datetime.now().isoformat(),
        })

        return state


rag_agent_instance = RAGAgent()


def rag_agent_node(state: PSXAgentState) -> PSXAgentState:
    return rag_agent_instance.run(state)
