import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

INDEX_DIR = Path("data/processed/vector_index")
INDEX_FILE = INDEX_DIR / "news_index.faiss"
METADATA_FILE = INDEX_DIR / "news_metadata.json"


def is_low_quality_news(item):
    title = str(item.get("title", "")).strip().lower()
    article_text = str(item.get("article_text", "")).strip()
    summary = str(item.get("summary", "")).strip()

    bad_titles = [
        "untitled",
        "notice",
        "navy and white modern investor pitch deck presentation",
    ]

    if title in bad_titles:
        return True

    if len(article_text) < 150 and len(summary) < 150:
        return True

    if not title and not article_text:
        return True

    return False


class NewsVectorStore:
    def __init__(self):
        if not INDEX_FILE.exists():
            raise FileNotFoundError(
                "FAISS index not found. Run: python -m rag_layer.create_embeddings"
            )

        if not METADATA_FILE.exists():
            raise FileNotFoundError(
                "Metadata file not found. Run: python -m rag_layer.create_embeddings"
            )

        print("Loading embedding model...")
        self.model = SentenceTransformer(MODEL_NAME)

        print("Loading FAISS index...")
        self.index = faiss.read_index(str(INDEX_FILE))

        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        print(f"Vector store loaded with {len(self.metadata)} news records.")

    def search(
        self,
        query: str,
        top_k: int = 5,
        symbol: Optional[str] = None,
        sector: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        news_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True
        )

        query_embedding = np.array(query_embedding).astype("float32")
        faiss.normalize_L2(query_embedding)

        search_k = min(len(self.metadata), max(top_k * 20, 20))

        scores, indices = self.index.search(query_embedding, search_k)

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            item = self.metadata[idx].copy()

            if is_low_quality_news(item):
                continue

            item_symbol = str(item.get("symbol", "")).upper()
            item_sector = str(item.get("sector", "")).lower()
            item_news_type = str(item.get("news_type", "")).lower()
            published_date = str(item.get("published_date", ""))[:10]
            has_valid_date = published_date.lower() not in ["", "nat", "nan", "none"]

            if symbol and item_symbol != symbol.upper():
                continue

            if sector and item_sector != sector.lower():
                continue

            if news_type and item_news_type != news_type.lower():
                continue

            if start_date and has_valid_date and published_date < start_date:
                continue

            if end_date and has_valid_date and published_date > end_date:
                continue

            item["similarity_score"] = round(float(score), 4)
            results.append(item)

            if len(results) >= top_k:
                break

        return results


if __name__ == "__main__":
    store = NewsVectorStore()

    results = store.search(
        query="HBL PSX banking market price movement",
        top_k=5,
        symbol="HBL",
        start_date="2026-05-01",
        end_date="2026-05-09",
    )

    print("\nSearch Results:")
    for item in results:
        print("-" * 80)
        print("Date:", item.get("published_date"))
        print("Symbol:", item.get("symbol"))
        print("Source:", item.get("source"))
        print("Score:", item.get("similarity_score"))
        print("Title:", item.get("title"))
        print("Original URL:", item.get("original_url"))
        print("Article Length:", len(str(item.get("article_text", ""))))
