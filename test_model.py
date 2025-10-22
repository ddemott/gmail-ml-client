#!/usr/bin/env python3
"""Test the trained model"""

from model import predict

def test_model():
    test_messages = [
        "Meeting tomorrow at 3pm regarding project update",
        "URGENT!!! Win $1000000 now!!! Click here!!!",
        "Team standup scheduled for Monday morning",
        "Your order has been shipped",
        "Free money! Act now! Limited time offer!"
    ]
    
    print("🧪 Testing trained model:")
    print("=" * 60)
    
    try:
        labels, confidence, spam_scores = predict(test_messages)
        
        for i, msg in enumerate(test_messages):
            print(f"📧 \"{msg}\"")
            print(f"   🏷️  Predicted: {labels[i]} (confidence: {confidence[i]:.2f})")
            print(f"   🚨 Spam score: {spam_scores[i]:.2f}")
            print()
            
    except Exception as e:
        print(f"❌ Prediction failed: {e}")

if __name__ == "__main__":
    test_model()