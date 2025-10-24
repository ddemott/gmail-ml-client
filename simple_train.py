#!/usr/bin/env python3
"""
Simple training script for Gmail ML Client
"""

import os

import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder

from cfg import MODEL_DIR
from data_store import fetch_for_training, init_db
from model import build_net, build_vectorizer, ensure_model_dir


def simple_train():
    """Train model with minimal validation for small datasets."""
    print("🤖 Starting simple training...")

    # Initialize database
    init_db()

    # Get training data
    texts, labels = fetch_for_training()
    print(f"📊 Found {len(texts)} reviewed messages")

    if len(texts) < 2:
        print("❌ Need at least 2 labeled examples to train")
        print("💡 Use the web interface to review more emails:")
        print("   1. Start server: python -m uvicorn api:app --host localhost --port 8000")
        print("   2. Visit: http://localhost:8000/docs")
        print("   3. Use /api/sync to get emails and /api/review to label them")
        return False

    if len(set(labels)) < 2:
        print("❌ Need at least 2 different labels to train")
        print(f"   Current labels: {set(labels)}")
        return False

    try:
        print(f"🏷️  Training with labels: {list(set(labels))}")

        # Build vectorizer and transform text
        vect = build_vectorizer()
        X = vect.fit_transform(texts)
        print(f"📝 Vectorized to {X.shape[1]} features")

        # Encode labels
        le = LabelEncoder()
        y = le.fit_transform(labels)

        # Build and train model
        model = build_net(X.shape[1], len(le.classes_))

        # Simple training without validation split for small datasets
        print("🔄 Training neural network...")
        history = model.fit(X.toarray(), y, epochs=6, batch_size=min(32, len(texts)), verbose=1)

        # Save model artifacts
        ensure_model_dir()

        vect_path = os.path.join(MODEL_DIR, "tfidf.joblib")
        label_path = os.path.join(MODEL_DIR, "labels.joblib")
        model_path = os.path.join(MODEL_DIR, "model.keras")

        joblib.dump(vect, vect_path)
        joblib.dump(le, label_path)
        model.save(model_path)

        print("✅ Model trained and saved successfully!")
        print(f"🎯 Classes: {list(le.classes_)}")
        print(f"📁 Model saved to: {MODEL_DIR}")

        # Test prediction
        print("\n🧪 Testing prediction...")
        predictions = model.predict(X.toarray())
        accuracy = np.mean(np.argmax(predictions, axis=1) == y)
        print(f"📊 Training accuracy: {accuracy:.2%}")

        return True

    except Exception as e:
        print(f"❌ Training failed: {e}")
        return False


if __name__ == "__main__":
    simple_train()
