"""
Decision Agent - Final recommendation - LangGraph compatible
"""
class DecisionAgent:
    """Makes final recommendation"""
    
    def process(self, state):
        """Process state - make decision"""
        print("🎯 Decision Agent: Making decision...")
        
        market_data = state.get("market_data", {})
        sentiment = state.get("sentiment_analysis", {})
        technical = state.get("technical_analysis", {})
        
        symbol = market_data.get("symbol", "Unknown")
        price = market_data.get("price", 0)
        change = market_data.get("change", 0)
        
        sentiment_score = sentiment.get("score", 0)
        rsi = technical.get("rsi", 50)
        tech_overall = technical.get("overall", "NEUTRAL")
        
        # Calculate signals
        buy = 0
        sell = 0
        
        if sentiment_score > 0.2:
            buy += 1
        elif sentiment_score < -0.2:
            sell += 1
        
        if rsi < 30:
            buy += 2
        elif rsi > 70:
            sell += 2
        
        if tech_overall == "BULLISH":
            buy += 1
        elif tech_overall == "BEARISH":
            sell += 1
        
        if change != 'N/A' and change > 1:
            buy += 1
        elif change != 'N/A' and change < -1:
            sell += 1
        
        # Final decision
        if buy >= sell + 2:
            action = "STRONG BUY"
            confidence = 85
        elif buy > sell:
            action = "BUY"
            confidence = 70
        elif sell >= buy + 2:
            action = "STRONG SELL"
            confidence = 85
        elif sell > buy:
            action = "SELL"
            confidence = 65
        else:
            action = "HOLD"
            confidence = 50
        
        # Build recommendations
        recs = [
            f"🎯 {action} {symbol}",
            f"💰 Price: PKR {price} ({change:+.2f}%)" if price != 'N/A' else f"💰 Symbol: {symbol}",
            f"📊 Sentiment: {sentiment.get('overall_sentiment', 'stable').upper()}",
            f"📈 Technical: {tech_overall} | RSI: {rsi}",
            f"💡 Confidence: {confidence}%",
            "",
            "⚠️ Disclaimer: AI-generated advice"
        ]
        
        state["recommendations"] = recs
        state["confidence_score"] = confidence / 100
        state["current_step"] = "decision_complete"
        state["completed"] = True
        
        return state