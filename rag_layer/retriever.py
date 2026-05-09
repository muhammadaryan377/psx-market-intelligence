from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from rag_layer.vector_store import NewsVectorStore


class RAGRetriever:
    def __init__(self):
        self.vector_store = NewsVectorStore()

    def _date_window(self, event_date: str, lookback_days: int = 7):
        end_date = datetime.fromisoformat(event_date).date()
        start_date = end_date - timedelta(days=lookback_days)

        return start_date.isoformat(), end_date.isoformat()

    def retrieve(
        self,
        symbol: str,
        event_date: str,
        event_type: str = "market_movement",
        trend: str = "UNKNOWN",
        sector: Optional[str] = None,
        top_k: int = 5,
        lookback_days: int = 7,
    ) -> List[Dict[str, Any]]:

        start_date, end_date = self._date_window(event_date, lookback_days)

        query = f"""
        Pakistan Stock Exchange news.
        Stock symbol: {symbol}
        Sector: {sector or "unknown"}
        Event type: {event_type}
        Trend: {trend}
        Find company news, sector news, market news, PSX announcements,
        earnings, financial results, investor sentiment and market movement reasons.
        """

        # 1. Same symbol news
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        if results:
            return results

        # 2. Same sector fallback
        if sector:
            results = self.vector_store.search(
                query=query,
                top_k=top_k,
                sector=sector,
                start_date=start_date,
                end_date=end_date,
            )

            if results:
                return results

        # 3. Market-wide fallback
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            symbol="KSE100",
            start_date=start_date,
            end_date=end_date,
        )

        if results:
            return results

        # 4. Wider fallback, 30 days
        wide_start_date, wide_end_date = self._date_window(event_date, 30)

        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            start_date=wide_start_date,
            end_date=wide_end_date,
        )

        return results


if __name__ == "__main__":
    retriever = RAGRetriever()

    results = retriever.retrieve(
        symbol="HBL",
        event_date="2026-05-08",
        event_type="price_down",
        trend="DOWN",
        sector="Banking",
        top_k=5,
        lookback_days=7,
    )

    print("\nRetrieved News:")
    for item in results:
        print("-" * 80)
        print("Date:", item.get("published_date"))
        print("Symbol:", item.get("symbol"))
        print("Source:", item.get("source"))
        print("Type:", item.get("news_type"))
        print("Score:", item.get("similarity_score"))
        print("Title:", item.get("title"))
        print("Article Length:", len(str(item.get("article_text", ""))))
        print("Summary:", str(item.get("summary", ""))[:300])
