from typing import Any, Dict, List, Optional

from sentiment_layer.sentiment_model import SimpleSentimentModel


class SentimentService:
    """Analyze retrieved PSX news with a lightweight Week 2 sentiment baseline."""

    def __init__(self):
        self._model: Optional[SimpleSentimentModel] = None

    @property
    def model(self) -> SimpleSentimentModel:
        if self._model is None:
            self._model = SimpleSentimentModel()

        return self._model

    def _build_text(self, news_item: Dict[str, Any]) -> str:
        title = str(news_item.get("title", "")).strip()
        summary = str(news_item.get("summary", "")).strip()
        article_text = str(news_item.get("article_text", "")).strip()
        return f"{title}\n\n{summary}\n\n{article_text}".strip()

    def analyze_news_list(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not news_items:
            return {
                "sentiment_label": "Neutral",
                "sentiment_score": 0.0,
                "sentiment_confidence": 0.0,
                "article_sentiments": [],
                "sentiment_status": "no_news_found",
            }

        article_sentiments = []

        for item in news_items:
            sentiment = self.model.analyze_text(self._build_text(item))
            article_sentiments.append(
                {
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "published_date": item.get("published_date", ""),
                    "symbol": item.get("symbol", ""),
                    "label": sentiment["label"],
                    "score": sentiment["score"],
                    "confidence": sentiment["confidence"],
                    "backend": sentiment.get("backend", "unknown"),
                    "raw_scores": sentiment["raw_scores"],
                }
            )

        avg_score = round(
            sum(item["score"] for item in article_sentiments) / len(article_sentiments),
            4,
        )
        avg_confidence = round(
            sum(item["confidence"] for item in article_sentiments) / len(article_sentiments),
            4,
        )

        return {
            "label": _aggregate_label(avg_score),
            "score": avg_score,
            "sentiment_label": _aggregate_label(avg_score),
            "sentiment_score": avg_score,
            "sentiment_confidence": avg_confidence,
            "article_sentiments": article_sentiments,
            "sentiment_status": "success",
        }


def _aggregate_label(score: float) -> str:
    if score > 0.05:
        return "Positive"
    if score < -0.05:
        return "Negative"
    return "Neutral"


def analyze_news_sentiment(news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return SentimentService().analyze_news_list(news_items)


if __name__ == "__main__":
    sample_news = [
        {
            "title": "Buying continues at PSX as KSE-100 gains",
            "summary": "The benchmark index gained as investor sentiment improved.",
            "article_text": "Pakistan Stock Exchange witnessed strong buying and recovery.",
        },
        {
            "title": "PSX falls amid political uncertainty",
            "summary": "Stocks declined due to uncertainty and selling pressure.",
            "article_text": "The market remained weak as investors avoided risky positions.",
        },
    ]

    result = analyze_news_sentiment(sample_news)
    print(result)
