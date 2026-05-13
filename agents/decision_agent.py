"""Decision Agent - Makes final trading/investment decisions"""
from agents.state import AgentState
from datetime import datetime
import random

class DecisionAgent:
    """Agent responsible for final decision making"""
    
    def process(self, state: AgentState) -> AgentState:
        """Make final decision based on all analyses"""
        print("🎯 Decision Agent: Making final recommendation...")
        
        # Gather all analysis results
        market_data = state.get("market_data", {})
        sentiment = state.get("sentiment_analysis", {})
        technical = state.get("technical_analysis", {})
        rag_context = state.get("rag_context", [])
        
        # Calculate confidence score
        confidence = self._calculate_confidence(sentiment, technical)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            market_data, sentiment, technical, confidence
        )
        
        # Assess risk
        risk_assessment = self._assess_risk(market_data, sentiment, technical)
        
        state["confidence_score"] = confidence
        state["recommendations"] = recommendations
        state["risk_assessment"] = risk_assessment
        state["completed"] = True
        
        state["messages"].append({
            "agent": "DecisionAgent",
            "content": f"Decision: {recommendations[0] if recommendations else 'Hold'}",
            "timestamp": datetime.now().isoformat()
        })
        
        state["current_step"] = "complete"
        return state
    
    def _calculate_confidence(self, sentiment: dict, technical: dict) -> float:
        """Calculate overall confidence score"""
        sentiment_score = abs(sentiment.get("score", 0))
        technical_score = 0.5  # Default
        
        if technical.get("rsi"):
            if 30 < technical["rsi"] < 70:
                technical_score = 0.7
            else:
                technical_score = 0.3
        
        confidence = (sentiment_score * 0.4 + technical_score * 0.6)
        return round(min(1.0, confidence), 2)
    
    def _generate_recommendations(self, market_data: dict, sentiment: dict, 
                                  technical: dict, confidence: float) -> list:
        """Generate actionable recommendations"""
        recommendations = []
        
        symbol = market_data.get("symbol", "the stock")
        sentiment_label = sentiment.get("overall_sentiment", "neutral")
        
        # Main recommendation based on sentiment and technicals
        if sentiment_label == "bullish" and confidence > 0.6:
            recommendations.append(f"BUY {symbol} - Strong bullish signals")
            recommendations.append("Consider accumulating on dips")
        elif sentiment_label == "bearish" and confidence > 0.6:
            recommendations.append(f"SELL or HOLD {symbol} - Bearish signals detected")
            recommendations.append("Wait for reversal signals before entering")
        else:
            recommendations.append(f"HOLD {symbol} - Mixed signals, wait for clarity")
            recommendations.append("Monitor price action near key levels")
        
        # Add technical recommendations
        if technical.get("rsi", 50) > 70:
            recommendations.append("Stock appears overbought - consider partial profit taking")
        elif technical.get("rsi", 50) < 30:
            recommendations.append("Stock appears oversold - potential buying opportunity")
        
        # Add risk management
        recommendations.append(f"Set stop-loss at {technical.get('support_levels', [0])[0]:.2f}")
        
        return recommendations
    
    def _assess_risk(self, market_data: dict, sentiment: dict, technical: dict) -> dict:
        """Assess investment risk"""
        volatility = technical.get("volatility", 0.2)
        sentiment_score = sentiment.get("score", 0)
        
        risk_level = "medium"
        if volatility > 0.25 or abs(sentiment_score) < 0.1:
            risk_level = "high"
        elif volatility < 0.15 and abs(sentiment_score) > 0.3:
            risk_level = "low"
        
        return {
            "level": risk_level,
            "volatility_risk": volatility,
            "sentiment_risk": 1 - abs(sentiment_score),
            "liquidity_risk": random.uniform(0.1, 0.3),
            "recommended_position_size": 0.05 if risk_level == "high" else 0.15
        }