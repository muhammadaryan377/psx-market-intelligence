"""Data Agent - Collects market data from Kafka and APIs"""
import os
import json
import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from kafka import KafkaConsumer, KafkaProducer
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.state import AgentState

# Try to import config
try:
    from config.kafka_config import KAFKA_CONFIG, get_consumer_config
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("⚠️ Kafka config not found. Using mock data.")

class DataAgent:
    """Agent responsible for collecting market data from Kafka and APIs"""
    
    def __init__(self, use_kafka: bool = False):
        """
        Initialize Data Agent
        
        Args:
            use_kafka: Whether to connect to real Kafka (default False for testing)
        """
        self.use_kafka = use_kafka and KAFKA_AVAILABLE
        self.consumer = None
        
        if self.use_kafka:
            try:
                config = get_consumer_config()
                self.consumer = KafkaConsumer(
                    'psx-stock-trades',
                    bootstrap_servers=config['bootstrap_servers'],
                    group_id=config.get('group_id', 'psx-data-agent'),
                    auto_offset_reset='latest',
                    enable_auto_commit=True
                )
                print("✓ DataAgent connected to Kafka")
            except Exception as e:
                print(f"⚠️ Failed to connect to Kafka: {e}")
                self.use_kafka = False
        
        # Cache for market data
        self.data_cache = {}
        self.cache_expiry = 60  # seconds
        
        # PSX symbols database
        self.psx_symbols = {
            "SYS": "Systems Limited",
            "ENGRO": "Engro Corporation",
            "LUCK": "Lucky Cement",
            "HUBC": "Hub Power Company",
            "FCCL": "Fauji Cement",
            "MCB": "MCB Bank",
            "NRL": "National Refinery",
            "POL": "Pakistan Oilfields",
            "PSO": "Pakistan State Oil",
            "OGDC": "Oil & Gas Development Co"
        }
    
    def process(self, state: AgentState) -> AgentState:
        """Collect market data based on query"""
        print("📊 Data Agent: Collecting market data...")
        
        query = state.get("query", "")
        symbol = self._extract_symbol(state, query)
        
        if symbol and symbol in self.psx_symbols:
            # Fetch specific stock data
            market_data = self._fetch_market_data(symbol)
            state["market_data"] = market_data
            
            state["messages"].append({
                "agent": "DataAgent",
                "content": f"Retrieved market data for {symbol} ({self.psx_symbols[symbol]})",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "price": market_data.get("price"),
                    "change": market_data.get("change"),
                    "volume": market_data.get("volume")
                }
            })
        else:
            # Get market summary
            market_summary = self._fetch_market_summary()
            state["market_data"] = market_summary
            
            if not symbol:
                state["messages"].append({
                    "agent": "DataAgent",
                    "content": "Retrieved market summary",
                    "timestamp": datetime.now().isoformat(),
                    "data": market_summary
                })
            elif symbol not in self.psx_symbols:
                state["messages"].append({
                    "agent": "DataAgent",
                    "content": f"Symbol '{symbol}' not found. Showing market summary instead.",
                    "timestamp": datetime.now().isoformat(),
                    "error": True
                })
        
        state["current_step"] = "data_collection_complete"
        return state
    
    def _extract_symbol(self, state: AgentState, query: str) -> Optional[str]:
        """Extract stock symbol from state or query"""
        # First check if symbol is already in state
        if state.get("market_data") and state["market_data"].get("symbol"):
            return state["market_data"]["symbol"]
        
        # Try to extract from query
        words = query.upper().split()
        for word in words:
            # Check if word is a known PSX symbol
            if word in self.psx_symbols:
                return word
            # Check if word is 3-5 characters and all letters (potential symbol)
            if len(word) in [3, 4, 5] and word.isalpha() and word.isupper():
                return word
        
        return None
    
    def _fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time market data for a specific symbol"""
        
        # Check cache first
        cache_key = f"stock_{symbol}"
        if cache_key in self.data_cache:
            cached_time, cached_data = self.data_cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_expiry:
                return cached_data
        
        # Try to get from Kafka if enabled
        if self.use_kafka and self.consumer:
            try:
                # Poll for messages (non-blocking)
                messages = self.consumer.poll(timeout_ms=1000, max_records=1)
                for topic_partition, records in messages.items():
                    for record in records:
                        data = json.loads(record.value.decode('utf-8'))
                        if data.get('symbol') == symbol:
                            market_data = self._format_market_data(data)
                            self.data_cache[cache_key] = (datetime.now(), market_data)
                            return market_data
            except Exception as e:
                print(f"⚠️ Kafka read error: {e}")
        
        # Return simulated data (for testing without Kafka)
        return self._generate_simulated_data(symbol)
    
    def _generate_simulated_data(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic simulated market data"""
        base_price = {
            "SYS": 350.50,
            "ENGRO": 285.75,
            "LUCK": 450.30,
            "HUBC": 95.20,
            "FCCL": 42.15,
            "MCB": 165.80,
            "NRL": 320.40,
            "POL": 395.60,
            "PSO": 210.25,
            "OGDC": 125.50
        }.get(symbol, random.uniform(50, 500))
        
        # Add random movement
        change_percent = random.uniform(-3, 3)
        price = base_price * (1 + change_percent / 100)
        change = price - base_price
        
        return {
            "symbol": symbol,
            "company": self.psx_symbols.get(symbol, symbol),
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": random.randint(50000, 5000000),
            "high": round(price * (1 + random.uniform(0.01, 0.03)), 2),
            "low": round(price * (1 - random.uniform(0.01, 0.03)), 2),
            "open": round(price * (1 - random.uniform(0.005, 0.02)), 2),
            "prev_close": base_price,
            "timestamp": datetime.now().isoformat()
        }
    
    def _format_market_data(self, raw_data: Dict) -> Dict[str, Any]:
        """Format raw Kafka data into standard format"""
        return {
            "symbol": raw_data.get("symbol"),
            "company": self.psx_symbols.get(raw_data.get("symbol"), raw_data.get("symbol")),
            "price": raw_data.get("price", 0),
            "change": raw_data.get("change", 0),
            "change_percent": raw_data.get("change_percent", 0),
            "volume": raw_data.get("volume", 0),
            "high": raw_data.get("high", 0),
            "low": raw_data.get("low", 0),
            "timestamp": raw_data.get("timestamp", datetime.now().isoformat())
        }
    
    def _fetch_market_summary(self) -> Dict[str, Any]:
        """Fetch market summary with indices data"""
        
        # Check cache
        if "summary" in self.data_cache:
            cached_time, cached_data = self.data_cache["summary"]
            if (datetime.now() - cached_time).seconds < self.cache_expiry:
                return cached_data
        
        # Generate market summary
        kse_100_base = 45000
        kse_30_base = 17500
        
        # Add random movement
        kse_100_change = random.uniform(-1, 1)
        kse_30_change = random.uniform(-1, 1)
        
        summary = {
            "indices": {
                "KSE-100": {
                    "value": round(kse_100_base * (1 + kse_100_change / 100), 2),
                    "change": round(kse_100_base * kse_100_change / 100, 2),
                    "change_percent": round(kse_100_change, 2)
                },
                "KSE-30": {
                    "value": round(kse_30_base * (1 + kse_30_change / 100), 2),
                    "change": round(kse_30_base * kse_30_change / 100, 2),
                    "change_percent": round(kse_30_change, 2)
                },
                "KMI-30": {
                    "value": round(28000 * (1 + random.uniform(-0.5, 0.5) / 100), 2),
                    "change": round(random.uniform(-100, 100), 2),
                    "change_percent": round(random.uniform(-0.5, 0.5), 2)
                }
            },
            "market_status": "Closed" if datetime.now().hour < 9 or datetime.now().hour > 15 else "Open",
            "total_volume": random.randint(100000000, 500000000),
            "advancers": random.randint(50, 150),
            "decliners": random.randint(30, 100),
            "unchanged": random.randint(10, 30),
            "timestamp": datetime.now().isoformat()
        }
        
        # Cache the summary
        self.data_cache["summary"] = (datetime.now(), summary)
        
        return summary
    
    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """Get realtime price for a symbol (utility method)"""
        data = self._fetch_market_data(symbol)
        return data.get("price")
    
    def get_multiple_stocks(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Get data for multiple stocks"""
        results = []
        for symbol in symbols:
            results.append(self._fetch_market_data(symbol))
        return results
    
    def get_top_gainers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top gaining stocks"""
        # Simulate top gainers
        gainers = []
        for symbol in list(self.psx_symbols.keys())[:limit]:
            data = self._generate_simulated_data(symbol)
            if data.get("change_percent", 0) > 0:
                gainers.append(data)
        
        gainers.sort(key=lambda x: x.get("change_percent", 0), reverse=True)
        return gainers[:limit]
    
    def get_top_losers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top losing stocks"""
        losers = []
        for symbol in list(self.psx_symbols.keys())[:limit]:
            data = self._generate_simulated_data(symbol)
            if data.get("change_percent", 0) < 0:
                losers.append(data)
        
        losers.sort(key=lambda x: x.get("change_percent", 0))
        return losers[:limit]
    
    def clear_cache(self):
        """Clear data cache"""
        self.data_cache.clear()
        print("✓ Data cache cleared")

# Standalone test
if __name__ == "__main__":
    print("Testing Data Agent...")
    agent = DataAgent()
    
    # Test single stock
    result = agent._fetch_market_data("SYS")
    print(f"SYS: {result}")
    
    # Test market summary
    summary = agent._fetch_market_summary()
    print(f"Market: KSE-100 = {summary['indices']['KSE-100']['value']}")
    
    # Test with state
    test_state = {
        "query": "What is SYS price?",
        "messages": []
    }
    
    updated_state = agent.process(test_state)
    print(f"State updated: {updated_state.get('market_data', {})}")