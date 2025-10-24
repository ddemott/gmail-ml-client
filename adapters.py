"""
Adapter implementations that wrap existing code to implement the abstract interfaces.
These adapters allow the existing Gmail ML Client code to work with the new interface-based architecture.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import data_store

# Import existing modules
import gmail_client
import model
import preprocessor
from config_manager import get_config
from interfaces import (
    ConfigurationInterface,
    DatabaseInterface,
    EmailMessage,
    FileSystemInterface,
    GmailApiInterface,
    LabelInfo,
    LoggerInterface,
    ModelInterface,
    PredictionResult,
    TextProcessorInterface,
    TrainingMetrics,
)
from logger import logger


class GmailApiAdapter(GmailApiInterface):
    """Adapter for existing gmail_client module."""

    def __init__(self):
        self._service = None

    def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        try:
            self._service = gmail_client.build_service()
            return True
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False

    def get_labels(self) -> List[LabelInfo]:
        """Get all Gmail labels."""
        try:
            labels_data = gmail_client.get_labels()
            return [
                LabelInfo(
                    id=label.get("id", ""),
                    name=label.get("name", ""),
                    type=label.get("type", "user"),
                    messages_total=label.get("messagesTotal"),
                    messages_unread=label.get("messagesUnread"),
                )
                for label in labels_data
            ]
        except Exception as e:
            logger.error(f"Failed to get labels: {e}")
            return []

    def create_label(self, name: str) -> str:
        """Create a new label and return its ID."""
        try:
            return gmail_client.ensure_label(name)
        except Exception as e:
            logger.error(f"Failed to create label {name}: {e}")
            return ""

    def list_messages(self, query: Optional[str] = None, max_results: int = 100) -> List[str]:
        """List message IDs matching query."""
        try:
            return gmail_client.list_messages(query=query, max_results=max_results)
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            return []

    def get_message(self, message_id: str) -> EmailMessage:
        """Get full message data."""
        try:
            msg_data = gmail_client.get_message(message_id)
            return EmailMessage(
                id=msg_data["id"],
                subject=msg_data.get("subject", ""),
                sender=msg_data.get("sender", ""),
                body=msg_data.get("body", ""),
                labels=msg_data.get("labels", []),
                timestamp=datetime.fromisoformat(
                    msg_data.get("timestamp", datetime.now().isoformat())
                ),
                thread_id=msg_data.get("thread_id"),
                snippet=msg_data.get("snippet"),
            )
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            raise

    def modify_message_labels(
        self, message_id: str, add_labels: List[str], remove_labels: List[str]
    ) -> bool:
        """Modify message labels."""
        try:
            gmail_client.modify_labels(message_id, add_labels, remove_labels)
            return True
        except Exception as e:
            logger.error(f"Failed to modify labels for {message_id}: {e}")
            return False

    def trash_message(self, message_id: str) -> bool:
        """Move message to trash."""
        try:
            gmail_client.trash_message(message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to trash message {message_id}: {e}")
            return False

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        # This would need to be implemented based on quota tracking
        return {"remaining_quota": 1000000, "reset_time": datetime.now().isoformat()}


class DatabaseAdapter(DatabaseInterface):
    """Adapter for existing data_store module."""

    def __init__(self):
        self._initialized = False

    def initialize(self, connection_string: str) -> bool:
        """Initialize database connection."""
        try:
            data_store.init_db(connection_string)
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    def store_messages(self, messages: List[EmailMessage]) -> int:
        """Store messages and return count of successfully stored."""
        if not self._initialized:
            return 0

        stored_count = 0
        for msg in messages:
            try:
                # Convert EmailMessage to dict format expected by data_store
                msg_data = {
                    "id": msg.id,
                    "subject": msg.subject,
                    "sender": msg.sender,
                    "body": msg.body,
                    "labels": msg.labels,
                    "timestamp": msg.timestamp.isoformat(),
                }
                data_store.upsert_message(msg_data)
                stored_count += 1
            except Exception as e:
                logger.error(f"Failed to store message {msg.id}: {e}")

        return stored_count

    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        """Get a single message by ID."""
        try:
            msg_data = data_store.get_message(message_id)
            if not msg_data:
                return None

            return EmailMessage(
                id=msg_data["id"],
                subject=msg_data.get("subject", ""),
                sender=msg_data.get("sender", ""),
                body=msg_data.get("body", ""),
                labels=msg_data.get("labels", []),
                timestamp=datetime.fromisoformat(
                    msg_data.get("timestamp", datetime.now().isoformat())
                ),
            )
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return None

    def get_messages_for_training(self, limit: Optional[int] = None) -> List[EmailMessage]:
        """Get messages with user-reviewed labels for training."""
        try:
            messages_data = data_store.fetch_for_training(limit)
            return [
                EmailMessage(
                    id=msg["id"],
                    subject=msg.get("subject", ""),
                    sender=msg.get("sender", ""),
                    body=msg.get("body", ""),
                    labels=msg.get("labels", []),
                    timestamp=datetime.fromisoformat(
                        msg.get("timestamp", datetime.now().isoformat())
                    ),
                )
                for msg in messages_data
            ]
        except Exception as e:
            logger.error(f"Failed to get training messages: {e}")
            return []

    def get_messages_for_prediction(self, limit: Optional[int] = None) -> List[EmailMessage]:
        """Get unreviewed messages for prediction."""
        try:
            messages_data = data_store.fetch_for_prediction(limit)
            return [
                EmailMessage(
                    id=msg["id"],
                    subject=msg.get("subject", ""),
                    sender=msg.get("sender", ""),
                    body=msg.get("body", ""),
                    labels=msg.get("labels", []),
                    timestamp=datetime.fromisoformat(
                        msg.get("timestamp", datetime.now().isoformat())
                    ),
                )
                for msg in messages_data
            ]
        except Exception as e:
            logger.error(f"Failed to get messages for prediction: {e}")
            return []

    def mark_message_reviewed(self, message_id: str, label: str) -> bool:
        """Mark message as reviewed with given label."""
        try:
            data_store.mark_review(message_id, label)
            return True
        except Exception as e:
            logger.error(f"Failed to mark message {message_id} as reviewed: {e}")
            return False

    def save_prediction(self, message_id: str, prediction: PredictionResult) -> bool:
        """Save prediction result for message."""
        try:
            data_store.save_prediction(
                message_id,
                {
                    "predicted_label": prediction.predicted_label,
                    "confidence": prediction.confidence,
                    "alternatives": prediction.alternatives,
                },
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save prediction for {message_id}: {e}")
            return False

    def get_training_stats(self) -> Dict[str, Any]:
        """Get training data statistics."""
        try:
            return data_store.get_training_stats()
        except Exception as e:
            logger.error(f"Failed to get training stats: {e}")
            return {}


class FileSystemAdapter(FileSystemInterface):
    """Adapter for file system operations."""

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return os.path.exists(path)

    def read_file(self, path: str) -> str:
        """Read text file content."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise

    def write_file(self, path: str, content: str) -> bool:
        """Write content to text file."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            return False

    def read_binary_file(self, path: str) -> bytes:
        """Read binary file content."""
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read binary file {path}: {e}")
            raise

    def write_binary_file(self, path: str, content: bytes) -> bool:
        """Write binary content to file."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write binary file {path}: {e}")
            return False

    def create_directory(self, path: str) -> bool:
        """Create directory if it doesn't exist."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
        """List files in directory matching pattern."""
        try:
            import glob

            if pattern:
                return glob.glob(os.path.join(directory, pattern))
            else:
                return [
                    os.path.join(directory, f)
                    for f in os.listdir(directory)
                    if os.path.isfile(os.path.join(directory, f))
                ]
        except Exception as e:
            logger.error(f"Failed to list files in {directory}: {e}")
            return []

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(path)
        except Exception as e:
            logger.error(f"Failed to get size of {path}: {e}")
            return 0

    def get_file_modified_time(self, path: str) -> datetime:
        """Get file last modified time."""
        try:
            timestamp = os.path.getmtime(path)
            return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.error(f"Failed to get modified time of {path}: {e}")
            return datetime.now()


class ModelAdapter(ModelInterface):
    """Adapter for existing model module."""

    def load_model(self, model_path: str) -> bool:
        """Load trained model from path."""
        try:
            model.load_model(model_path)
            return True
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            return False

    def save_model(self, model_path: str) -> bool:
        """Save current model to path."""
        try:
            model.save_model(model_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save model to {model_path}: {e}")
            return False

    def train(
        self, training_data: List[Tuple[str, str]], epochs: int = 6, batch_size: int = 64
    ) -> TrainingMetrics:
        """Train model on labeled data."""
        try:
            # Convert data format for existing model
            texts = [item[0] for item in training_data]
            labels = [item[1] for item in training_data]

            metrics = model.train(texts, labels, epochs=epochs, batch_size=batch_size)

            return TrainingMetrics(
                accuracy=metrics.get("accuracy", 0.0),
                precision=metrics.get("precision", {}),
                recall=metrics.get("recall", {}),
                f1_score=metrics.get("f1_score", {}),
                confusion_matrix=metrics.get("confusion_matrix", []),
            )
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise

    def predict(self, text: str) -> PredictionResult:
        """Predict label for given text."""
        try:
            predictions = model.predict_single_email({"body": text, "subject": ""})

            main_prediction = (
                predictions[0] if predictions else {"label": "UNKNOWN", "confidence": 0.0}
            )
            alternatives = (
                [(p["label"], p["confidence"]) for p in predictions[1:]]
                if len(predictions) > 1
                else []
            )

            return PredictionResult(
                predicted_label=main_prediction["label"],
                confidence=main_prediction["confidence"],
                alternatives=alternatives,
                features_used=["tfidf", "neural_network"],
            )
        except Exception as e:
            logger.error(f"Prediction failed for text: {e}")
            raise

    def predict_batch(self, texts: List[str]) -> List[PredictionResult]:
        """Predict labels for multiple texts."""
        return [self.predict(text) for text in texts]

    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata and performance info."""
        try:
            return model.get_model_info()
        except Exception:
            return {"status": "unknown", "last_trained": None}

    def is_trained(self) -> bool:
        """Check if model is trained and ready."""
        try:
            return model.is_model_trained()
        except Exception:
            return False


