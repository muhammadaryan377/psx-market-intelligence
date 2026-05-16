"""
Retriever - Main interface for news search
"""
from typing import List, Dict
from rag_layer.vector_store import get_vector_store
from rag_layer.news_loader import get_news_by_symbol, get_latest_news

class Retriever:
    """Main retriever interface for RAG"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
    
    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Semantic search using FAISS"""
        results = self.vector_store.search(query, k)
        
        formatted = []
        for doc, score in results:
            formatted.append({
                "title": doc.get('title', ''),
                "content": doc.get('summary', ''),
                "relevance_score": score,
                "date": doc.get('date', ''),
                "source": doc.get('source', ''),
                "symbols": doc.get('symbols', ''),
                "url": doc.get('url', '')
            })
        
        return formatted
    
    def search_by_symbol(self, symbol: str, k: int = 5) -> List[Dict]:
        """Search news for specific symbol"""
        query = f"{symbol} stock company news Pakistan PSX"
        return self.search(query, k)
    
    def get_news_for_symbol(self, symbol: str, limit: int = 5) -> List[Dict]:
        """Get news by symbol (direct match)"""
        df = get_news_by_symbol(symbol, limit)
        return df.to_dict('records')
    
    def get_latest(self, limit: int = 10) -> List[Dict]:
        """Get latest news"""
        df = get_latest_news(limit)
        return df.to_dict('records')

_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever