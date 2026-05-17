"""
News Collector - Collect news from RSS feeds and merge with existing CSV (append)
"""
import feedparser
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import hashlib

class NewsCollector:
    def __init__(self):
        self.news_file = Path("data/psx_news.csv")
        self.news_file.parent.mkdir(parents=True, exist_ok=True)
        
        # RSS Feeds
        self.rss_feeds = [
            {"name": "Dawn Business", "url": "https://www.dawn.com/feeds/business"},
            {"name": "Tribune", "url": "https://tribune.com.pk/feed/business"},
            {"name": "BR Recorder", "url": "https://www.brecorder.com/feed"},
        ]
    
    def collect_news(self, hours_back: int = 48) -> List[Dict]:
        """Collect news from RSS feeds"""
        all_news = []
        
        for feed in self.rss_feeds:
            try:
                parsed = feedparser.parse(feed['url'])
                
                for entry in parsed.entries[:20]:  # Latest 20 from each
                    # Extract data
                    news_item = {
                        "record_id": hashlib.md5(entry.get('link', '').encode()).hexdigest(),
                        "title": entry.get('title', ''),
                        "summary": entry.get('summary', '')[:500],
                        "url": entry.get('link', ''),
                        "date": self._parse_date(entry.get('published', '')),
                        "source": feed['name'],
                        "document_text": f"{entry.get('title', '')} {entry.get('summary', '')}"
                    }
                    
                    # Extract symbols from text
                    news_item['symbols'] = self._extract_symbols(news_item['document_text'])
                    
                    all_news.append(news_item)
                    
            except Exception as e:
                print(f"Error fetching {feed['name']}: {e}")
        
        # Remove duplicates by URL (within this batch)
        seen = set()
        unique_news = []
        for news in all_news:
            if news['url'] not in seen:
                seen.add(news['url'])
                unique_news.append(news)
        
        return unique_news
    
    def save_to_csv(self, news_list: List[Dict]):
        """Save or merge news list to CSV (append new, avoid duplicates)"""
        if not news_list:
            print("No news to save")
            return

        new_df = pd.DataFrame(news_list)
        
        # If file already exists, merge with existing data (avoid duplicates)
        if self.news_file.exists():
            existing_df = pd.read_csv(self.news_file)
            # Combine and drop duplicates based on 'url'
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined.drop_duplicates(subset=['url'], keep='first', inplace=True)
            combined.to_csv(self.news_file, index=False)
            print(f"✓ Merged {len(new_df)} new articles (total {len(combined)})")
        else:
            new_df.to_csv(self.news_file, index=False)
            print(f"✓ Saved {len(new_df)} news articles to {self.news_file}")
    
    def _extract_symbols(self, text: str) -> str:
        """Extract PSX symbols from text"""
        psx_symbols = ["SYS", "ENGRO", "LUCK", "HUBC", "FCCL", "MCB", "HBL", "UBL", 
                       "NRL", "POL", "PSO", "OGDC", "MARI", "EFERT", "NESTLE", "DAWH"]
        found = []
        text_upper = text.upper()
        for symbol in psx_symbols:
            if symbol in text_upper:
                found.append(symbol)
        return ",".join(found) if found else "MARKET"
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string"""
        try:
            from dateutil import parser
            dt = parser.parse(date_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def run(self):
        """Run the collector"""
        print("="*50)
        print("📰 News Collector Started")
        print("="*50)
        
        news = self.collect_news()
        self.save_to_csv(news)
        
        print(f"\n✅ Collection complete! Total: {len(news)} articles")
        return news

if __name__ == "__main__":
    collector = NewsCollector()
    collector.run()