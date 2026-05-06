from datetime import datetime

from kafka_layer.producer import generate_live_tick


def test_generate_live_tick_builds_valid_market_tick():
    row = {
        "symbol": "HBL",
        "price": "142.50",
        "volume": "12000",
        "high": "145.00",
        "low": "140.20",
    }

    tick = generate_live_tick(row)

    assert tick["symbol"] == "HBL"
    assert 140.50 <= tick["price"] <= 144.50
    assert 12100 <= tick["volume"] <= 13000
    assert tick["high"] == 145.0
    assert tick["low"] == 140.2
    datetime.fromisoformat(tick["timestamp"])
