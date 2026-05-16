"""
Market Status - Check if market is open or closed
"""
from datetime import datetime, time as dt_time
from typing import Dict  # ← YEH LINE ADD KARO

class MarketStatus:
    def __init__(self):
        self.market_open_time = dt_time(9, 30)
        self.market_close_time = dt_time(15, 30)
    
    def is_market_open(self) -> bool:
        now = datetime.now()
        current_time = now.time()
        is_weekday = now.weekday() < 5  # Monday=0 to Friday=4
        is_trading_hours = self.market_open_time <= current_time <= self.market_close_time
        return is_weekday and is_trading_hours
    
    def get_status(self) -> Dict:
        is_open = self.is_market_open()
        now = datetime.now()
        
        if is_open:
            message = "Market is Open - Showing live data"
            status = "open"
        else:
            message = "Market is Closed - Showing last available data"
            status = "closed"
        
        return {
            'is_open': is_open,
            'status': status,
            'message': message,
            'time': now.strftime("%Y-%m-%d %H:%M:%S"),
            'next_open': self._get_next_open_time()
        }
    
    def _get_next_open_time(self) -> str:
        now = datetime.now()
        next_day = now.replace(hour=9, minute=30, second=0)
        if now.weekday() >= 4:  # Friday or weekend
            days_to_add = 7 - now.weekday() + 4
            next_day = now.replace(day=now.day + days_to_add, hour=9, minute=30)
        elif now.time() > self.market_close_time:
            next_day = now.replace(day=now.day + 1, hour=9, minute=30)
        return next_day.strftime("%Y-%m-%d %H:%M:%S")

market_status = MarketStatus()