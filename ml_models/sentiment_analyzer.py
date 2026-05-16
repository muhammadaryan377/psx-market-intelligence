"""
Sentiment Analyzer - Analyzes news sentiment using TextBlob
"""
from textblob import TextBlob
import re

class SentimentAnalyzer:
    def __init__(self):
        print("✅ Sentiment Analyzer ready")
    
    def analyze(self, text):
        if not text:
            return "neutral", 0.0
        
        text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.1:
            return "positive", polarity * 100
        elif polarity < -0.1:
            return "negative", abs(polarity) * 100
        else:
            return "neutral", 50
    
    def analyze_batch(self, news_list):
        sentiments = []
        for news in news_list:
            text = news.get('title', '') + " " + news.get('summary', '')
            sentiment, score = self.analyze(text)
            sentiments.append({'sentiment': sentiment, 'score': score})
        
        positive = sum(1 for s in sentiments if s['sentiment'] == 'positive')
        negative = sum(1 for s in sentiments if s['sentiment'] == 'negative')
        
        if positive > negative * 2:
            overall = "bullish"
            confidence = 80
        elif negative > positive * 2:
            overall = "bearish"
            confidence = 80
        else:
            overall = "neutral"
            confidence = 50
        
        return {'overall': overall, 'confidence': confidence, 'details': sentiments}

sentiment_analyzer = SentimentAnalyzer()