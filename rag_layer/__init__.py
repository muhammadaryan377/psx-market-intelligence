"""
RAG Layer - Context retrieval with FAISS
"""
from typing import Dict, Any, List
from rag_layer.vector_store import get_vector_store

class RAGLayer:
    def __init__(self):
        self.vector_store = get_vector_store()
        self.knowledge = {
            'SYS': 'Systems Limited - IT services company',
            'ENGRO': 'Engro Corporation - Diversified conglomerate',
            'LUCK': 'Lucky Cement - Cement manufacturer',
            'UBL': 'United Bank Limited - Commercial bank',
            'MCB': 'MCB Bank - Private bank',
            'HUBC': 'Hub Power Company - Power generation'
        }
    
    def get_context(self, symbol: str) -> List[Dict]:
        symbol = symbol.upper()
        
        # First try to get from FAISS
        results = self.vector_store.search_by_symbol(symbol, k=3)
        
        context = []
        for doc, score in results:
            context.append({
                'type': 'stored_data',
                'content': f"{doc.get('symbol')} - Price: PKR {doc.get('price')}, Change: {doc.get('change_pct')}%",
                'relevance': score,
                'source': 'faiss_storage'
            })
        
        # If no FAISS data, use knowledge base
        if not context and symbol in self.knowledge:
            context.append({
                'type': 'company_info',
                'content': self.knowledge[symbol],
                'relevance': 0.95,
                'source': 'knowledge_base'
            })
        
        # Fallback
        if not context:
            context.append({
                'type': 'general',
                'content': f'{symbol} is listed on Pakistan Stock Exchange',
                'relevance': 0.5,
                'source': 'general'
            })
        
        return context
    
    def process(self, state: Dict) -> Dict:
        print("🔍 RAG Layer: Retrieving context...")
        symbol = state.get('market_data', {}).get('symbol', '')
        context = self.get_context(symbol)
        state['rag_context'] = context
        state['current_step'] = 'rag_complete'
        print(f"   ✓ Retrieved {len(context)} context items")
        return state

_rag = None

def get_rag():
    global _rag
    if _rag is None:
        _rag = RAGLayer()
    return _rag