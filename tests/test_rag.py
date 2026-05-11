from pathlib import Path

from rag_layer.news_loader import load_news
from rag_layer.vector_store import NewsVectorStore


LONG_TEXT = (
    "HBL Habib Bank Limited faced selling pressure after weak banking sentiment. "
    "Investors discussed price down movement, market pressure, and cautious outlook. "
    "The article gives enough detail for the retrieval quality filter to keep it. "
) * 2


def test_news_loader_accepts_flexible_columns(tmp_path: Path):
    news_file = tmp_path / "news.csv"
    news_file.write_text(
        "date,ticker,headline,content,source\n"
        "2026-05-08,HBL,HBL price down reason,"
        "\"HBL HBL market pressure and weak sentiment continued.\",Test Source\n",
        encoding="utf-8",
    )

    df = load_news(news_file)

    assert len(df) == 1
    assert df.iloc[0]["symbol"] == "HBL"
    assert df.iloc[0]["title"] == "HBL price down reason"
    assert "document_text" in df.columns


def test_vector_store_uses_fallback_retrieval_with_injected_metadata():
    store = NewsVectorStore(
        metadata=[
            {
                "record_id": "1",
                "published_date": "2026-05-08",
                "symbol": "HBL",
                "company": "Habib Bank Limited",
                "sector": "Banking",
                "title": "HBL price down reason",
                "summary": LONG_TEXT,
                "article_text": LONG_TEXT,
                "source": "Test Source",
                "news_type": "company_news",
                "document_text": LONG_TEXT,
            }
        ]
    )

    results = store.search("HBL price down reason", top_k=1, query_symbol="HBL")

    assert len(results) == 1
    assert results[0]["symbol"] == "HBL"
    assert results[0]["final_score"] >= 0
