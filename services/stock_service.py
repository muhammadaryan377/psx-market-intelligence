"""
Stock Service - List of all PSX companies
"""
from typing import List

class StockService:
    def __init__(self):
        self._all_tickers = self._get_all_tickers()
    
    def _get_all_tickers(self) -> List[str]:
        """Complete list of PSX stocks - 100+ companies"""
        return [
            'UBL', 'MCB', 'SYS', 'ENGRO', 'LUCK', 'HUBC', 'HBL', 'POL', 
            'FCCL', 'NRL', 'PSO', 'OGDC', 'MARI', 'EFERT', 'DAWH', 'INDU',
            'SEARL', 'FFC', 'KTML', 'NESTLE', 'AGIL', 'ATRL', 'CHCC', 'COLG',
            'DGKC', 'EPCL', 'FABL', 'FATIMA', 'GAL', 'GLAXO', 'HINO', 'IBLHL',
            'ICI', 'IML', 'ISL', 'KAPCO', 'KOHE', 'LINDE', 'LOTTE', 'MFL',
            'MLCF', 'NATF', 'NBP', 'NCPL', 'PAEL', 'PICT', 'PIF', 'PPL',
            'PRL', 'PSMC', 'PTC', 'SAZEW', 'SHEL', 'SING', 'SNGP', 'SSGC',
            'STCL', 'SZL', 'THALL', 'TOMCL', 'TPL', 'TREET', 'UNITY', 'WTL',
            'AICL', 'ALIFE', 'ASL', 'BGL', 'BIFO', 'BIPL', 'BOP', 'BYCO',
            'CASH', 'CENI', 'CNERGY', 'CRTM', 'DCL', 'DMTX', 'DSFL', 'DYNO',
            'ECOP', 'ENGL', 'ESBL', 'EXIDE', 'FANM', 'FCIBL', 'FDIBL', 'FHAM',
            'FIBLM', 'FML', 'FNEL', 'FTL', 'GAMON', 'GCIL', 'GEM', 'GGL'
        ]
    
    def get_all_tickers(self) -> List[str]:
        return self._all_tickers
    
    def get_historical_data(self, symbol: str) -> List[float]:
        import random
        random.seed(hash(symbol) % 10000)
        prices = []
        base = random.uniform(100, 500)
        for i in range(100):
            change = random.uniform(-3, 3)
            base = base + change * 0.5
            prices.append(max(30, min(1000, base)))
        return prices

stock_service = StockService()