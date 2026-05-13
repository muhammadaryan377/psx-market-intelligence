"""News Agent - Fetches relevant news from various sources"""
from agents.state import AgentState, NewsItem
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Try to import optional dependencies with fallbacks
try:
    import feedparser
except ImportError:
    feedparser = None
    print("Warning: feedparser not installed. Install with: pip install feedparser")

try:
    import requests
except ImportError:
    requests = None
    print("Warning: requests not installed. Install with: pip install requests")

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    print("Warning: BeautifulSoup not installed. Install with: pip install beautifulsoup4")

class NewsAgent:
    """Agent responsible for fetching news"""
    
    def process(self, state: AgentState) -> AgentState:
        """Fetch news related to the stock"""
        print("📰 News Agent: Fetching news...")
        
        symbol = state.get("market_data", {}).get("symbol")
        news_list = []
        
        # Fetch from multiple sources
        sources = [
            self._fetch_dawn_news,
            self._fetch_tribune_news,
            self._fetch_brecorder_news
        ]
        
        for source in sources:
            try:
                news = source(symbol)
                news_list.extend(news)
            except Exception as e:
                state["errors"].append(f"News fetch error: {str(e)}")
        
        # Deduplicate and sort by relevance
        unique_news = self._deduplicate_news(news_list)
        unique_news.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        state["news_data"] = unique_news[:10]  # Keep top 10
        state["messages"].append({
            "agent": "NewsAgent",
            "content": f"Fetched {len(unique_news)} news articles",
            "timestamp": datetime.now().isoformat()
        })
        
        state["current_step"] = "news_fetching_complete"
        return state
    
    def _fetch_dawn_news(self, symbol: str = None) -> List[Dict]:
        """Fetch news from Dawn"""
        # Simulated news since we're using mock data
        news = []
        titles = [
            f"PSX hits record high as {symbol if symbol else 'market'} rallies",
            "Foreign investment flows into Pakistan's stock market",
            f"Analysts remain bullish on {symbol if symbol else 'banking sector'}"
        ]
        
        for title in titles:
            news.append({
                "title": title,
                "summary": f"Summary of {title.lower()}...",
                "source": "Dawn",
                "date": datetime.now().isoformat(),
                "relevance": random.uniform(0.5, 0.95),
                "sentiment": random.uniform(-0.5, 0.5)
            })
        
        return news
    
    def _fetch_tribune_news(self, symbol: str = None) -> List[Dict]:
        """Fetch news from Tribune"""
        return self._fetch_dawn_news(symbol)
    
    def _fetch_brecorder_news(self, symbol: str = None) -> List[Dict]:
        """Fetch news from Business Recorder"""
        return self._fetch_dawn_news(symbol)
    
    def _deduplicate_news(self, news_list: List[Dict]) -> List[Dict]:
        """Remove duplicate news articles"""
        seen_titles = set()
        unique = []
        for news in news_list:
            if news["title"] not in seen_titles:
                seen_titles.add(news["title"])
                unique.append(news)
        return unique
"""News Agent - Fetches relevant news from various sources"""
from agents.state import AgentState, NewsItem
from datetime import datetime, timedelta
import feedparser
import requests
from bs4 import BeautifulSoup
import random

class NewsAgent:
    """Agent responsible for fetching news"""
    
    def process(self, state: AgentState) -> AgentState:
        """Fetch news related to the stock"""
        print("📰 News Agent: Fetching news...")
        
        symbol = state.get("market_data", {}).get("symbol")
        news_list = []
        
        # Fetch from multiple sources
        sources = [
            self._fetch_dawn_news,
            self._fetch_tribune_news,
            self._fetch_brecorder_news
        ]
        
        for source in sources:
            try:
                news = source(symbol)
                news_list.extend(news)
            except Exception as e:
                state["errors"].append(f"News fetch error: {str(e)}")
        
        # Deduplicate and sort by relevance
        unique_news = self._deduplicate_news(news_list)
        unique_news.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        state["news_data"] = unique_news[:10]  # Keep top 10
        state["messages"].append({
            "agent": "NewsAgent",
            "content": f"Fetched {len(unique_news)} news articles",
            "timestamp": datetime.now().isoformat()
        })
        
        state["current_step"] = "news_fetching_complete"
        return state
    
    def _fetch_dawn_news(self, symbol: str = None) -> list:
        """Fetch news from Dawn"""
        # TODO: Implement actual RSS feed parsing
        # feed = feedparser.parse('https://www.dawn.com/feeds/business')
        
        # Simulated news
        news = []
        titles = [
            f"PSX hits record high as {symbol if symbol else 'market'} rallies",
            "Foreign investment flows into Pakistan's stock market",
            f"Analysts remain bullish on {symbol if symbol else 'banking sector'}"
        ]
        
        for title in titles:
            news.append(NewsItem(
                title=title,
                summary=f"Summary of {title.lower()}...",
                source="Dawn",
                date=datetime.now().isoformat(),
                relevance=random.uniform(0.5, 0.95),
                sentiment=random.uniform(-0.5, 0.5)
            ))
        
        return news
    
    def _fetch_tribune_news(self, symbol: str = None) -> list:
        """Fetch news from Tribune"""
        # Similar to above
        return self._fetch_dawn_news(symbol)  # Simplified
    
    def _fetch_brecorder_news(self, symbol: str = None) -> list:
        """Fetch news from Business Recorder"""
        return self._fetch_dawn_news(symbol)  # Simplified
    
    def _deduplicate_news(self, news_list: list) -> list:
        """Remove duplicate news articles"""
        seen_titles = set()
        unique = []
        for news in news_list:
            if news["title"] not in seen_titles:
                seen_titles.add(news["title"])
                unique.append(news)
        return unique