class TextProcessorAdapter(TextProcessorInterface):
    """Adapter for existing preprocessor module."""

    def extract_features(self, text: str) -> Dict[str, Any]:
        """Extract features from text."""
        try:
            return preprocessor.extract_features(text)
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return {}

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        try:
            return preprocessor.clean_text(text)
        except Exception as e:
            logger.error(f"Text cleaning failed: {e}")
            return text

    def extract_email_body(self, raw_content: str) -> str:
        """Extract body text from raw email content."""
        try:
            return preprocessor.extract_text(raw_content)
        except Exception as e:
            logger.error(f"Email body extraction failed: {e}")
            return raw_content

    def detect_language(self, text: str) -> str:
        """Detect text language."""
        # This would need to be implemented if language detection is needed
        return "en"  # Default to English


class ConfigurationAdapter(ConfigurationInterface):
    """Adapter for configuration management."""

    def __init__(self):
        self._config = get_config()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        try:
            # Navigate nested config structure
            parts = key.split(".")
            value = self._config
            for part in parts:
                value = getattr(value, part)
            return value
        except (AttributeError, KeyError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        # This would need to be implemented for dynamic config updates
        logger.warning(f"Dynamic config update not implemented for key: {key}")

    def reload(self) -> None:
        """Reload configuration from source."""
        from config_manager import reload_config

        self._config = reload_config()

    def validate(self) -> List[str]:
        """Validate configuration and return errors."""
        return self._config.validate()


class LoggerAdapter(LoggerInterface):
    """Adapter for existing logger."""

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        logger.critical(message, **kwargs)
