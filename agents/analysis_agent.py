"""
Analysis Agent - Technical Analysis - LangGraph compatible
"""
class AnalysisAgent:
    """Performs technical analysis"""
    
    def process(self, state):
        """Process state - technical analysis"""
        print("📈 Analysis Agent: Technical analysis...")
        
        market_data = state.get("market_data", {})
        price = market_data.get("price", 0)
        change = market_data.get("change", 0)
        
        if isinstance(price, str) or price == 0:
            price = 100
        if isinstance(change, str):
            change = 0
        
        # Calculate RSI (simulated)
        if change > 2:
            rsi = 75
        elif change > 0:
            rsi = 55
        elif change < -2:
            rsi = 25
        elif change < 0:
            rsi = 45
        else:
            rsi = 50
        
        # Determine trend
        if change > 1.5:
            trend = "strong_uptrend"
        elif change > 0.5:
            trend = "uptrend"
        elif change < -1.5:
            trend = "strong_downtrend"
        elif change < -0.5:
            trend = "downtrend"
        else:
            trend = "sideways"
        
        # Support/Resistance
        if price != 'N/A' and price != 0:
            support = round(price * 0.95, 2)
            resistance = round(price * 1.05, 2)
        else:
            support = 0
            resistance = 0
        
        state["technical_analysis"] = {
            "rsi": rsi,
            "rsi_signal": "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral",
            "trend": trend,
            "momentum": round(change, 2),
            "support": support,
            "resistance": resistance,
            "overall": "BULLISH" if change > 1 else "BEARISH" if change < -1 else "NEUTRAL"
        }
        
        print(f"   ✓ RSI: {rsi} | Trend: {trend}")
        state["current_step"] = "analysis_complete"
        return state