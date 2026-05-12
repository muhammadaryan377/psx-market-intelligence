import csv
import os
from datetime import date, datetime
from pathlib import Path
import sys
from typing import Any, Dict, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.state import PSXAgentState

SYMBOLS_FILE = PROJECT_ROOT / "data" / "symbols_seed.csv"


def _plain_value(value: Any) -> Any:
    if hasattr(value, "asDict"):
        return value.asDict()

    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass

    return value


def _row_to_dict(row: Any) -> Dict[str, Any]:
    if hasattr(row, "asDict"):
        return row.asDict(recursive=True)

    if isinstance(row, Mapping):
        return {str(key): _plain_value(value) for key, value in row.items()}

    if hasattr(row, "to_dict"):
        return {
            str(key): _plain_value(value)
            for key, value in row.to_dict().items()
        }

    raise TypeError("Unsupported market event row type.")


def _to_float(value: Any) -> float | None:
    value = _plain_value(value)

    if value in [None, ""]:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    value = _plain_value(value)

    if value in [None, ""]:
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_date_text(value: Any) -> str:
    value = _plain_value(value)

    if value in [None, ""]:
        return ""

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()

    if "T" in text:
        return text.split("T", 1)[0]

    if " " in text:
        return text.split(" ", 1)[0]

    return text[:10]


def load_symbol_metadata(symbols_file: Path = SYMBOLS_FILE) -> Dict[str, Dict[str, str]]:
    if not symbols_file.exists():
        return {}

    with open(symbols_file, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        metadata = {}

        for row in reader:
            symbol = str(row.get("symbol", "")).strip().upper()

            if not symbol:
                continue

            metadata[symbol] = {
                "company": str(row.get("company", "")).strip() or symbol,
                "sector": str(row.get("sector", "")).strip() or "Unknown",
            }

    return metadata


def market_event_to_state(row: Any) -> PSXAgentState:
    row_dict = _row_to_dict(row)
    normalized = {str(key).lower(): value for key, value in row_dict.items()}

    symbol = str(normalized.get("symbol", "")).strip().upper()
    symbols = load_symbol_metadata()
    symbol_meta = symbols.get(symbol, {})

    event_date = os.getenv("DEMO_EVENT_DATE_OVERRIDE", "").strip()

    if not event_date:
        event_date = (
            _to_date_text(normalized.get("date"))
            or _to_date_text(normalized.get("event_time"))
        )

    price = _to_float(normalized.get("close"))
    volume = _to_int(normalized.get("volume"))
    moving_average = _to_float(normalized.get("moving_average"))
    confidence_hint = _to_float(normalized.get("confidence_hint"))

    state: PSXAgentState = {
        "symbol": symbol,
        "company": symbol_meta.get("company", symbol or "Unknown"),
        "sector": symbol_meta.get("sector", "Unknown"),
        "event_date": event_date,
        "event_type": str(
            normalized.get("event_type") or "market_movement"
        ).strip(),
        "trend": str(normalized.get("trend") or "UNKNOWN").strip().upper(),
        "price": price if price is not None else 0.0,
        "volume": volume if volume is not None else 0,
        "moving_average": moving_average if moving_average is not None else 0.0,
        "confidence_hint": confidence_hint if confidence_hint is not None else 0.0,
    }

    return state


spark_row_to_state = market_event_to_state
