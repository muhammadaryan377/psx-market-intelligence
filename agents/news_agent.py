"""
News Agent - Fetches news primarily from FAISS (retriever),
optionally from CSV loader, filters by last 7 days,
and generates a trading signal with recency weighting.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.append(str(Path(__file__).parent.parent))

class NewsAgent:
    def __init__(self):
        self.sentiment_analyzer = None
        try:
            from ml_models.sentiment_analyzer import sentiment_analyzer
            self.sentiment_analyzer = sentiment_analyzer
        except ImportError:
            pass

    def process(self, state):
        print("📰 News Agent: Fetching news (FAISS first, CSV fallback)...")

        market_data = state.get("market_data", {})
        symbol = market_data.get("symbol")
        news_signal = {
            'overall': 'neutral',
            'confidence': 50,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'key_headlines': []
        }

        if not symbol:
            state["news_data"] = []
            state["news_signal"] = news_signal
            return state

        # Use fixed simulation date if provided
        sim_date = state.get("simulation_date")
        current_date = sim_date if sim_date else datetime.now()

        # 1. Try FAISS first
        faiss_news = self._fetch_from_retriever(symbol, days_limit=7, current_date=current_date)

        if faiss_news:
            all_news = faiss_news
            print(f"   ✅ FAISS returned {len(faiss_news)} articles")
        else:
            # 2. Fallback to CSV loader
            csv_news = self._fetch_from_loader(symbol, days_limit=7, current_date=current_date) if self._use_csv() else []
            if csv_news:
                all_news = csv_news
                print(f"   ✅ CSV fallback returned {len(csv_news)} articles")
            else:
                # 3. Final fallback: mock news
                all_news = self._mock_news(symbol, current_date)
                print(f"   ⚠️ Using mock news for {symbol}")

        positive = negative = neutral = 0
        headlines = []
        total_weight = 0.0
        weighted_sentiment = 0.0

        for news in all_news:
            text = f"{news.get('title', '')} {news.get('content', '')} {news.get('summary', '')}"
            sentiment = self._analyze_sentiment(text)
            news['analyzed_sentiment'] = sentiment

            weight = self._get_recency_weight(news.get('date'), max_days=7, current_date=current_date)
            total_weight += weight

            sent_score = 1 if sentiment == 'positive' else (-1 if sentiment == 'negative' else 0)
            weighted_sentiment += sent_score * weight

            if sentiment == 'positive':
                positive += 1
            elif sentiment == 'negative':
                negative += 1
            else:
                neutral += 1

            if len(headlines) < 3:
                headlines.append({
                    'title': news.get('title', '')[:80],
                    'sentiment': sentiment,
                    'date': news.get('date', '')
                })

        total_articles = len(all_news)
        if total_articles > 0 and total_weight > 0:
            avg_sentiment = weighted_sentiment / total_weight
            if avg_sentiment > 0.3:
                overall = 'bullish'
                confidence = 60 + min(25, int(avg_sentiment * 40))
            elif avg_sentiment < -0.3:
                overall = 'bearish'
                confidence = 60 + min(25, int(abs(avg_sentiment) * 40))
            elif avg_sentiment > 0:
                overall = 'slightly_bullish'
                confidence = 55
            elif avg_sentiment < 0:
                overall = 'slightly_bearish'
                confidence = 55
            else:
                overall = 'neutral'
                confidence = 50
        else:
            overall = 'neutral'
            confidence = 50
            avg_sentiment = 0

        news_signal = {
            'overall': overall,
            'confidence': confidence,
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'key_headlines': headlines,
            'total_articles': total_articles,
            'avg_sentiment_score': round(avg_sentiment, 2)
        }

        state["news_data"] = all_news
        state["news_signal"] = news_signal
        state["current_step"] = "news_complete"

        print(f"   ✓ Final signal: {overall.upper()} ({confidence}%) based on {total_articles} articles")
        return state

    def _fetch_from_retriever(self, symbol, days_limit=7, current_date=None):
        """Fetch news from FAISS (via retriever) and filter by date"""
        if current_date is None:
            current_date = datetime.now()
        try:
            from rag_layer import get_rag
            rag = get_rag()
            if rag and hasattr(rag, 'search_by_symbol'):
                results = rag.search_by_symbol(symbol, k=15)
                # Sort results deterministically
                results = sorted(results, key=lambda x: (x.get('date', ''), x.get('title', '')))
                news = []
                cutoff = current_date - timedelta(days=days_limit)
                for item in results:
                    date_str = item.get('date', '')
                    pub_date = self._parse_date(date_str)
                    if pub_date and pub_date >= cutoff:
                        news.append({
                            'title': item.get('title', ''),
                            'content': item.get('content', item.get('summary', '')),
                            'source': item.get('source', 'FAISS'),
                            'date': item.get('date', ''),
                            'relevance_score': item.get('relevance_score', 0),
                            'type': 'faiss'
                        })
                return news
        except Exception as e:
            print(f"   ⚠️ FAISS retriever error: {e}")
        return []

    def _fetch_from_loader(self, symbol, days_limit=7, current_date=None):
        """Optional: fetch from CSV loader and filter by date"""
        if current_date is None:
            current_date = datetime.now()
        try:
            from rag_layer.news_loader import get_news_by_symbol
            import pandas as pd
            df = get_news_by_symbol(symbol, limit=15)
            if df.empty:
                return []
            cutoff = current_date - timedelta(days=days_limit)
            news = []
            for _, row in df.iterrows():
                date_str = row.get('date', '')
                pub_date = self._parse_date(date_str)
                if pub_date and pub_date >= cutoff:
                    news.append({
                        'title': row.get('title', ''),
                        'content': row.get('summary', row.get('content', '')),
                        'source': row.get('source', 'CSV'),
                        'date': date_str,
                        'type': 'csv'
                    })
            return news
        except Exception as e:
            print(f"   ⚠️ CSV loader error: {e}")
        return []

    def _merge_news(self, list1, list2):
        """Merge and deduplicate by title – deterministic order"""
        combined = sorted(list1 + list2, key=lambda x: (x.get('date', ''), x.get('title', '')))
        seen = set()
        unique = []
        for news in combined:
            title = news.get('title', '').lower().strip()
            if title and title not in seen:
                seen.add(title)
                unique.append(news)
        return unique

    def _mock_news(self, symbol, current_date=None):
        """Fallback mock – uses given current_date or real now"""
        if current_date is None:
            current_date = datetime.now()
        return [{
            "title": f"{symbol} stock active in today's trading",
            "content": f"Market shows interest in {symbol} shares.",
            "date": current_date.strftime("%Y-%m-%d"),
            "source": "Mock News"
        }]

    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%b %d, %Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _get_recency_weight(self, date_str, max_days=7, current_date=None):
        """Weight from 2.0 (today) down to 0.5 (7 days old)"""
        if current_date is None:
            current_date = datetime.now()
        pub_date = self._parse_date(date_str)
        if not pub_date:
            return 1.0
        days_ago = (current_date - pub_date).days
        if days_ago <= 1:
            return 2.0
        elif days_ago <= 3:
            return 1.5
        elif days_ago <= max_days:
            return 1.0
        else:
            return 0.5

    def _use_csv(self):
        """Decide whether to use CSV loader (default False)"""
        return False   # Change to True if you want CSV fallback

    def _analyze_sentiment(self, text):
        """ML or keyword sentiment"""
        if self.sentiment_analyzer:
            try:
                sentiment, _ = self.sentiment_analyzer.analyze(text)
                return sentiment
            except:
                pass
        # Keyword fallback
        pos_words = ['profit', 'gain', 'growth', 'positive', 'bullish', 'up', 'record', 'high', 'rise', 'increase']
        neg_words = ['loss', 'decline', 'negative', 'bearish', 'down', 'low', 'fall', 'drop', 'decrease', 'crash']
        text_lower = text.lower()
        pos = sum(1 for w in pos_words if w in text_lower)
        neg = sum(1 for w in neg_words if w in text_lower)
        if pos > neg:
            return 'positive'
        elif neg > pos:
            return 'negative'
        else:
            return 'neutral'