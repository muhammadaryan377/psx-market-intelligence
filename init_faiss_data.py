"""
Initialize FAISS with historical data - Run this ONCE
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from rag_layer.vector_store import get_vector_store

# Historical data for major PSX stocks
HISTORICAL_DATA = [
    # Banking
    {'symbol': 'UBL', 'price': 379.50, 'change': 2.50, 'change_pct': 0.66, 'sector': 'Banking', 'volume': 1250000, 'date': '2024-05-15'},
    {'symbol': 'MCB', 'price': 160.86, 'change': -4.92, 'change_pct': -2.98, 'sector': 'Banking', 'volume': 980000, 'date': '2024-05-15'},
    {'symbol': 'HBL', 'price': 274.85, 'change': 1.35, 'change_pct': 0.49, 'sector': 'Banking', 'volume': 1100000, 'date': '2024-05-15'},
    {'symbol': 'NBP', 'price': 52.30, 'change': -0.45, 'change_pct': -0.85, 'sector': 'Banking', 'volume': 750000, 'date': '2024-05-15'},
    
    # Technology
    {'symbol': 'SYS', 'price': 350.75, 'change': 5.25, 'change_pct': 1.52, 'sector': 'Technology', 'volume': 850000, 'date': '2024-05-15'},
    {'symbol': 'TPL', 'price': 45.80, 'change': -0.75, 'change_pct': -1.61, 'sector': 'Technology', 'volume': 320000, 'date': '2024-05-15'},
    {'symbol': 'WTL', 'price': 15.25, 'change': 0.15, 'change_pct': 0.99, 'sector': 'Technology', 'volume': 280000, 'date': '2024-05-15'},
    
    # Cement
    {'symbol': 'LUCK', 'price': 417.75, 'change': 2.55, 'change_pct': 0.61, 'sector': 'Cement', 'volume': 680000, 'date': '2024-05-15'},
    {'symbol': 'FCCL', 'price': 49.59, 'change': -0.41, 'change_pct': -0.82, 'sector': 'Cement', 'volume': 890000, 'date': '2024-05-15'},
    {'symbol': 'DGKC', 'price': 79.30, 'change': 0.85, 'change_pct': 1.08, 'sector': 'Cement', 'volume': 550000, 'date': '2024-05-15'},
    
    # Fertilizer
    {'symbol': 'ENGRO', 'price': 285.30, 'change': -1.20, 'change_pct': -0.42, 'sector': 'Fertilizer', 'volume': 720000, 'date': '2024-05-15'},
    {'symbol': 'EFERT', 'price': 85.40, 'change': 0.95, 'change_pct': 1.12, 'sector': 'Fertilizer', 'volume': 480000, 'date': '2024-05-15'},
    {'symbol': 'FFC', 'price': 112.60, 'change': -0.80, 'change_pct': -0.71, 'sector': 'Fertilizer', 'volume': 620000, 'date': '2024-05-15'},
    
    # Oil & Gas
    {'symbol': 'POL', 'price': 660.51, 'change': 2.31, 'change_pct': 0.35, 'sector': 'Oil & Gas', 'volume': 340000, 'date': '2024-05-15'},
    {'symbol': 'PSO', 'price': 354.14, 'change': -1.86, 'change_pct': -0.52, 'sector': 'Oil & Gas', 'volume': 580000, 'date': '2024-05-15'},
    {'symbol': 'OGDC', 'price': 125.50, 'change': 0.75, 'change_pct': 0.60, 'sector': 'Oil & Gas', 'volume': 920000, 'date': '2024-05-15'},
    {'symbol': 'MARI', 'price': 480.60, 'change': 3.40, 'change_pct': 0.71, 'sector': 'Oil & Gas', 'volume': 310000, 'date': '2024-05-15'},
    {'symbol': 'NRL', 'price': 381.97, 'change': -2.03, 'change_pct': -0.53, 'sector': 'Oil & Gas', 'volume': 270000, 'date': '2024-05-15'},
    
    # Energy
    {'symbol': 'HUBC', 'price': 95.20, 'change': 0.30, 'change_pct': 0.32, 'sector': 'Energy', 'volume': 1250000, 'date': '2024-05-15'},
    {'symbol': 'KAPCO', 'price': 32.45, 'change': -0.15, 'change_pct': -0.46, 'sector': 'Energy', 'volume': 680000, 'date': '2024-05-15'},
    
    # Automobile
    {'symbol': 'INDU', 'price': 1245.00, 'change': 15.00, 'change_pct': 1.22, 'sector': 'Automobile', 'volume': 145000, 'date': '2024-05-15'},
    {'symbol': 'PSMC', 'price': 685.50, 'change': -5.50, 'change_pct': -0.80, 'sector': 'Automobile', 'volume': 198000, 'date': '2024-05-15'},
    {'symbol': 'SAZEW', 'price': 445.20, 'change': 4.80, 'change_pct': 1.09, 'sector': 'Automobile', 'volume': 267000, 'date': '2024-05-15'},
    
    # Pharma
    {'symbol': 'SEARL', 'price': 72.45, 'change': 0.95, 'change_pct': 1.33, 'sector': 'Pharma', 'volume': 234000, 'date': '2024-05-15'},
    {'symbol': 'GLAXO', 'price': 115.30, 'change': -0.70, 'change_pct': -0.60, 'sector': 'Pharma', 'volume': 187000, 'date': '2024-05-15'},
    
    # Food
    {'symbol': 'NESTLE', 'price': 7025.00, 'change': 25.00, 'change_pct': 0.36, 'sector': 'Food', 'volume': 12500, 'date': '2024-05-15'},
    {'symbol': 'UNITY', 'price': 28.75, 'change': 0.25, 'change_pct': 0.88, 'sector': 'Food', 'volume': 345000, 'date': '2024-05-15'},
]

def main():
    print("="*50)
    print("📀 Initializing FAISS Vector Store with Historical Data")
    print("="*50)
    
    vector_store = get_vector_store()
    
    # Store bulk historical data
    vector_store.store_bulk_historical_data(HISTORICAL_DATA)
    
    # Show stats
    stats = vector_store.get_stats()
    print("\n📊 FAISS Store Statistics:")
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   Index size: {stats['index_size']}")
    print(f"   Dimension: {stats['dimension']}")
    print(f"   Stored symbols: {len(stats['stored_symbols'])}")
    
    print("\n✅ Initialization complete!")
    print("="*50)

if __name__ == "__main__":
    main()