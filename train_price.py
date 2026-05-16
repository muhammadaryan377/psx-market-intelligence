import numpy as np
from ml_models.price_predictor import price_predictor

# 100 sample prices (dynamically generated)
prices = []
base = 100
for i in range(100):
    # Add random movement
    change = np.random.uniform(-2, 3)
    base = base + change
    prices.append(max(50, base))  # Ensure price doesn't go below 50

print(f"Generated {len(prices)} price points")
print(f"First 10: {prices[:10]}")
print(f"Last 10: {prices[-10:]}")

print("\nTraining Price Predictor...")
result = price_predictor.train(prices)

if result:
    print("✅ Price Predictor trained successfully!")
    
    # Test prediction
    test_price = price_predictor.predict_next_price(prices)
    print(f"📈 Next predicted price: {test_price:.2f}")
else:
    print("❌ Training failed")