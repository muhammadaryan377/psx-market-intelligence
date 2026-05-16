"""
Data Agent - LangGraph compatible
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

class DataAgent:
    """Fetches live market data for ANY PSX company"""
    
    def __init__(self):
        self.psx = None
        self.available = False
        
        try:
            import psxdata as psx
            self.psx = psx
            self.available = True
            print("✓ DataAgent: Live PSX ready")
        except:
            print("⚠️ DataAgent: PSX not available")
    
    def process(self, state):
        """Process state - fetch market data"""
        print("📊 Data Agent: Fetching live data...")
        
        query = state.get("query", "")
        symbol = self._extract_symbol(query)
        
        if not symbol:
            state["market_data"] = {"symbol": None, "price": "N/A", "found": False}
            return state
        
        # Fetch live quote
        quote = self._get_quote(symbol)
        state["market_data"] = quote
        
        if quote.get('found'):
            print(f"   ✓ {symbol}: PKR {quote.get('price', 'N/A')}")
        else:
            print(f"   ✗ {symbol}: Not found")
        
        state["current_step"] = "data_complete"
        return state
    
    def _extract_symbol(self, query):
        """Extract symbol from query dynamically"""
        words = query.upper().split()
        skip = ['WHAT', 'IS', 'PRICE', 'OF', 'FOR', 'THE', 'MARKET', 'SHOW', 'TELL', 'ME']
        
        for word in words:
            if len(word) >= 2 and len(word) <= 5 and word.isalpha() and word not in skip:
                return word
        return None
    
    def _get_quote(self, symbol):
        """Get live quote dynamically"""
        if not self.available:
            return {"symbol": symbol, "price": "N/A", "change": 0, "found": False}
        
        try:
            quote = self.psx.quote(symbol)
            
            if quote is None:
                return {"symbol": symbol, "found": False}
            
            if hasattr(quote, 'iloc') and len(quote) > 0:
                quote = quote.iloc[0]
            
            price = self._extract_value(quote, ['price', 'current_price', 'close', 'ltp'])
            change = self._extract_value(quote, ['change_percent', 'p_change', 'change'])
            
            return {
                "symbol": symbol,
                "price": price if price != 'N/A' else 'N/A',
                "change": change if change != 'N/A' else 0,
                "found": price != 'N/A'
            }
        except:
            return {"symbol": symbol, "found": False}
    
    def _extract_value(self, data, keys):
        for key in keys:
            try:
                val = data.get(key) if isinstance(data, dict) else getattr(data, key, None)
                if val is not None:
                    return round(val, 2) if isinstance(val, float) else val
            except:
                continue
        return 'N/A'