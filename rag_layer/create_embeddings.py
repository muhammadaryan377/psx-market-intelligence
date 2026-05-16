"""
Create embeddings and build FAISS index from news
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))

from rag_layer.vector_store import get_vector_store
from rag_layer.news_loader import load_news

def create_embeddings():
    """Build FAISS index from news articles"""
    print("="*50)
    print("🔨 Building FAISS Vector Index")
    print("="*50)
    
    # Step 1: Load news
    print("\n1️⃣ Loading news data...")
    df = load_news()
    
    if df.empty:
        print("❌ No news data found!")
        print("💡 Run news_collector.py first to collect news")
        return False
    
    # Step 2: Prepare documents
    print("\n2️⃣ Preparing documents for embedding...")
    documents = []
    metadatas = []
    
    for _, row in df.iterrows():
        # Create document text
        doc_text = f"Title: {row.get('title', '')}\nSummary: {row.get('summary', '')}\nContent: {row.get('content', '')}"
        documents.append(doc_text)
        
        # Store metadata
        metadatas.append({
            "title": row.get('title', ''),
            "summary": row.get('summary', '')[:300],
            "symbol": row.get('symbol', ''),
            "date": row.get('date', ''),
            "source": row.get('source', '')
        })
    
    # Step 3: Build FAISS index
    print("\n3️⃣ Building FAISS index...")
    vector_store = get_vector_store()
    vector_store.add_documents(documents, metadatas)
    
    # Step 4: Test search
    print("\n4️⃣ Testing search...")
    test_results = vector_store.search("UBL bank", k=3)
    
    print(f"\n✅ FAISS Index built successfully!")
    print(f"   - Documents indexed: {len(documents)}")
    print(f"   - Index dimension: {vector_store.dimension}")
    
    if test_results:
        print(f"\n📊 Test search results for 'UBL bank':")
        for doc, score in test_results:
            print(f"   - {doc.get('title', '')[:50]} (score: {score:.3f})")
    
    return True

if __name__ == "__main__":
    create_embeddings()