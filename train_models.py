"""
Train ML Models - Simple training script
"""
import numpy as np
from ml_models.price_predictor import price_predictor

# Sample historical prices (50 days)
sample_prices = [
    100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
    110, 112, 111, 113, 115, 114, 116, 118, 117, 119,
    120, 122, 121, 123, 125, 124, 126, 128, 127, 129,
    130, 132, 131, 133, 135, 134, 136, 138, 137, 139,
    140, 142, 141, 143, 145, 144, 146, 148, 147, 149
]

print("="*50)
print("Training Price Predictor Model")
print("="*50)

result = price_predictor.train(sample_prices)

if result:
    print("✅ Model trained successfully!")
else:
    print("❌ Training failed")

print("="*50)