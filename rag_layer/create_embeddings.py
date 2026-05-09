import json
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from rag_layer.news_loader import load_news


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

INDEX_DIR = Path("data/processed/vector_index")
INDEX_FILE = INDEX_DIR / "news_index.faiss"
METADATA_FILE = INDEX_DIR / "news_metadata.json"


def create_embeddings():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading news data...")
    df = load_news()

    if df.empty:
        raise ValueError("psx_news.csv is empty. Collect news first.")

    df["record_id"] = df["record_id"].astype(str).str.strip()
    df = df[df["record_id"] != ""].copy()
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["record_id"], keep="last").reset_index(drop=True)

    if df.empty:
        raise ValueError("No valid record_id values found in psx_news.csv.")

    print(f"Total news records: {len(df)}")
    if before_dedup != len(df):
        print(f"Dropped duplicate record_id rows: {before_dedup - len(df)}")

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    documents = df["document_text"].tolist()

    print("Creating embeddings...")
    embeddings = model.encode(
        documents,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    embeddings = np.array(embeddings).astype("float32")

    # cosine similarity ke liye normalize
    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print("Saving FAISS index...")
    faiss.write_index(index, str(INDEX_FILE))

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

    metadata = metadata_df[metadata_columns].to_dict(orient="records")

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    print("Embedding index created successfully.")
    print(f"FAISS index: {INDEX_FILE}")
    print(f"Metadata: {METADATA_FILE}")


if __name__ == "__main__":
    create_embeddings()
