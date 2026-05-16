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
            try:
                self.model = joblib.load(self.model_file)
                self.scaler = joblib.load(self.scaler_file)
                print("✅ Trend Predictor model loaded")
            except:
                self.model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
                print("⚠️ New Trend Predictor model created")
        else:
            self.model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
            print("⚠️ New Trend Predictor model created")
    
    def _create_features(self, prices):
        """Create features for trend prediction"""
        if len(prices) < 10:
            return None
        
        features = []
        
        # Price features
        features.append(prices[-1] / prices[-2] - 1 if len(prices) >= 2 else 0)  # Daily return
        features.append(prices[-1] / prices[-5] - 1 if len(prices) >= 5 else 0)  # 5-day return
        features.append(prices[-1] / prices[-10] - 1 if len(prices) >= 10 else 0)  # 10-day return
        
        # Moving averages
        ma5 = np.mean(prices[-5:]) if len(prices) >= 5 else prices[-1]
        ma10 = np.mean(prices[-10:]) if len(prices) >= 10 else prices[-1]
        ma20 = np.mean(prices[-20:]) if len(prices) >= 20 else prices[-1]
        features.append(prices[-1] / ma5 - 1 if ma5 > 0 else 0)
        features.append(prices[-1] / ma10 - 1 if ma10 > 0 else 0)
        features.append(prices[-1] / ma20 - 1 if ma20 > 0 else 0)
        
        # Volatility
        features.append(np.std(prices[-10:]) if len(prices) >= 10 else 0)
        
        # Momentum
        features.append(prices[-1] - prices[-2] if len(prices) >= 2 else 0)
        
        return features
    
    def train(self, prices, labels=None):
        """Train trend prediction model"""
        if len(prices) < 20:
            print("⚠️ Not enough data for training")
            return False
        
        X = []
        y = []
        
        for i in range(10, len(prices) - 1):
            window = prices[:i+1]
            features = self._create_features(window)
            if features:
                X.append(features)
                # Label: 1 if price increased, 0 if decreased
                y.append(1 if prices[i+1] > prices[i] else 0)
        
        if len(X) < 5:
            return False
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        
        self.model_file.parent.mkdir(exist_ok=True)
        joblib.dump(self.model, self.model_file)
        joblib.dump(self.scaler, self.scaler_file)
        
        print(f"✅ Trend model trained on {len(X)} samples")
        return True
    
    def predict_trend(self, prices):
        """Predict next day trend with proper confidence"""
        if len(prices) < 10:
            return "neutral", 50
        
        # Calculate price momentum
        recent_prices = prices[-5:]
        price_trend = recent_prices[-1] - recent_prices[0]
        price_change_pct = (price_trend / recent_prices[0]) * 100 if recent_prices[0] > 0 else 0
        
        # Calculate volatility
        volatility = np.std(prices[-10:]) if len(prices) >= 10 else 0
        avg_price = np.mean(prices[-10:]) if len(prices) >= 10 else prices[-1]
        volatility_pct = (volatility / avg_price) * 100 if avg_price > 0 else 0
        
        # Determine trend based on price movement
        if price_change_pct > 1.5:
            trend = "up"
            confidence = min(85, 65 + abs(price_change_pct) * 5)
        elif price_change_pct > 0.5:
            trend = "up"
            confidence = 60
        elif price_change_pct < -1.5:
            trend = "down"
            confidence = min(85, 65 + abs(price_change_pct) * 5)
        elif price_change_pct < -0.5:
            trend = "down"
            confidence = 60
        else:
            trend = "neutral"
            confidence = 50
        
        # Adjust confidence based on volatility
        if volatility_pct > 5:
            confidence = min(confidence, 65)  # High volatility = less confidence
        elif volatility_pct < 2:
            confidence = min(confidence + 10, 85)  # Low volatility = more confidence
        
        # Use trained model if available
        if self.model is not None and len(prices) >= 10:
            try:
                features = self._create_features(prices)
                if features:
                    X_pred = self.scaler.transform([features])
                    prob = self.model.predict_proba(X_pred)[0]
                    
                    if len(prob) > 1:
                        model_confidence = max(prob[0], prob[1]) * 100
                        # Blend with price-based confidence
                        confidence = int((confidence + model_confidence) / 2)
                        
                        if prob[1] > prob[0]:
                            trend = "up"
                        else:
                            trend = "down"
            except:
                pass
        
        return trend, int(confidence)
    
    def get_confidence_level(self, prices):
        """Get confidence level for prediction"""
        if len(prices) < 10:
            return 50
        
        # Calculate confidence based on trend strength
        recent = prices[-10:]
        ups = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
        trend_strength = abs(ups - (len(recent)-1 - ups)) / (len(recent)-1)
        
        base_confidence = 50 + (trend_strength * 40)
        
        # Adjust based on volatility
        volatility = np.std(prices[-10:])
        avg_price = np.mean(prices[-10:])
        volatility_pct = (volatility / avg_price) * 100 if avg_price > 0 else 0
        
        if volatility_pct > 5:
            base_confidence -= 15
        elif volatility_pct < 2:
            base_confidence += 10
        
        return min(85, max(50, int(base_confidence)))

trend_predictor = TrendPredictor()