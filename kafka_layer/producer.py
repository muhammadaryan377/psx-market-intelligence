import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.app_config import (
    CLEANED_DATA_FILE,
    HISTORICAL_DIR,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    PRICES_100_DAILY_FILE,
    SAMPLE_DATA_FILE,
)


DEFAULT_SEND_DELAY_SECONDS = float(os.getenv("PSX_PRODUCER_DELAY_SECONDS", "0.1"))
DEFAULT_SOURCE = os.getenv("PSX_PRODUCER_SOURCE", "sample").strip().lower()
MAX_ROWS_ENV = os.getenv("PSX_PRODUCER_MAX_ROWS", "").strip()
REQUIRED_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume"]


def generate_live_tick(row):
    """
    Build a simulated live market tick from a simple price row.

    Kept for tests and backward compatibility with the earlier live-tick producer.
    The main producer emits normalized OHLC records through row_to_kafka_message().
    """

    price_change = random.uniform(-2, 2)
    new_price = round(float(row["price"]) + price_change, 2)

    return {
        "symbol": str(row["symbol"]),
        "price": new_price,
        "volume": int(row["volume"]) + random.randint(100, 1000),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "timestamp": datetime.now().isoformat(),
    }


def convert_bool(value) -> bool:
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
        key_serializer=lambda key: str(key).encode("utf-8"),
        api_version_auto_timeout_ms=3000,
        request_timeout_ms=10000,
    )


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

    aliases = {
        "timestamp": ["time", "datetime", "event_time"],
        "date": ["trade_date", "business_date"],
        "open": ["open_price"],
        "high": ["high_price"],
        "low": ["low_price"],
        "close": ["close_price", "closing_price"],
        "volume": ["vol", "trade_volume"],
    }

    for canonical, candidates in aliases.items():
        if canonical in df.columns:
            continue

        for candidate in candidates:
            if candidate in df.columns:
                df = df.rename(columns={candidate: canonical})
                break

    return df


def _read_market_csv(path: Path, default_symbol: Optional[str] = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = _normalize_columns(df)

    if "symbol" not in df.columns and default_symbol:
        df["symbol"] = default_symbol

    if "date" not in df.columns and "timestamp" in df.columns:
        df["date"] = df["timestamp"]

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col_name in ["open", "high", "low", "close", "volume"]:
        df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

    df = df.dropna(subset=REQUIRED_COLUMNS)
    df = df[df["symbol"] != ""]
    df = df.sort_values(["symbol", "date"])

    if "is_anomaly" not in df.columns:
        df["is_anomaly"] = False

    if "source" not in df.columns:
        df["source"] = "psxdata" if path != SAMPLE_DATA_FILE else "sample_csv"

    if "stream_type" not in df.columns:
        df["stream_type"] = "historical_replay"

    return df


def _source_files(source: str) -> Iterable[Path]:
    explicit_input = os.getenv("PSX_PRODUCER_INPUT", "").strip()
    if explicit_input:
        yield Path(explicit_input)
        return

    if source == "historical":
        yield from sorted(HISTORICAL_DIR.glob("*.csv"))
        return

    source_map = {
        "sample": SAMPLE_DATA_FILE,
        "cleaned": CLEANED_DATA_FILE,
        "processed": PRICES_100_DAILY_FILE,
        "processed100": PRICES_100_DAILY_FILE,
    }

    selected_file = source_map.get(source, SAMPLE_DATA_FILE)
    if selected_file.exists():
        yield selected_file
        return

    for fallback_file in [SAMPLE_DATA_FILE, CLEANED_DATA_FILE, PRICES_100_DAILY_FILE]:
        if fallback_file.exists():
            yield fallback_file
            return

    yield from sorted(HISTORICAL_DIR.glob("*.csv"))


def load_market_data(source: str = DEFAULT_SOURCE) -> pd.DataFrame:
    frames = []
    files = list(_source_files(source))

    if not files:
        raise FileNotFoundError(
            "No producer input data found. Expected data/sample_psx_data.csv "
            "or CSV files under data/historical/."
        )

    for path in files:
        symbol = path.stem.upper() if path.parent == HISTORICAL_DIR else None
        frames.append(_read_market_csv(path, default_symbol=symbol))

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["symbol", "date"], keep="last")
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    if MAX_ROWS_ENV:
        df = df.head(int(MAX_ROWS_ENV))

    return df


def row_to_kafka_message(row) -> dict:
    event_time = row["date"]
    date_text = event_time.date().isoformat() if hasattr(event_time, "date") else str(event_time)[:10]

    return {
        "symbol": str(row["symbol"]).upper().strip(),
        "date": date_text,
        "timestamp": date_text,
        "open": float(row["open"]),
        "high": float(row["high"]),
        "low": float(row["low"]),
        "close": float(row["close"]),
        "volume": int(float(row["volume"])),
        "is_anomaly": convert_bool(row.get("is_anomaly", False)),
        "source": str(row.get("source", "psxdata")),
        "stream_type": str(row.get("stream_type", "historical_replay")),
    }


def run_producer(
    source: str = DEFAULT_SOURCE,
    send_delay_seconds: float = DEFAULT_SEND_DELAY_SECONDS,
) -> None:
    df = load_market_data(source=source)
    kafka_producer = create_producer()

    print("=" * 60)
    print("PSX Kafka Producer Started")
    print(f"Kafka Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Kafka Topic: {KAFKA_TOPIC}")
    print(f"Input source: {source}")
    print(f"Total Rows: {len(df)}")
    print("=" * 60)

    for index, row in df.iterrows():
        message = row_to_kafka_message(row)
        future = kafka_producer.send(
            KAFKA_TOPIC,
            key=message["symbol"],
            value=message,
        )
        future.get(timeout=10)

        print(
            f"Sent {index + 1}/{len(df)} | "
            f"{message['symbol']} | {message['date']} | "
            f"Close={message['close']} | Volume={message['volume']}"
        )

        if send_delay_seconds > 0:
            time.sleep(send_delay_seconds)

    kafka_producer.flush()
    kafka_producer.close()
    print("All PSX rows sent to Kafka successfully.")


def main() -> int:
    try:
        run_producer()
    except NoBrokersAvailable:
        print(
            "Error: Kafka broker is not available at "
            f"{KAFKA_BOOTSTRAP_SERVERS}. Start it with: docker compose up -d"
        )
        return 1
    except KafkaError as error:
        print(f"Kafka producer error: {error}")
        return 1
    except Exception as error:
        print(f"Producer error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
