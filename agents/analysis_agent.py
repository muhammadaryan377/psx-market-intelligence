"""Analysis Agent - Performs technical analysis"""
from agents.state import AgentState
from datetime import datetime
import random

class AnalysisAgent:
    """Agent responsible for technical analysis"""
    
    def process(self, state: AgentState) -> AgentState:
        """Perform technical analysis on market data"""
        print("📈 Analysis Agent: Performing technical analysis...")
        
        market_data = state.get("market_data", {})
        
        if not market_data or "price" not in market_data:
            state["technical_analysis"] = {"error": "Insufficient data"}
            return state
        
        # Calculate technical indicators
        analysis = self._calculate_indicators(market_data)
        
        state["technical_analysis"] = analysis
        state["messages"].append({
            "agent": "AnalysisAgent",
            "content": f"Technical analysis complete. RSI: {analysis.get('rsi', 'N/A')}",
            "timestamp": datetime.now().isoformat()
        })
        
        state["current_step"] = "analysis_complete"
        return state
    
    def _calculate_indicators(self, data: dict) -> dict:
        """Calculate various technical indicators"""
        price = data.get("price", 100)
        
        # Simulate indicator calculations
        return {
            "rsi": random.randint(30, 70),
            "macd": round(random.uniform(-10, 10), 2),
            "moving_average_50": price * random.uniform(0.95, 1.05),
            "moving_average_200": price * random.uniform(0.9, 1.1),
            "bollinger_upper": price * 1.05,
            "bollinger_lower": price * 0.95,
            "support_levels": [price * 0.9, price * 0.85, price * 0.8],
            "resistance_levels": [price * 1.1, price * 1.15, price * 1.2],
            "trend": random.choice(["uptrend", "downtrend", "sideways"]),
            "volatility": random.uniform(0.1, 0.3)
        }