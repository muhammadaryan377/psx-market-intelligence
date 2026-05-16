"""
Live PSX Data Service - Uses your existing live_psx.py logic
"""
import psxdata as psx
import time
from datetime import datetime

class LiveDataService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 10  # seconds
    
    def get_live_quote(self, symbol):
        """Get live quote for a symbol - same as live_psx.py"""
        symbol = symbol.upper()
        
        # Check cache
        if symbol in self.cache:
            cached_time, cached_data = self.cache[symbol]
            if (datetime.now() - cached_time).seconds < self.cache_duration:
                return cached_data
        
        try:
            # Same logic as your live_psx.py
            quote = psx.quote(symbol)
            
            if quote is None:
                return None
            
            if hasattr(quote, 'iloc') and len(quote) > 0:
                quote = quote.iloc[0]
            
            if hasattr(quote, 'get'):
                price = quote.get('current_price') or quote.get('price') or quote.get('close')
                change = quote.get('change') or quote.get('net_change')
                change_pct = quote.get('change_percent') or quote.get('p_change')
                volume = quote.get('volume') or quote.get('total_volume')
            else:
                price = getattr(quote, 'current_price', getattr(quote, 'price', None))
                change = getattr(quote, 'change', None)
                change_pct = getattr(quote, 'change_percent', None)
                volume = getattr(quote, 'volume', None)
            
            data = {
                'symbol': symbol,
                'price': float(price) if price else None,
                'change': float(change) if change else 0,
                'change_pct': float(change_pct) if change_pct else 0,
                'volume': volume,
                'timestamp': datetime.now().isoformat(),
                'found': price is not None
            }
            
            self.cache[symbol] = (datetime.now(), data)
            return data
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def get_all_live_data(self, symbols):
        """Get live data for multiple symbols"""
        results = []
        for symbol in symbols:
            data = self.get_live_quote(symbol)
            if data and data.get('found'):
                results.append(data)
        return results

live_service = LiveDataService()