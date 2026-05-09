import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from agents.event_adapter import market_event_to_state
from agents.graph import psx_graph


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRENDS_DIR = PROJECT_ROOT / "data" / "processed" / "psx_trends"


FALLBACK_ROW = {
    "symbol": "HBL",
    "date": "2026-05-08",
    "close": 145.5,
    "volume": 250000,
    "moving_average": 148.2,
    "trend": "DOWN",
    "event_type": "price_down",
    "confidence_hint": 0.75,
}


def _read_json_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []

    for file_path in sorted(path.glob("*.json")):
        if file_path.name.startswith("."):
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                rows.append(json.loads(line))

    return rows


def _read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []

    for file_path in sorted(path.glob("*.csv")):
        if file_path.name.startswith("."):
            continue

        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            rows.extend(dict(row) for row in csv.DictReader(f))

    return rows


def _read_parquet_rows(path: Path) -> List[Dict[str, Any]]:
    parquet_files = [
        file_path
        for file_path in path.glob("*.parquet")
        if not file_path.name.startswith(".")
    ]

    if not parquet_files:
        return []

    try:
        import pandas as pd
    except ImportError:
        return []

    rows = []

    for file_path in sorted(parquet_files):
        try:
            rows.extend(pd.read_parquet(file_path).to_dict(orient="records"))
        except Exception:
            continue

    return rows


def read_processed_trend_rows(path: Path = TRENDS_DIR) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    readers = [
        _read_parquet_rows,
        _read_json_rows,
        _read_csv_rows,
    ]

    for reader in readers:
        rows = reader(path)

        if rows:
            return rows

    return []


def _sort_key(row: Dict[str, Any]) -> tuple:
    return (
        str(row.get("processed_at", "")),
        str(row.get("event_time", "")),
        str(row.get("date", "")),
    )


def select_demo_row(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return FALLBACK_ROW.copy()

    non_stable_rows = [
        row
        for row in rows
        if str(row.get("trend", "")).upper() not in ["", "STABLE"]
    ]

    candidate_rows = non_stable_rows or rows
    return sorted(candidate_rows, key=_sort_key)[-1]


def test_spark_to_agents_pipeline():
    trend_rows = read_processed_trend_rows()
    input_row = select_demo_row(trend_rows)
    state = market_event_to_state(input_row)

    final_state = psx_graph.invoke(state)

    print("\n================ INPUT TREND ROW ================")
    print(input_row)

    print("\n================ AGENT STATE SENT TO GRAPH ================")
    print(state)

    print("\n================ AGENT OUTPUT ================")
    print("Retrieved News Count:", len(final_state.get("retrieved_news", [])))
    print("Sentiment Label:", final_state.get("sentiment_label"))
    print("Sentiment Score:", final_state.get("sentiment_score"))

    print("\n================ RAG EXPLANATION ================")
    print(final_state.get("rag_explanation"))

    print("\n================ DECISION ================")
    print("Decision:", final_state.get("decision"))
    print("Confidence:", final_state.get("confidence"))
    print("Decision Reason:", final_state.get("decision_reason"))

    print("\n================ AUDIT LOG ================")
    for log in final_state.get("audit_log", []):
        print(log)

    assert final_state.get("decision") in {"BUY", "SELL", "HOLD"}
    assert "confidence" in final_state
    assert final_state.get("decision_reason")


if __name__ == "__main__":
    test_spark_to_agents_pipeline()
