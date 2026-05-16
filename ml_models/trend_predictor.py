"""
Trend Predictor - Predicts price direction (Up/Down) using Random Forest
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path

class TrendPredictor:
    def __init__(self):
        self.model_file = Path("models/trend_predictor.pkl")
        self.scaler_file = Path("models/trend_scaler.pkl")
        self.model = None
        self.scaler = StandardScaler()
        self._load_model()
    
    def _load_model(self):
        if self.model_file.exists():
            self.model = joblib.load(self.model_file)
            self.scaler = joblib.load(self.scaler_file)
            print("✅ Trend Predictor model loaded")
        else:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            print("⚠️ New Trend Predictor model created")
    
    def _create_features(self, prices):
        if len(prices) < 20:
            return None, None
        
        X, y = [], []
        for i in range(20, len(prices) - 1):
            features = []
            
            # Price features
            features.append(prices[i] / prices[i-1] - 1)
            features.append(prices[i] / prices[i-5] - 1)
            features.append(prices[i] / prices[i-10] - 1)
            
            # Moving averages
            ma5 = np.mean(prices[i-5:i])
            ma10 = np.mean(prices[i-10:i])
            ma20 = np.mean(prices[i-20:i])
            features.append(prices[i] / ma5 - 1)
            features.append(prices[i] / ma10 - 1)
            features.append(prices[i] / ma20 - 1)
            
            # Volatility
            features.append(np.std(prices[i-10:i]))
            
            # Target: 1=up, 0=down
            y.append(1 if prices[i + 1] > prices[i] else 0)
            X.append(features)
        
        return np.array(X), np.array(y)
    
    def train(self, prices):
        X, y = self._create_features(prices)
        
        if X is None or len(X) == 0:
            print("⚠️ Not enough data for training")
            return False
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        
        train_acc = self.model.score(X_scaled, y)
        
        self.model_file.parent.mkdir(exist_ok=True)
        joblib.dump(self.model, self.model_file)
        joblib.dump(self.scaler, self.scaler_file)
        
        print(f"✅ Model trained on {len(X)} samples (Accuracy: {train_acc:.2%})")
        return True
    
    def predict_trend(self, prices):
        if self.model is None or len(prices) < 20:
            return "neutral", 50
        
        i = len(prices) - 1
        
        features = []
        features.append(prices[i] / prices[i-1] - 1)
        features.append(prices[i] / prices[i-5] - 1)
        features.append(prices[i] / prices[i-10] - 1)
        
        ma5 = np.mean(prices[i-5:i])
        ma10 = np.mean(prices[i-10:i])
        ma20 = np.mean(prices[i-20:i])
        features.append(prices[i] / ma5 - 1)
        features.append(prices[i] / ma10 - 1)
        features.append(prices[i] / ma20 - 1)
        features.append(np.std(prices[i-10:i]))
        
        X_pred = self.scaler.transform([features])
        prob = self.model.predict_proba(X_pred)[0]
        
        if prob[1] > 0.6:
            return "up", prob[1] * 100
        elif prob[0] > 0.6:
            return "down", prob[0] * 100
        else:
            return "neutral", 50

trend_predictor = TrendPredictor()