from rag_layer.retriever import RAGRetriever
from sentiment_layer.sentiment_service import SentimentService


def test_rag_sentiment_pipeline():
    retriever = RAGRetriever()
    sentiment_service = SentimentService()

    news_items = retriever.retrieve(
        symbol="HBL",
        event_date="2026-05-08",
        event_type="price_down",
        trend="DOWN",
        sector="Banking",
        top_k=5,
        lookback_days=7,
    )

    print("\n================ RETRIEVED NEWS ================")
    print("News count:", len(news_items))

    for item in news_items:
        print("-" * 80)
        print("Date:", item.get("published_date"))
        print("Symbol:", item.get("symbol"))
        print("Source:", item.get("source"))
        print("Title:", item.get("title"))
        print("Score:", item.get("similarity_score"))
        print("Article Length:", len(str(item.get("article_text", ""))))

    sentiment_result = sentiment_service.analyze_news_list(news_items)

    print("\n================ SENTIMENT RESULT ================")
    print("Final Label:", sentiment_result.get("sentiment_label"))
    print("Final Score:", sentiment_result.get("sentiment_score"))
    print("Confidence:", sentiment_result.get("sentiment_confidence"))
    print("Status:", sentiment_result.get("sentiment_status"))

    print("\n================ ARTICLE SENTIMENTS ================")
    for item in sentiment_result.get("article_sentiments", []):
        print("-" * 80)
        print("Title:", item.get("title"))
        print("Label:", item.get("label"))
        print("Score:", item.get("score"))
        print("Confidence:", item.get("confidence"))


if __name__ == "__main__":
    test_rag_sentiment_pipeline()