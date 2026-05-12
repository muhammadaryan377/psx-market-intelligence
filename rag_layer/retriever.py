import argparse
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag_layer.vector_store import NewsVectorStore


class RAGRetriever:
    def __init__(self):
        self._vector_store: Optional[NewsVectorStore] = None

    @property
    def vector_store(self) -> NewsVectorStore:
        if self._vector_store is None:
            self._vector_store = NewsVectorStore()

        return self._vector_store

    def _date_window(self, event_date: str, lookback_days: int = 7):
        end_date = datetime.fromisoformat(str(event_date)[:10]).date()
        start_date = end_date - timedelta(days=lookback_days)

        return start_date.isoformat(), end_date.isoformat()

    def _company_for_symbol(self, symbol: str) -> Optional[str]:
        symbol = str(symbol or "").upper().strip()

        if not symbol:
            return None

        companies = [
            str(item.get("company", "")).strip()
            for item in self.vector_store.metadata
            if str(item.get("symbol", "")).upper().strip() == symbol
            and str(item.get("company", "")).strip()
        ]

        if not companies:
            return None

        return Counter(companies).most_common(1)[0][0]

    def _item_key(self, item: Dict[str, Any]) -> str:
        record_id = str(item.get("record_id", "")).strip()

        if record_id:
            return record_id

        return "|".join([
            str(item.get("published_date", ""))[:10],
            str(item.get("symbol", "")),
            str(item.get("title", "")),
            str(item.get("original_url", "") or item.get("url", "")),
        ])

    def _add_results(
        self,
        collected: List[Dict[str, Any]],
        seen_keys: set,
        new_results: List[Dict[str, Any]],
        retrieval_scope: str,
        top_k: int,
    ) -> None:
        for item in new_results:
            key = self._item_key(item)

            if key in seen_keys:
                continue

            enriched_item = item.copy()
            enriched_item["retrieval_scope"] = retrieval_scope
            collected.append(enriched_item)
            seen_keys.add(key)

        collected.sort(
            key=lambda item: (
                item.get("final_score", 0.0),
                item.get("similarity_score", 0.0),
            ),
            reverse=True,
        )

        del collected[top_k:]

    def retrieve(
        self,
        symbol: str,
        event_date: str,
        event_type: str = "market_movement",
        trend: str = "UNKNOWN",
        sector: Optional[str] = None,
        company: Optional[str] = None,
        top_k: int = 5,
        lookback_days: int = 7,
    ) -> List[Dict[str, Any]]:

        start_date, end_date = self._date_window(event_date, lookback_days)

        try:
            vector_store = self.vector_store
        except Exception as exc:
            print(f"RAG retriever unavailable: {exc}")
            return []

        company = company or self._company_for_symbol(symbol)

        query = f"""
        Pakistan Stock Exchange news.
        Stock symbol: {symbol}
        Company: {company or "unknown"}
        Sector: {sector or "unknown"}
        Event type: {event_type}
        Trend: {trend}
        Find company news, sector news, market news, PSX announcements,
        earnings, financial results, investor sentiment and market movement reasons.
        """

        collected: List[Dict[str, Any]] = []
        seen_keys = set()

        # 1. Same symbol news with strict quality filters.
        same_symbol_results = vector_store.search(
            query=query,
            top_k=top_k,
            symbol=symbol,
            sector=sector,
            company=company,
            query_symbol=symbol,
            query_sector=sector,
            start_date=start_date,
            end_date=end_date,
        )
        self._add_results(
            collected,
            seen_keys,
            same_symbol_results,
            retrieval_scope="company_specific",
            top_k=top_k,
        )

        if len(collected) >= top_k:
            return collected

        # 2. Same sector fallback
        if sector:
            same_sector_results = vector_store.search(
                query=query,
                top_k=top_k,
                sector=sector,
                company=company,
                query_symbol=symbol,
                query_sector=sector,
                start_date=start_date,
                end_date=end_date,
            )
            self._add_results(
                collected,
                seen_keys,
                same_sector_results,
                retrieval_scope="sector",
                top_k=top_k,
            )

            if len(collected) >= top_k:
                return collected

        # 3. Market-wide fallback
        kse100_results = vector_store.search(
            query=query,
            top_k=top_k,
            symbol="KSE100",
            company=company,
            query_symbol=symbol,
            query_sector=sector,
            start_date=start_date,
            end_date=end_date,
        )
        self._add_results(
            collected,
            seen_keys,
            kse100_results,
            retrieval_scope="market_wide",
            top_k=top_k,
        )

        if len(collected) >= top_k:
            return collected

        market_news_results = vector_store.search(
            query=query,
            top_k=top_k,
            company=company,
            query_symbol=symbol,
            query_sector=sector,
            start_date=start_date,
            end_date=end_date,
            news_type="market_news",
        )
        self._add_results(
            collected,
            seen_keys,
            market_news_results,
            retrieval_scope="market_wide",
            top_k=top_k,
        )

        if len(collected) >= top_k:
            return collected

        # 4. Wider fallback, 30 days
        wide_start_date, wide_end_date = self._date_window(event_date, 30)

        wide_symbol_results = vector_store.search(
            query=query,
            top_k=top_k,
            symbol=symbol,
            sector=sector,
            company=company,
            query_symbol=symbol,
            query_sector=sector,
            start_date=wide_start_date,
            end_date=wide_end_date,
        )
        self._add_results(
            collected,
            seen_keys,
            wide_symbol_results,
            retrieval_scope="wide_company_specific",
            top_k=top_k,
        )

        if len(collected) >= top_k:
            return collected

        if sector:
            wide_sector_results = vector_store.search(
                query=query,
                top_k=top_k,
                sector=sector,
                company=company,
                query_symbol=symbol,
                query_sector=sector,
                start_date=wide_start_date,
                end_date=wide_end_date,
            )
            self._add_results(
                collected,
                seen_keys,
                wide_sector_results,
                retrieval_scope="wide_sector",
                top_k=top_k,
            )

            if len(collected) >= top_k:
                return collected

        wide_market_results = vector_store.search(
            query=query,
            top_k=top_k,
            company=company,
            query_symbol=symbol,
            query_sector=sector,
            start_date=wide_start_date,
            end_date=wide_end_date,
        )
        self._add_results(
            collected,
            seen_keys,
            wide_market_results,
            retrieval_scope="wide_market",
            top_k=top_k,
        )

        return collected

    def query(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            return self.vector_store.search(query=query, top_k=top_k)
        except Exception as exc:
            print(f"RAG query failed: {exc}")
            return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the PSX RAG retriever")
    parser.add_argument(
        "query",
        nargs="?",
        default="HBL price down reason",
        help="Free-text news query",
    )
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    retriever = RAGRetriever()
    results = retriever.query(args.query, top_k=args.top_k)

    print("\nRetrieved News:")
    for item in results:
        print("-" * 80)
        print("Date:", item.get("published_date"))
        print("Symbol:", item.get("symbol"))
        print("Sector:", item.get("sector"))
        print("Source:", item.get("source"))
        print("Type:", item.get("news_type"))
        print("Similarity Score:", item.get("similarity_score"))
        print("Final Score:", item.get("final_score"))
        print("Title:", item.get("title"))
        print("Article Length:", len(str(item.get("article_text", ""))))
