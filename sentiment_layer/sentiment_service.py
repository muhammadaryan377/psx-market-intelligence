from typing import List, Dict, Any

from sentiment_layer.sentiment_model import FinBERTSentimentModel


class SentimentService:
    """
    Retrieved news list ka sentiment analyze karta hai.
    Uses title + summary + article_text.
    """

    def __init__(self):
        self.model = FinBERTSentimentModel()

    def _build_text(self, news_item: Dict[str, Any]) -> str:
        title = str(news_item.get("title", "")).strip()
        summary = str(news_item.get("summary", "")).strip()
        article_text = str(news_item.get("article_text", "")).strip()

        return f"{title}\n\n{summary}\n\n{article_text}".strip()

    def analyze_news_list(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not news_items:
            return {
                "sentiment_label": "neutral",
                "sentiment_score": 0.0,
                "sentiment_confidence": 0.0,
                "article_sentiments": [],
                "sentiment_status": "no_news_found"
            }

        article_sentiments = []

        for item in news_items:
            text = self._build_text(item)
            sentiment = self.model.analyze_text(text)

            article_sentiments.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "published_date": item.get("published_date", ""),
                "symbol": item.get("symbol", ""),
                "label": sentiment["label"],
                "score": sentiment["score"],
                "confidence": sentiment["confidence"],
                "raw_scores": sentiment["raw_scores"],
            })

        avg_score = sum(x["score"] for x in article_sentiments) / len(article_sentiments)
        avg_score = round(avg_score, 4)

        avg_confidence = sum(x["confidence"] for x in article_sentiments) / len(article_sentiments)
        avg_confidence = round(avg_confidence, 4)

        if avg_score > 0.15:
            final_label = "positive"
        elif avg_score < -0.15:
            final_label = "negative"
        else:
            final_label = "neutral"

        return {
            "sentiment_label": final_label,
            "sentiment_score": avg_score,
            "sentiment_confidence": avg_confidence,
            "article_sentiments": article_sentiments,
            "sentiment_status": "success"
        }


if __name__ == "__main__":
    sample_news = [
        {
            "title": "Buying continues at PSX, KSE-100 Index gains nearly 1,200 points",
            "summary": "The benchmark index gained as investor sentiment improved.",
            "article_text": "Pakistan Stock Exchange witnessed strong buying as investors reacted positively to market developments."
        },
        {
            "title": "PSX falls amid political uncertainty",
            "summary": "Stocks declined due to uncertainty and selling pressure.",
            "article_text": "The market remained under pressure as investors avoided risky positions."
        }
    ]

    service = SentimentService()
    result = service.analyze_news_list(sample_news)

    print(result)