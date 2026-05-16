"""
Price Predictor - Simple ML model for price prediction
"""
import numpy as np
from sklearn.linear_model import LinearRegression
import joblib
from pathlib import Path

class PricePredictor:
    def __init__(self):
        self.model_file = Path("models/price_predictor.pkl")
        self.model = None
        self._load_model()
    
    def _load_model(self):
        if self.model_file.exists():
            try:
                self.model = joblib.load(self.model_file)
                print("✓ Price Predictor model loaded")
            except:
                self.model = LinearRegression()
                print("⚠️ New Price Predictor model created")
        else:
            self.model = LinearRegression()
            print("⚠️ New Price Predictor model created")
    
    def predict_next_price(self, prices):
        """Predict next price using linear regression"""
        if len(prices) < 5:
            return None
        
        # Convert to numpy float64 to avoid float32 issues
        prices = [float(p) for p in prices]
        
        X = np.array(range(len(prices))).reshape(-1, 1).astype(np.float64)
        y = np.array(prices).astype(np.float64)
        
        self.model.fit(X, y)
        next_x = np.array([[len(prices)]]).astype(np.float64)
        prediction = self.model.predict(next_x)[0]
        
        # Convert to Python float
        return float(prediction)
    
    def train(self, prices):
        """Train model on historical prices"""
        if len(prices) < 5:
            return False
        
        # Convert to numpy float64
        prices = [float(p) for p in prices]
        
        X = np.array(range(len(prices))).reshape(-1, 1).astype(np.float64)
        y = np.array(prices).astype(np.float64)
        
        self.model.fit(X, y)
        
        # Save model
        self.model_file.parent.mkdir(exist_ok=True)
        joblib.dump(self.model, self.model_file)
        return True

price_predictor = PricePredictor()