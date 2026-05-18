"""
Price Predictor – Unified version (supports both batch & incremental training)
"""
import numpy as np
from sklearn.linear_model import SGDRegressor
from sklearn.preprocessing import MinMaxScaler
import joblib
from pathlib import Path

class PricePredictor:
    def __init__(self, symbol=None):
        self.symbol = symbol
        if symbol:
            self.model_file = Path(f"models/price_predictor_{symbol}.pkl")
            self.scaler_file = Path(f"models/price_scaler_{symbol}.pkl")
        else:
            self.model_file = Path("models/price_predictor.pkl")
            self.scaler_file = Path("models/price_scaler.pkl")
        self.model = None
        self.scaler = MinMaxScaler()
        self._load_or_create()

    def _load_or_create(self):
        if self.model_file.exists() and self.scaler_file.exists():
            self.model = joblib.load(self.model_file)
            self.scaler = joblib.load(self.scaler_file)
        else:
            self.model = SGDRegressor(loss='squared_error', penalty='l2',
                                      alpha=0.0001, max_iter=1000, random_state=42)

    # ----- Batch training (full training from history) -----
    def train(self, prices):
        """Train model on a list of historical prices (batch)."""
        if len(prices) < 5:
            return False
        X = np.arange(len(prices)).reshape(-1, 1).astype(np.float64)
        y = np.array(prices).astype(np.float64)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self._save()
        return True

    # ----- Incremental update (one new point) -----
    def partial_fit(self, X, y):
        """
        Incrementally update model with a single new data point.
        IMPORTANT: scaler must already be fitted (call train() at least once before).
        """
        if not hasattr(self.scaler, 'scale_'):
            # Scaler not fitted – cannot do partial_fit safely
            raise RuntimeError("Scaler not fitted. Call train() first with at least 5 points.")
        X_scaled = self.scaler.transform(X)
        self.model.partial_fit(X_scaled, y)
        self._save()

    # ----- Prediction -----
    def predict_next_price(self, last_prices):
        """Predict next price based on last N prices."""
        if len(last_prices) < 5 or self.model is None:
            return None
        X = np.arange(len(last_prices)).reshape(-1, 1)
        # If scaler not fitted, we cannot transform
        if not hasattr(self.scaler, 'scale_'):
            return None
        X_scaled = self.scaler.transform(X)
        next_idx = len(last_prices)
        X_next = np.array([[next_idx]]).astype(np.float64)
        X_next_scaled = self.scaler.transform(X_next)
        return float(self.model.predict(X_next_scaled)[0])

    def _save(self):
        self.model_file.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_file)
        joblib.dump(self.scaler, self.scaler_file)

# ----- Global instance for frontend (default model, not per‑symbol) -----
# You may still use this, but we recommend per‑symbol models via PricePredictor(symbol=...)
price_predictor = PricePredictor()