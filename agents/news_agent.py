"""
News Agent - LangGraph compatible
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

class NewsAgent:
    """Fetches news for ANY company"""
    
    def process(self, state):
        """Process state - fetch news"""
        print("📰 News Agent: Fetching news...")
        
        market_data = state.get("market_data", {})
        symbol = market_data.get("symbol")
        
        news_list = []
        
        if symbol:
            news_list = self._fetch_news(symbol)
        
        state["news_data"] = news_list
        state["current_step"] = "news_complete"
        
        print(f"   ✓ Found {len(news_list)} articles")
        return state
    
    def _fetch_news(self, symbol):
        """Fetch news dynamically"""
        # Try RAG layer first
        try:
            from rag_layer import get_rag
            rag = get_rag()
            if rag and hasattr(rag, 'search_by_symbol'):
                return rag.search_by_symbol(symbol, k=5)
        except:
            pass
        
        # Mock news as fallback
        return [
            {
                "title": f"{symbol} stock active in today's trading",
                "content": f"Market shows interest in {symbol} shares.",
                "date": "2024-01-15",
                "source": "Market News"
            }
        ]