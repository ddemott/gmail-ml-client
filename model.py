from __future__ import annotations
import os, joblib, numpy as np
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from tensorflow import keras
from cfg import MODEL_DIR
from logger import logger

VECT_PATH = os.path.join(MODEL_DIR, "tfidf.joblib")
LABE_PATH = os.path.join(MODEL_DIR, "labels.joblib")
KerasPath = os.path.join(MODEL_DIR, "model.keras")

def ensure_model_dir():
    os.makedirs(MODEL_DIR, exist_ok=True)

def build_vectorizer():
    return TfidfVectorizer(max_features=50000, ngram_range=(1,2), min_df=2)

def build_net(input_dim: int, output_dim: int):
    model = keras.Sequential([
        keras.layers.Input(shape=(input_dim,), dtype="float32"),
        keras.layers.Dense(256, activation="relu"),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(128, activation="relu"),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(output_dim, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model

def train(texts: List[str], labels: List[str], epochs: int = 6, batch_size: int = 64):
    """Train the neural classifier with enhanced error handling and validation."""
    try:
        if not texts or not labels:
            raise ValueError("Cannot train with empty texts or labels")
        
        if len(texts) != len(labels):
            raise ValueError(f"Texts ({len(texts)}) and labels ({len(labels)}) must have same length")
        
        if len(set(labels)) < 2:
            raise ValueError(f"Need at least 2 different labels for training, got: {set(labels)}")
        
        logger.info(f"Training with {len(texts)} samples, {len(set(labels))} classes")
        
        ensure_model_dir()
        
        # Build vectorizer and transform texts
        vect = build_vectorizer()
        X = vect.fit_transform(texts)
        logger.info(f"Vectorized to {X.shape[1]} features")
        
        # Encode labels
        le = LabelEncoder()
        y = le.fit_transform(labels)
        
        # Split for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X.toarray(), y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Build and train model
        model = build_net(X.shape[1], len(le.classes_))
        
        # Add early stopping
        early_stopping = keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=2, restore_best_weights=True
        )
        
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
            callbacks=[early_stopping]
        )
        
        # Save model artifacts
        joblib.dump(vect, VECT_PATH)
        joblib.dump(le, LABE_PATH)
        model.save(KerasPath)
        logger.info("Model artifacts saved")
        
        # Generate validation report
        val_preds = model.predict(X_val, verbose=0).argmax(axis=1)
        report = classification_report(y_val, val_preds, target_names=le.classes_)
        
        logger.info(f"Training completed. Final validation accuracy: {history.history['val_accuracy'][-1]:.3f}")
        return report, list(le.classes_)
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise

def load():
    """Load trained model with error handling."""
    try:
        if not all(os.path.exists(path) for path in [VECT_PATH, LABE_PATH, KerasPath]):
            raise FileNotFoundError("Model artifacts not found. Train the model first.")
        
        vect = joblib.load(VECT_PATH)
        le = joblib.load(LABE_PATH)
        model = keras.models.load_model(KerasPath)
        
        logger.debug("Model artifacts loaded successfully")
        return vect, le, model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

def predict(texts: List[str]):
    """Make predictions with error handling."""
    try:
        if not texts:
            logger.warning("No texts provided for prediction")
            return [], [], []
        
        vect, le, model = load()
        X = vect.transform(texts).toarray()
        
        if X.shape[1] == 0:
            logger.warning("No features after vectorization")
            return ["UNKNOWN"] * len(texts), [0.0] * len(texts), [0.5] * len(texts)
        
        probs = model.predict(X, verbose=0)
        idx = probs.argmax(axis=1)
        labels = le.inverse_transform(idx)
        conf = probs.max(axis=1)
        
        # Calculate spam scores
        spam_idx = None
        for i, name in enumerate(le.classes_):
            if name.lower() in ("spam", "junk"):
                spam_idx = i
                break
        
        spam_scores = probs[:, spam_idx] if spam_idx is not None else 1.0 - conf
        
        logger.debug(f"Made predictions for {len(texts)} texts")
        return labels, conf, spam_scores
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        # Return safe defaults
        return ["UNKNOWN"] * len(texts), [0.0] * len(texts), [0.5] * len(texts)
