"""
Stock Service - Dynamically fetches all PSX companies from PSX API
"""
import psxdata as psx
from typing import List, Dict, Any
import random

class StockService:
    def __init__(self):
        self._all_tickers = self._fetch_all_tickers()
        print(f"✅ StockService initialized with {len(self._all_tickers)} PSX companies")
    
    def _fetch_all_tickers(self) -> List[str]:
        """Fetch ALL PSX tickers dynamically from PSX API"""
        try:
            tickers = psx.tickers()
            if tickers and len(tickers) > 0:
                # Clean and sort
                tickers = [str(t).upper().strip() for t in tickers if t]
                tickers = sorted(list(set(tickers)))  # Remove duplicates
                return tickers
            else:
                print("⚠️ psx.tickers() returned empty, using fallback list")
                return self._fallback_tickers()
        except Exception as e:
            print(f"❌ Error fetching tickers: {e}")
            return self._fallback_tickers()
    
    def _fallback_tickers(self) -> List[str]:
        """Fallback list in case API fails"""
        return [
            'UBL', 'MCB', 'SYS', 'ENGRO', 'LUCK', 'HUBC', 'HBL', 'POL', 
            'FCCL', 'NRL', 'PSO', 'OGDC', 'MARI', 'EFERT', 'DAWH', 'INDU',
            'SEARL', 'FFC', 'KTML', 'NESTLE', 'AGIL', 'ATRL', 'CHCC', 'COLG',
            'DGKC', 'EPCL', 'FABL', 'FATIMA', 'GAL', 'GLAXO', 'HINO', 'IBLHL',
            'ICI', 'IML', 'ISL', 'KAPCO', 'KOHE', 'LINDE', 'LOTTE', 'MFL',
            'MLCF', 'NATF', 'NBP', 'NCPL', 'PAEL', 'PICT', 'PIF', 'PPL',
            'PRL', 'PSMC', 'PTC', 'SAZEW', 'SHEL', 'SING', 'SNGP', 'SSGC',
            'STCL', 'SZL', 'THALL', 'TOMCL', 'TPL', 'TREET', 'UNITY', 'WTL'
        ]
    
    def get_all_tickers(self) -> List[str]:
        """Return all PSX tickers"""
        return self._all_tickers
    
    def get_company_exists(self, symbol: str) -> bool:
        """Check if a symbol exists in PSX"""
        return symbol.upper() in self._all_tickers
    
    def search_companies(self, query: str, limit: int = 20) -> List[Dict]:
        """Search companies by symbol prefix or partial match"""
        query = query.upper()
        results = []
        for ticker in self._all_tickers:
            if query in ticker:
                results.append({'symbol': ticker, 'name': ticker})
                if len(results) >= limit:
                    break
        return results
    
    def get_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get symbol suggestions for auto-complete"""
        prefix = prefix.upper()
        suggestions = []
        for ticker in self._all_tickers:
            if ticker.startswith(prefix):
                suggestions.append(ticker)
                if len(suggestions) >= limit:
                    break
        return suggestions
    
    def get_historical_data(self, symbol: str, days: int = 100) -> List[float]:
        """Generate synthetic historical data for ML (if real not available)"""
        # This is a fallback. In production, you'd fetch real historical data.
        random.seed(hash(symbol) % 10000)
        prices = []
        base = random.uniform(100, 500)
        for i in range(days):
            change = random.uniform(-3, 3)
            base = base + change * 0.5
            prices.append(max(30, min(1000, base)))
        return prices

# Singleton instance
stock_service = StockService()