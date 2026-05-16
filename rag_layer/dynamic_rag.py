"""
Dynamic RAG - Main interface combining PSX data + News search
"""
import psxdata as psx
from datetime import datetime
from typing import Dict, List
from rag_layer.retriever import get_retriever

class DynamicRAG:
    """Complete RAG system with FAISS news search"""
    
    def __init__(self):
        self.retriever = get_retriever()
        self.all_tickers = []
        
        try:
            self.all_tickers = psx.tickers()
            print(f"✓ DynamicRAG: {len(self.all_tickers)} PSX companies")
        except:
            self.all_tickers = ["SYS", "ENGRO", "LUCK", "MCB", "HBL"]
    
    def process(self, state: Dict) -> Dict:
        """Process state and retrieve context"""
        print("🔍 RAG: Retrieving context...")
        
        query = state.get("query", "")
        symbol = state.get("market_data", {}).get("symbol", "")
        
        context = []
        
        # Search news
        if symbol:
            results = self.retriever.search_by_symbol(symbol, k=3)
        else:
            results = self.retriever.search(query, k=3)
        
        for item in results:
            context.append({
                "type": "news",
                "title": item.get('title', ''),
                "content": item.get('content', '')[:400],
                "relevance": item.get('relevance_score', 0.7),
                "date": item.get('date', ''),
                "source": item.get('source', '')
            })
        
        state["rag_context"] = context
        state["current_step"] = "rag_complete"
        
        print(f"   ✓ Retrieved {len(context)} news articles")
        return state

_rag = None

def get_rag():
    global _rag
    if _rag is None:
        _rag = DynamicRAG()
    return _rag