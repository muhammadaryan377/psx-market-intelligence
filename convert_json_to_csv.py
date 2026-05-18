import json
import csv
from pathlib import Path

input_file = Path("data/historical_price.json")   # your JSON file
output_file = Path("data/historical_prices_clean.csv")

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['symbol', 'price', 'timestamp'])
    writer.writeheader()
    for symbol, entries in data.items():
        for entry in entries:
            writer.writerow({
                'symbol': symbol,
                'price': entry['price'],
                'timestamp': entry['timestamp']
            })

print(f"✅ Converted {input_file} → {output_file}")