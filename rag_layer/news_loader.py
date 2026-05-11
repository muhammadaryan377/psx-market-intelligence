from pathlib import Path
import hashlib

import pandas as pd

from config.app_config import NEWS_FILE

CANONICAL_COLUMNS = [
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
]

COLUMN_ALIASES = {
    "published_date": ["date", "published_at", "timestamp"],
    "symbol": ["ticker", "stock", "stock_symbol"],
    "title": ["headline", "heading"],
    "summary": ["description", "snippet"],
    "article_text": ["content", "body", "text", "news", "story"],
    "source": ["source_name"],
    "url": ["link"],
}


def clean_title(title: str, source: str = "") -> str:
    """
    Google News title usually contains source name at the end:
    Example:
    'Buying continues at PSX - Business Recorder'

    This function removes '- Business Recorder' from title.
    """
    title = str(title).strip()
    source = str(source).strip()

    if source and title.lower().endswith(f"- {source}".lower()):
        title = title[: -(len(source) + 2)].strip()

    return title


def load_news(news_file: Path = NEWS_FILE) -> pd.DataFrame:
    if not news_file.exists():
        raise FileNotFoundError(f"News file not found: {news_file}")

    try:
        df = pd.read_csv(news_file).fillna("")
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=CANONICAL_COLUMNS)

    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in df.columns:
            continue

        for alias in aliases:
            if alias in df.columns:
                df[canonical] = df[alias]
                break

    missing_cols = [col for col in CANONICAL_COLUMNS if col not in df.columns]

    for col in missing_cols:
        df[col] = ""

    if df.empty:
        df["document_text"] = ""
        return df

    if "record_id" not in df.columns or (df["record_id"].astype(str).str.strip() == "").any():
        def make_record_id(row) -> str:
            raw = "|".join(
                [
                    str(row.get("published_date", "")),
                    str(row.get("symbol", "")),
                    str(row.get("source", "")),
                    str(row.get("url", "")),
                    str(row.get("title", "")),
                ]
            )
            return hashlib.md5(raw.encode("utf-8")).hexdigest()

        empty_ids = df["record_id"].astype(str).str.strip() == ""
        df.loc[empty_ids, "record_id"] = df[empty_ids].apply(make_record_id, axis=1)

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    df["source"] = df["source"].astype(str).str.strip()
    df["publisher"] = df["publisher"].astype(str).str.strip()
    df["company"] = df["company"].astype(str).str.strip()
    df["sector"] = df["sector"].astype(str).str.strip()
    df["news_type"] = df["news_type"].astype(str).str.strip()
    df["url"] = df["url"].astype(str).str.strip()
    df["original_url"] = df["original_url"].astype(str).str.strip()
    df.loc[df["original_url"] == "", "original_url"] = df["url"]

    df["title"] = df.apply(
        lambda row: clean_title(row["title"], row["source"]),
        axis=1
    )

    df["summary"] = df["summary"].astype(str).str.strip()
    df["article_text"] = df["article_text"].astype(str).str.strip()

    # Use title and summary only as fallbacks when article text is unavailable.
    df.loc[df["summary"] == "", "summary"] = df["title"]
    df.loc[df["article_text"] == "", "article_text"] = df["summary"]
    df.loc[df["article_text"] == "", "article_text"] = df["title"]

    df["published_date"] = pd.to_datetime(
        df["published_date"],
        errors="coerce"
    )
    published_date_text = df["published_date"].dt.strftime("%Y-%m-%d").fillna("")

    # RAG ke liye final searchable document
    df["document_text"] = (
        "Published Date: " + published_date_text + "\n"
        + "Symbol: " + df["symbol"].astype(str) + "\n"
        + "Company: " + df["company"].astype(str) + "\n"
        + "Sector: " + df["sector"].astype(str) + "\n"
        + "Source: " + df["source"].astype(str) + "\n"
        + "News Type: " + df["news_type"].astype(str) + "\n"
        + "Title: " + df["title"].astype(str) + "\n"
        + "Summary: " + df["summary"].astype(str) + "\n"
        + "Article Text: " + df["article_text"].astype(str)
    )

    return df


if __name__ == "__main__":
    df = load_news()

    print("News records:", len(df))
    print("\nColumns:")
    print(df.columns.tolist())

    print("\nSample news:")
    print(
        df[
            [
                "published_date",
                "symbol",
                "company",
                "sector",
                "source",
                "title",
                "article_text",
                "news_type",
            ]
        ].head(10).to_string(index=False)
    )
