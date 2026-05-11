from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
HISTORICAL_DIR = DATA_DIR / "historical"
RAW_PRICE_DIR = DATA_DIR / "raw" / "prices_daily"
METADATA_DIR = DATA_DIR / "metadata"
PROCESSED_DIR = DATA_DIR / "processed"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
LOG_DIR = DATA_DIR / "logs"

SAMPLE_DATA_FILE = DATA_DIR / "sample_psx_data.csv"
CLEANED_DATA_FILE = PROCESSED_DIR / "psx_cleaned_data.csv"
PRICES_100_DAILY_FILE = PROCESSED_DIR / "psx_prices_100_daily.csv"
ALL_TICKERS_FILE = DATA_DIR / "all_tickers.csv"
SYMBOLS_SEED_FILE = DATA_DIR / "symbols_seed.csv"
NEWS_FILE = DATA_DIR / "psx_news.csv"

TREND_OUTPUT_DIR = PROCESSED_DIR / "psx_trends"
VECTOR_INDEX_DIR = PROCESSED_DIR / "vector_index"

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "psx-market-data")

SPARK_APP_NAME = os.getenv("SPARK_APP_NAME", "PSX Kafka Stream Processor")
SPARK_CHECKPOINT_LOCATION = Path(
    os.getenv(
        "SPARK_CHECKPOINT_LOCATION",
        str(CHECKPOINT_DIR / "psx_stream_processor"),
    )
)


def ensure_runtime_dirs() -> None:
    for path in [
        DATA_DIR,
        HISTORICAL_DIR,
        PROCESSED_DIR,
        CHECKPOINT_DIR,
        TREND_OUTPUT_DIR,
        VECTOR_INDEX_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
