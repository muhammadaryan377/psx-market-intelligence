"""
Sentiment Agent - LangGraph compatible
"""
class SentimentAgent:
    """Analyzes market sentiment"""
    
    def process(self, state):
        """Process state - analyze sentiment"""
        print("😊 Sentiment Agent: Analyzing sentiment...")
        
        news_data = state.get("news_data", [])
        market_data = state.get("market_data", {})
        
        # Calculate score
        score = self._calculate_score(news_data, market_data)
        
        # Determine label
        if score > 0.2:
            label = "bullish"
            emoji = "🟢"
        elif score < -0.2:
            label = "bearish"
            emoji = "🔴"
        else:
            label = "stable"
            emoji = "🟡"
        
        state["sentiment_analysis"] = {
            "overall_sentiment": label,
            "score": round(score, 2),
            "emoji": emoji,
            "confidence": min(abs(score), 1.0)
        }
        
        print(f"   ✓ Sentiment: {emoji} {label.upper()} ({score:+.2f})")
        state["current_step"] = "sentiment_complete"
        return state
    
    def _calculate_score(self, news_data, market_data):
        """Calculate sentiment score dynamically"""
        score = 0
        
        # From news
        for news in news_data[:5]:
            title = news.get("title", "").lower()
            content = news.get("content", "").lower()
            text = title + " " + content
            
            pos_words = ['profit', 'gain', 'growth', 'positive', 'bullish', 'high', 'rise']
            neg_words = ['loss', 'decline', 'negative', 'bearish', 'low', 'fall', 'drop']
            
            for w in pos_words:
                if w in text:
                    score += 0.1
            for w in neg_words:
                if w in text:
                    score -= 0.1
        
        # From market data
        change = market_data.get('change', 0)
        if change != 'N/A':
            if change > 1:
                score += 0.3
            elif change > 0:
                score += 0.1
            elif change < -1:
                score -= 0.3
            elif change < 0:
                score -= 0.1
        
        return max(-1, min(1, score))