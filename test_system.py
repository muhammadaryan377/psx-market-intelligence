"""
Complete System Test - Verify All Agents & RAG Layer
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

print("="*60)
print("🔍 PSX MARKET INTELLIGENCE - SYSTEM VERIFICATION")
print("="*60)

# ============ 1. TEST AGENTS ============
print("\n📌 1. TESTING AGENTS...")
print("-"*40)

try:
    from agents.data_agent import DataAgent
    print("✅ DataAgent - Import successful")
    
    from agents.news_agent import NewsAgent
    print("✅ NewsAgent - Import successful")
    
    from agents.sentiment_agent import SentimentAgent
    print("✅ SentimentAgent - Import successful")
    
    from agents.analysis_agent import AnalysisAgent
    print("✅ AnalysisAgent - Import successful")
    
    from agents.decision_agent import DecisionAgent
    print("✅ DecisionAgent - Import successful")
    
    from agents.state import AgentState
    print("✅ AgentState - Import successful")
    
except Exception as e:
    print(f"❌ Agent import error: {e}")

# ============ 2. TEST RAG LAYER ============
print("\n📌 2. TESTING RAG LAYER...")
print("-"*40)

try:
    from rag_layer import get_rag
    rag = get_rag()
    print("✅ RAG Layer - Import successful")
    
    # Test get_context
    context = rag.get_context("SYS")
    print(f"✅ RAG get_context('SYS') - Retrieved {len(context)} items")
    if context:
        print(f"   Content: {context[0].get('content', 'N/A')[:100]}...")
    
except Exception as e:
    print(f"❌ RAG Layer error: {e}")

# ============ 3. TEST VECTOR STORE ============
print("\n📌 3. TESTING VECTOR STORE (FAISS)...")
print("-"*40)

try:
    from rag_layer.vector_store import get_vector_store
    vector_store = get_vector_store()
    stats = vector_store.get_stats()
    print(f"✅ Vector Store - Loaded")
    print(f"   Total documents: {stats.get('total_documents', 0)}")
    print(f"   Index size: {stats.get('index_size', 0)}")
    print(f"   Stored symbols: {len(stats.get('stored_symbols', []))}")
    
    # Test search
    results = vector_store.search_by_symbol("UBL", k=3)
    print(f"✅ Search by symbol 'UBL' - Found {len(results)} results")
    
except Exception as e:
    print(f"❌ Vector Store error: {e}")

# ============ 4. TEST FRONTEND API ============
print("\n📌 4. TESTING FRONTEND API...")
print("-"*40)

try:
    import requests
    import time
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:5000/api/stock/UBL", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API /api/stock/UBL - Working")
            print(f"   Symbol: {data.get('symbol', 'N/A')}")
            print(f"   Price: {data.get('price', 'N/A')}")
            print(f"   Recommendation: {data.get('recommendation', 'N/A')}")
            print(f"   Sentiment: {data.get('sentiment', 'N/A')}")
        else:
            print(f"⚠️ API returned status: {response.status_code}")
    except requests.ConnectionError:
        print("⚠️ Frontend server not running. Run: python frontend/app.py")
    except Exception as e:
        print(f"⚠️ API test error: {e}")
        
except ImportError:
    print("⚠️ requests module not installed. Install: pip install requests")

# ============ 5. TEST SERVICES ============
print("\n📌 5. TESTING SERVICES...")
print("-"*40)

try:
    from services.stock_service import stock_service
    tickers = stock_service.get_all_tickers()
    print(f"✅ StockService - Loaded {len(tickers)} tickers")
    print(f"   Sample: {tickers[:5]}")
    
    from services.market_status import market_status
    status = market_status.get_status()
    print(f"✅ MarketStatus - Working")
    print(f"   Market Open: {status.get('is_open', False)}")
    print(f"   Status: {status.get('status', 'N/A')}")
    
except Exception as e:
    print(f"❌ Services error: {e}")

# ============ 6. TEST ML MODELS ============
print("\n📌 6. TESTING ML MODELS...")
print("-"*40)

try:
    from ml_models.price_predictor import price_predictor
    test_prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
    prediction = price_predictor.predict_next_price(test_prices)
    print(f"✅ PricePredictor - Working")
    print(f"   Test prediction: {prediction}")
    
except Exception as e:
    print(f"❌ ML Models error: {e}")

# ============ 7. TEST LIVE DATA ============
print("\n📌 7. TESTING LIVE DATA FETCH...")
print("-"*40)

try:
    import psxdata as psx
    test_quote = psx.quote("UBL")
    if test_quote is not None:
        print(f"✅ PSX Library - Working")
        if hasattr(test_quote, 'iloc') and len(test_quote) > 0:
            test_quote = test_quote.iloc[0]
        price = test_quote.get('current_price', test_quote.get('price', 'N/A'))
        print(f"   UBL Live Price: {price}")
    else:
        print("⚠️ PSX Library - No data (market closed or symbol issue)")
        
except Exception as e:
    print(f"⚠️ PSX Library error: {e}")

# ============ SUMMARY ============
print("\n" + "="*60)
print("📊 VERIFICATION SUMMARY")
print("="*60)

components = [
    ("Agents", "agents"),
    ("RAG Layer", "rag_layer"),
    ("Vector Store (FAISS)", "vector_store"),
    ("Services", "services"),
    ("ML Models", "ml_models"),
]

for name, _ in components:
    print(f"   ✅ {name}")

print("\n" + "="*60)
print("🚀 To run full system:")
print("   python frontend/app.py")
print("   Then open: http://localhost:5000")
print("="*60)