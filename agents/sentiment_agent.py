"""Sentiment Agent - Analyzes sentiment from news and social media"""
from agents.state import AgentState
from datetime import datetime
import random

class SentimentAgent:
    """Agent responsible for sentiment analysis"""
    
    def __init__(self):
        # TODO: Load your sentiment model
        # self.model = torch.load('models/sentiment_model.pth')
        pass
    
    def process(self, state: AgentState) -> AgentState:
        """Analyze sentiment from news and market data"""
        print("😊 Sentiment Agent: Analyzing sentiment...")
        
        news_data = state.get("news_data", [])
        
        if not news_data:
            state["sentiment_analysis"] = {
                "overall_sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "factors": []
            }
            return state
        
        # Analyze each news article
        sentiments = []
        for news in news_data:
            sentiment_score = self._analyze_text(news.get("title", ""))
            news["sentiment"] = sentiment_score
            sentiments.append(sentiment_score)
        
        # Calculate overall sentiment
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Determine sentiment label
        if avg_sentiment > 0.2:
            label = "bullish"
        elif avg_sentiment < -0.2:
            label = "bearish"
        else:
            label = "neutral"
        
        state["sentiment_analysis"] = {
            "overall_sentiment": label,
            "score": avg_sentiment,
            "confidence": min(abs(avg_sentiment) * 2, 1.0),
            "news_sentiments": sentiments,
            "factors": self._identify_factors(news_data)
        }
        
        state["messages"].append({
            "agent": "SentimentAgent",
            "content": f"Sentiment: {label} (score: {avg_sentiment:.2f})",
            "timestamp": datetime.now().isoformat()
        })
        
        state["current_step"] = "sentiment_complete"
        return state
    
    def _analyze_text(self, text: str) -> float:
        """Analyze sentiment of text"""
        # TODO: Replace with actual model inference
        positive_words = ["bullish", "rally", "gain", "high", "record", "growth", "profit"]
        negative_words = ["bearish", "decline", "loss", "low", "risk", "concern", "drop"]
        
        score = 0
        text_lower = text.lower()
        
        for word in positive_words:
            if word in text_lower:
                score += 0.2
        for word in negative_words:
            if word in text_lower:
                score -= 0.2
        
        return max(-1, min(1, score + random.uniform(-0.1, 0.1)))
    
    def _identify_factors(self, news_data: list) -> list:
        """Identify sentiment factors from news"""
        factors = []
        for news in news_data[:3]:
            if news.get("sentiment", 0) != 0:
                factors.append({
                    "title": news.get("title", "")[:50],
                    "impact": "positive" if news.get("sentiment", 0) > 0 else "negative"
                })
        return factors