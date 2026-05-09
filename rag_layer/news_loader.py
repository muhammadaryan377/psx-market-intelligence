from pathlib import Path
import pandas as pd


NEWS_FILE = Path("data/psx_news.csv")


REQUIRED_COLUMNS = [
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

BACKFILLABLE_COLUMNS = {"article_text", "publisher", "original_url"}


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
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    blocking_missing_cols = [
        col for col in missing_cols if col not in BACKFILLABLE_COLUMNS
    ]

    if blocking_missing_cols:
        raise ValueError(f"Missing columns in news file: {blocking_missing_cols}")

    for col in missing_cols:
        df[col] = ""

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
