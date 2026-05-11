import json
import os
import sys
from pathlib import Path

import pytest


pyspark = pytest.importorskip("pyspark")

from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from spark_layer.cleaning import clean_stock_batch
from spark_layer.trend_detection import add_trend_signals


@pytest.fixture(scope="module")
def spark():
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    try:
        session = (
            SparkSession.builder
            .master("local[1]")
            .appName("psx-week2-tests")
            .config("spark.sql.shuffle.partitions", "1")
            .getOrCreate()
        )
    except Exception as exc:
        pytest.skip(f"Spark session unavailable: {exc}")

    yield session
    session.stop()


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows),
        encoding="utf-8",
    )
    return path


def test_cleaning_removes_invalid_rows_and_normalizes_schema(spark, tmp_path):
    input_file = _write_jsonl(
        tmp_path / "cleaning.jsonl",
        [
            {"symbol": " hbl ", "date": "2026-05-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000},
            {"symbol": "", "date": "2026-05-01", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000},
            {"symbol": "HBL", "date": "bad-date", "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1000},
        ],
    )

    cleaned = clean_stock_batch(spark.read.json(str(input_file)))

    assert cleaned.count() == 1
    assert cleaned.filter(col("symbol") == "HBL").count() == 1
    assert cleaned.filter(col("source") == "psxdata").count() == 1
    assert cleaned.filter(col("stream_type") == "historical_replay").count() == 1


def test_trend_detection_uses_previous_close_threshold(spark, tmp_path):
    input_file = _write_jsonl(
        tmp_path / "trends.jsonl",
        [
            {"symbol": "HBL", "date": "2026-05-01", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1000},
            {"symbol": "HBL", "date": "2026-05-02", "open": 100.0, "high": 103.0, "low": 99.0, "close": 101.0, "volume": 1200},
            {"symbol": "HBL", "date": "2026-05-03", "open": 101.0, "high": 102.0, "low": 98.0, "close": 99.0, "volume": 1300},
        ],
    )

    cleaned = clean_stock_batch(spark.read.json(str(input_file)))
    trended = add_trend_signals(cleaned, moving_average_days=2, stable_threshold=0.005)

    assert trended.filter((col("date").cast("string") == "2026-05-01") & (col("trend") == "STABLE")).count() == 1
    assert trended.filter((col("date").cast("string") == "2026-05-02") & (col("trend") == "UP")).count() == 1
    assert trended.filter((col("date").cast("string") == "2026-05-03") & (col("trend") == "DOWN")).count() == 1
