"""
News Loader - Load news from CSV
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict

NEWS_FILE = Path("data/psx_news.csv")

def load_news() -> pd.DataFrame:
    """Load news from CSV file"""
    if NEWS_FILE.exists():
        df = pd.read_csv(NEWS_FILE)
        print(f"✓ Loaded {len(df)} news articles")
        return df
    else:
        print(f"⚠️ News file not found: {NEWS_FILE}")
        return pd.DataFrame()

def get_news_by_symbol(symbol: str, limit: int = 10) -> pd.DataFrame:
    """Get news for specific symbol"""
    df = load_news()
    if df.empty:
        return df
    
    # Filter by symbol
    symbol_news = df[df['symbols'].str.contains(symbol.upper(), na=False)]
    return symbol_news.head(limit)

def get_latest_news(limit: int = 20) -> pd.DataFrame:
    """Get latest news"""
    df = load_news()
    if df.empty:
        return df
    
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    return df.sort_values('date', ascending=False).head(limit)

def get_news_stats() -> Dict:
    """Get news statistics"""
    df = load_news()
    if df.empty:
        return {"total": 0}
    
    return {
        "total": len(df),
        "sources": df['source'].value_counts().to_dict(),
        "date_range": {
            "oldest": df['date'].min() if not df.empty else None,
            "newest": df['date'].max() if not df.empty else None
        }
    }