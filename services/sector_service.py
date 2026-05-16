"""
Sector Service - Company segregation
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List

class SectorService:
    def __init__(self):
        self.sector_file = Path("data/sector_mapping.csv")
        self._create_default_mapping()
        self.df = self._load_data()
    
    def _create_default_mapping(self):
        """Create default sector mapping file if not exists"""
        if self.sector_file.exists():
            return
        
        self.sector_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = [
            ["UBL", "United Bank Limited", "Banking", "Commercial"],
            ["MCB", "MCB Bank", "Banking", "Commercial"],
            ["HBL", "Habib Bank Limited", "Banking", "Commercial"],
            ["SYS", "Systems Limited", "Technology", "IT Services"],
            ["ENGRO", "Engro Corporation", "Fertilizer", "Chemicals"],
            ["LUCK", "Lucky Cement", "Cement", "Construction"],
            ["HUBC", "Hub Power Company", "Energy", "Power Generation"],
            ["FCCL", "Fauji Cement", "Cement", "Construction"],
            ["NRL", "National Refinery", "Oil & Gas", "Refinery"],
            ["POL", "Pakistan Oilfields", "Oil & Gas", "Exploration"],
            ["PSO", "Pakistan State Oil", "Oil & Gas", "Marketing"],
            ["OGDC", "Oil & Gas Development", "Oil & Gas", "Exploration"],
            ["MARI", "Mari Petroleum", "Oil & Gas", "Exploration"],
            ["EFERT", "Engro Fertilizers", "Fertilizer", "Production"],
            ["NBP", "National Bank", "Banking", "Government"],
            ["DAWH", "Dawn", "Media", "Publishing"],
            ["INDU", "Indus Motor", "Automobile", "Manufacturing"],
            ["SEARL", "Searle", "Pharma", "Healthcare"],
            ["FFC", "Fauji Fertilizer", "Fertilizer", "Production"],
            ["KTML", "Kot Addu Power", "Energy", "Power Generation"],
        ]
        
        df = pd.DataFrame(data, columns=["symbol", "company", "sector", "sub_sector"])
        df.to_csv(self.sector_file, index=False)
        print(f"✅ Created sector mapping with {len(data)} companies")
    
    def _load_data(self):
        return pd.read_csv(self.sector_file)
    
    def get_companies_by_sector(self, sector: str) -> List[Dict]:
        filtered = self.df[self.df["sector"] == sector]
        return filtered.to_dict("records")
    
    def get_sectors_with_companies(self) -> Dict:
        result = {}
        for sector in self.df["sector"].unique():
            result[sector] = self.get_companies_by_sector(sector)
        return result
    
    def get_company_info(self, symbol: str) -> Dict:
        row = self.df[self.df["symbol"] == symbol.upper()]
        if not row.empty:
            return row.iloc[0].to_dict()
        return {}

# Create instance
sector_service = SectorService()