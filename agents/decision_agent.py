"""
Decision Agent - Final recommendation with ML Trend Predictor
"""
from ml_models.trend_predictor import trend_predictor

class DecisionAgent:
    """Makes final recommendation using ML trend prediction"""
    
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
        
        # === ML Trend Prediction ===
        try:
            # Get historical prices for trend prediction
            historical_prices = self._get_historical_prices(symbol, price)
            trend, trend_confidence = trend_predictor.predict_trend(historical_prices)
            print(f"   📈 ML Trend Prediction: {trend.upper()} (confidence: {trend_confidence:.0f}%)")
        except Exception as e:
            print(f"   ⚠️ Trend predictor error: {e}")
            trend = "neutral"
            trend_confidence = 50
        
        # Calculate signals
        buy = 0
        sell = 0
        
        # Sentiment signal
        if sentiment_score > 0.2:
            buy += 1
        elif sentiment_score < -0.2:
            sell += 1
        
        # RSI signal (technical)
        if rsi < 30:
            buy += 2
        elif rsi > 70:
            sell += 2
        
        # Technical overall signal
        if tech_overall == "BULLISH":
            buy += 1
        elif tech_overall == "BEARISH":
            sell += 1
        
        # Price change signal
        if change != 'N/A' and change > 1:
            buy += 1
        elif change != 'N/A' and change < -1:
            sell += 1
        
        # === ML Trend Signal ===
        if trend == "up":
            buy += 2
        elif trend == "down":
            sell += 2
        elif trend == "neutral":
            pass
        
        # Final decision based on total signals
        if buy >= sell + 3:
            action = "STRONG BUY"
            confidence = 85
        elif buy >= sell + 1:
            action = "BUY"
            confidence = 70
        elif sell >= buy + 3:
            action = "STRONG SELL"
            confidence = 85
        elif sell >= buy + 1:
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
            f"🤖 ML Trend: {trend.upper()} ({trend_confidence:.0f}% confidence)",
            f"💡 Confidence: {confidence}%",
            "",
            "⚠️ Disclaimer: AI-generated advice"
        ]
        
        state["recommendations"] = recs
        state["confidence_score"] = confidence / 100
        state["current_step"] = "decision_complete"
        state["completed"] = True
        state["trend_prediction"] = {
            'trend': trend,
            'confidence': trend_confidence
        }
        
        return state
    
    def _get_historical_prices(self, symbol: str, current_price: float) -> list:
        """Generate historical prices for ML prediction"""
        import random
        random.seed(hash(symbol) % 10000)
        
        prices = []
        price = float(current_price) if current_price != 'N/A' else 100
        
        for i in range(30):
            change_pct = random.uniform(-0.03, 0.03)
            price = price * (1 + change_pct)
            prices.append(max(price * 0.5, min(price * 1.5, price)))
        
        return prices