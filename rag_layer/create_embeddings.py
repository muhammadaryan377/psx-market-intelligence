import json
import pickle
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.app_config import VECTOR_INDEX_DIR
from rag_layer.news_loader import load_news


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

INDEX_DIR = VECTOR_INDEX_DIR
FAISS_INDEX_FILE = INDEX_DIR / "news_index.faiss"
TFIDF_INDEX_FILE = INDEX_DIR / "tfidf_index.pkl"
METADATA_FILE = INDEX_DIR / "news_metadata.json"


def _optional_faiss_stack_available() -> bool:
    try:
        import faiss  # noqa: F401
        import numpy as np  # noqa: F401
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except Exception:
        return False

    return True


def _metadata_records(df: pd.DataFrame) -> list[dict]:
    metadata_columns = [
        "record_id",
        "published_date",
        "symbol",
        "company",
        "sector",
        "title",
        "summary",
        "article_text",
        "source",
        "publisher",
        "url",
        "original_url",
        "news_type",
        "document_text",
    ]

    metadata_df = df.copy()
    metadata_df["published_date"] = (
        pd.to_datetime(metadata_df["published_date"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
        .fillna("")
    )

    for col in metadata_columns:
        if col not in metadata_df.columns:
            metadata_df[col] = ""

    return metadata_df[metadata_columns].fillna("").to_dict(orient="records")


def _save_metadata(metadata: list[dict]) -> None:
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def _create_faiss_index(documents: list[str]) -> bool:
    if not _optional_faiss_stack_available():
        return False

    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer

        print("Loading sentence-transformers model...")
        model = SentenceTransformer(MODEL_NAME)

        print("Creating dense embeddings...")
        embeddings = model.encode(
            documents,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        embeddings = np.array(embeddings).astype("float32")
        faiss.normalize_L2(embeddings)

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(FAISS_INDEX_FILE))
        print(f"Saved FAISS index: {FAISS_INDEX_FILE}")
        return True
    except Exception as exc:
        print(f"Dense embedding index unavailable; using TF-IDF fallback. Error: {exc}")
        return False


def _create_tfidf_index(documents: list[str]) -> None:
    from sklearn.feature_extraction.text import TfidfVectorizer

    print("Creating TF-IDF fallback index...")
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        max_features=20000,
        ngram_range=(1, 2),
    )
    matrix = vectorizer.fit_transform(documents)

    with open(TFIDF_INDEX_FILE, "wb") as f:
        pickle.dump({"vectorizer": vectorizer, "matrix": matrix}, f)

    print(f"Saved TF-IDF index: {TFIDF_INDEX_FILE}")


def create_embeddings() -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading news data...")
    df = load_news()

    if df.empty:
        raise ValueError("psx_news.csv is empty. Add news rows before indexing.")

    df["record_id"] = df["record_id"].astype(str).str.strip()
    df = df[df["record_id"] != ""].copy()
    df = df.drop_duplicates(subset=["record_id"], keep="last").reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid news records found after cleaning.")

    documents = df["document_text"].astype(str).tolist()
    metadata = _metadata_records(df)

    _save_metadata(metadata)
    print(f"Saved metadata: {METADATA_FILE}")
    print(f"Total news records: {len(metadata)}")

    if not _create_faiss_index(documents):
        _create_tfidf_index(documents)

    print("RAG index build complete.")


if __name__ == "__main__":
    create_embeddings()
