import csv
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
HISTORICAL_CSV = DATA_DIR / "historical_prices.csv"

def init_csv():
    """Create CSV with headers if not exists"""
    if not HISTORICAL_CSV.exists():
        DATA_DIR.mkdir(exist_ok=True)
        with open(HISTORICAL_CSV, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "symbol", "price", "change_pct", "source"])

def log_price(symbol, price, change_pct=0, source="live"):
    """Append one price record to CSV"""
    init_csv()
    with open(HISTORICAL_CSV, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), symbol, price, change_pct, source])