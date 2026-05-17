import json
import csv
from pathlib import Path

json_path = Path("data/historical_prices.json")
csv_path = Path("data/historical_prices.csv")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["symbol", "price", "timestamp"])

    for symbol, records in data.items():
        for record in records:
            writer.writerow([symbol, record["price"], record["timestamp"]])

print(f"✅ Converted {sum(len(v) for v in data.values())} rows to {csv_path}")
