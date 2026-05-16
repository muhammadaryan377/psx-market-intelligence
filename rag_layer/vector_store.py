"""
Vector Store - FAISS based vector database for storing news and historical data
"""
import faiss
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime
import json

# Try to import sentence_transformers, but don't fail
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    print("⚠️ sentence_transformers not available. Install: pip install sentence-transformers")
    # Create dummy class
    class SentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass
        def encode(self, *args, **kwargs):
            return np.random.randn(1, 384)
        def get_sentence_embedding_dimension(self):
            return 384

import warnings
warnings.filterwarnings('ignore')

class FAISSVectorStore:
    """FAISS vector store for news and historical data"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.index_dir = Path("data/vector_index")
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.index_dir / "faiss.index"
        self.metadata_file = self.index_dir / "metadata.pkl"
        
        try:
            self.model = SentenceTransformer(model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            print("✓ FAISS Vector Store initialized")
        except:
            print("⚠️ SentenceTransformer not available, using fallback")
            self.model = None
            self.dimension = 384
        
        self.index = None
        self.metadata = []
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        if self.index_file.exists() and self.metadata_file.exists():
            self.index = faiss.read_index(str(self.index_file))
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
            print(f"✓ Loaded FAISS index with {len(self.metadata)} documents")
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            print("✓ Created new FAISS index")
    
    def add_documents(self, documents: List[str], metadatas: List[Dict]):
        if not documents or self.model is None:
            return
        
        embeddings = self.model.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        self.index.add(embeddings.astype('float32'))
        self.metadata.extend(metadatas)
        self._save()
        print(f"✓ Added {len(documents)} documents to FAISS index")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[Dict, float]]:
        if self.index.ntotal == 0 or self.model is None:
            return []
        
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        
        scores, indices = self.index.search(query_embedding.astype('float32'), k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.metadata):
                results.append((self.metadata[idx], float(score)))
        
        return results
    
    def search_by_symbol(self, symbol: str, k: int = 5) -> List[Tuple[Dict, float]]:
        query = f"{symbol} stock company news financial performance Pakistan PSX"
        return self.search(query, k)
    
    def get_historical_data(self, symbol: str) -> List[float]:
        """Get historical price data from stored documents"""
        results = self.search(f"{symbol} price history", k=10)
        prices = []
        for doc, score in results:
            if doc.get('type') == 'price_history' and doc.get('symbol') == symbol:
                prices.append(doc.get('price', 0))
        return prices if prices else None
    
    def store_price_data(self, symbol: str, price: float, date: str):
        """Store historical price data"""
        doc_text = f"{symbol} price on {date} was PKR {price}"
        metadata = {
            'type': 'price_history',
            'symbol': symbol,
            'price': price,
            'date': date,
            'timestamp': datetime.now().isoformat()
        }
        self.add_documents([doc_text], [metadata])
    
    def store_bulk_historical_data(self, data_list: List[Dict]):
        """Store bulk historical data"""
        documents = []
        metadatas = []
        
        for item in data_list:
            doc_text = f"{item['symbol']} - {item.get('sector', 'N/A')} sector. Price: PKR {item['price']}. Change: {item.get('change_pct', 0)}%"
            documents.append(doc_text)
            metadatas.append({
                'symbol': item['symbol'],
                'sector': item.get('sector', 'N/A'),
                'price': item['price'],
                'change': item.get('change', 0),
                'change_pct': item.get('change_pct', 0),
                'volume': item.get('volume', 0),
                'date': item.get('date', datetime.now().strftime("%Y-%m-%d")),
                'type': 'price_history',
                'timestamp': datetime.now().isoformat()
            })
        
        self.add_documents(documents, metadatas)
        print(f"✓ Stored {len(data_list)} price records in FAISS")
    
    def get_stored_symbols(self) -> List[str]:
        """Get all symbols stored in FAISS"""
        symbols = set()
        for doc in self.metadata:
            if doc.get('symbol'):
                symbols.add(doc['symbol'])
        return list(symbols)
    
    def _save(self):
        if self.index is not None and self.index.ntotal > 0:
            faiss.write_index(self.index, str(self.index_file))
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
    
    def get_stats(self) -> Dict:
        return {
            "total_documents": len(self.metadata),
            "index_size": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "stored_symbols": self.get_stored_symbols()
        }

_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = FAISSVectorStore()
    return _vector_store