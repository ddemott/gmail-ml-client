"""
Mock implementations for testing.
Provides controllable, predictable implementations of all external dependencies.
"""

import json
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock

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


class MockGmailApi(GmailApiInterface):
    """Mock Gmail API for testing."""

    def __init__(self):
        self.authenticated = False
        self.labels = [
            LabelInfo(
                id="label_1", name="INBOX", type="system", messages_total=100, messages_unread=5
            ),
            LabelInfo(id="label_2", name="Work", type="user", messages_total=50, messages_unread=2),
            LabelInfo(
                id="label_3", name="Personal", type="user", messages_total=30, messages_unread=1
            ),
        ]
        self.messages = {
            "msg_1": EmailMessage(
                id="msg_1",
                subject="Test Email 1",
                sender="test1@example.com",
                body="This is a test email body",
                labels=["INBOX", "Work"],
                timestamp=datetime(2024, 1, 1, 10, 0, 0),
                thread_id="thread_1",
                snippet="This is a test...",
            ),
            "msg_2": EmailMessage(
                id="msg_2",
                subject="Test Email 2",
                sender="test2@example.com",
                body="Another test email body",
                labels=["INBOX"],
                timestamp=datetime(2024, 1, 2, 10, 0, 0),
                thread_id="thread_2",
                snippet="Another test...",
            ),
        }
        self.call_log = []
        self.should_fail = False
        self.rate_limit_remaining = 1000

    def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        self.call_log.append(("authenticate",))
        if self.should_fail:
            return False
        self.authenticated = True
        return True

    def get_labels(self) -> List[LabelInfo]:
        """Get all Gmail labels."""
        self.call_log.append(("get_labels",))
        if not self.authenticated or self.should_fail:
            return []
        return self.labels.copy()

    def create_label(self, name: str) -> str:
        """Create a new label and return its ID."""
        self.call_log.append(("create_label", name))
        if not self.authenticated or self.should_fail:
            return ""

        label_id = f"label_{len(self.labels) + 1}"
        self.labels.append(LabelInfo(id=label_id, name=name, type="user"))
        return label_id

    def list_messages(self, query: Optional[str] = None, max_results: int = 100) -> List[str]:
        """List message IDs matching query."""
        self.call_log.append(("list_messages", query, max_results))
        if not self.authenticated or self.should_fail:
            return []

        message_ids = list(self.messages.keys())
        return message_ids[:max_results]

    def get_message(self, message_id: str) -> EmailMessage:
        """Get full message data."""
        self.call_log.append(("get_message", message_id))
        if not self.authenticated or self.should_fail:
            raise Exception("Mock failure")

        if message_id not in self.messages:
            raise Exception(f"Message {message_id} not found")

        return self.messages[message_id]

    def modify_message_labels(
        self, message_id: str, add_labels: List[str], remove_labels: List[str]
    ) -> bool:
        """Modify message labels."""
        self.call_log.append(("modify_message_labels", message_id, add_labels, remove_labels))
        if not self.authenticated or self.should_fail:
            return False

        if message_id in self.messages:
            msg = self.messages[message_id]
            for label in add_labels:
                if label not in msg.labels:
                    msg.labels.append(label)
            for label in remove_labels:
                if label in msg.labels:
                    msg.labels.remove(label)
            return True
        return False

    def trash_message(self, message_id: str) -> bool:
        """Move message to trash."""
        self.call_log.append(("trash_message", message_id))
        if not self.authenticated or self.should_fail:
            return False

        if message_id in self.messages:
            self.messages[message_id].labels = ["TRASH"]
            return True
        return False

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        self.call_log.append(("get_rate_limit_status",))
        return {
            "remaining_quota": self.rate_limit_remaining,
            "reset_time": datetime.now().isoformat(),
        }

    # Test helper methods
    def set_should_fail(self, should_fail: bool):
        """Control whether operations should fail."""
        self.should_fail = should_fail

    def add_test_message(self, message: EmailMessage):
        """Add a test message."""
        self.messages[message.id] = message

    def get_call_log(self) -> List[Tuple]:
        """Get log of all API calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()

    def clear_data(self):
        """Clear all stored data."""
        self.messages.clear()


class MockDatabase(DatabaseInterface):
    """Mock database for testing."""

    def __init__(self):
        self.initialized = False
        self.messages: Dict[str, EmailMessage] = {}
        self.reviewed_messages: Dict[str, str] = {}  # message_id -> label
        self.predictions: Dict[str, PredictionResult] = {}
        self.call_log = []
        self.should_fail = False

    def initialize(self, connection_string: str) -> bool:
        """Initialize database connection."""
        self.call_log.append(("initialize", connection_string))
        if self.should_fail:
            return False
        self.initialized = True
        return True

    def store_messages(self, messages: List[EmailMessage]) -> int:
        """Store messages and return count of successfully stored."""
        self.call_log.append(("store_messages", len(messages)))
        if not self.initialized or self.should_fail:
            return 0

        stored_count = 0
        for msg in messages:
            self.messages[msg.id] = msg
            stored_count += 1
        return stored_count

    def get_message(self, message_id: str) -> Optional[EmailMessage]:
        """Get a single message by ID."""
        self.call_log.append(("get_message", message_id))
        if not self.initialized or self.should_fail:
            return None
        return self.messages.get(message_id)

    def get_messages_for_training(self, limit: Optional[int] = None) -> List[EmailMessage]:
        """Get messages with user-reviewed labels for training."""
        self.call_log.append(("get_messages_for_training", limit))
        if not self.initialized or self.should_fail:
            return []

        reviewed_messages = [
            msg for msg_id, msg in self.messages.items() if msg_id in self.reviewed_messages
        ]

        if limit:
            reviewed_messages = reviewed_messages[:limit]

        return reviewed_messages

    def get_messages_for_prediction(self, limit: Optional[int] = None) -> List[EmailMessage]:
        """Get unreviewed messages for prediction."""
        self.call_log.append(("get_messages_for_prediction", limit))
        if not self.initialized or self.should_fail:
            return []

        unreviewed_messages = [
            msg for msg_id, msg in self.messages.items() if msg_id not in self.reviewed_messages
        ]

        if limit:
            unreviewed_messages = unreviewed_messages[:limit]

        return unreviewed_messages

    def get_unreviewed_messages(self, limit: int = 200) -> List[Tuple[str, str]]:
        """Get unreviewed messages as (id, snippet) tuples for compatibility."""
        messages = self.get_messages_for_prediction(limit)
        return [(msg.id, msg.snippet or "") for msg in messages]

    def mark_message_reviewed(self, message_id: str, label: str) -> bool:
        """Mark message as reviewed with given label."""
        self.call_log.append(("mark_message_reviewed", message_id, label))
        if not self.initialized or self.should_fail:
            return False

        if message_id in self.messages:
            self.reviewed_messages[message_id] = label
            # Update the message labels to include the review label
            self.messages[message_id].labels = [label]
            return True
        return False

    def save_prediction(self, message_id: str, prediction: PredictionResult) -> bool:
        """Save prediction result for message."""
        self.call_log.append(("save_prediction", message_id))
        if not self.initialized or self.should_fail:
            return False

        self.predictions[message_id] = prediction
        return True

    def get_training_stats(self) -> Dict[str, Any]:
        """Get training data statistics."""
        self.call_log.append(("get_training_stats",))
        if not self.initialized or self.should_fail:
            return {}

        label_counts = {}
        for label in self.reviewed_messages.values():
            label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "total_reviewed": len(self.reviewed_messages),
            "label_counts": label_counts,
            "total_messages": len(self.messages),
        }

    # Test helper methods
    def set_should_fail(self, should_fail: bool):
        """Control whether operations should fail."""
        self.should_fail = should_fail

    def add_test_message(
        self, message: EmailMessage, is_reviewed: bool = False, review_label: str = None
    ):
        """Add a test message."""
        self.messages[message.id] = message
        if is_reviewed and review_label:
            self.reviewed_messages[message.id] = review_label
            # Update the message labels to include the review label
            message.labels = [review_label]

    def get_call_log(self) -> List[Tuple]:
        """Get log of all database calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()

    def clear_data(self):
        """Clear all stored data."""
        self.messages.clear()
        self.reviewed_messages.clear()
        self.predictions.clear()


class MockFileSystem(FileSystemInterface):
    """Mock file system for testing."""

    def __init__(self):
        self.files: Dict[str, str] = {}  # path -> content
        self.binary_files: Dict[str, bytes] = {}  # path -> binary content
        self.call_log = []
        self.should_fail = False

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        self.call_log.append(("file_exists", path))
        return path in self.files or path in self.binary_files

    def read_file(self, path: str) -> str:
        """Read text file content."""
        self.call_log.append(("read_file", path))
        if self.should_fail:
            raise Exception("Mock file system failure")

        if path not in self.files:
            raise FileNotFoundError(f"File not found: {path}")

        return self.files[path]

    def write_file(self, path: str, content: str) -> bool:
        """Write content to text file."""
        self.call_log.append(("write_file", path, len(content)))
        if self.should_fail:
            return False

        self.files[path] = content
        return True

    def read_binary_file(self, path: str) -> bytes:
        """Read binary file content."""
        self.call_log.append(("read_binary_file", path))
        if self.should_fail:
            raise Exception("Mock file system failure")

        if path not in self.binary_files:
            raise FileNotFoundError(f"Binary file not found: {path}")

        return self.binary_files[path]

    def write_binary_file(self, path: str, content: bytes) -> bool:
        """Write binary content to file."""
        self.call_log.append(("write_binary_file", path, len(content)))
        if self.should_fail:
            return False

        self.binary_files[path] = content
        return True

    def create_directory(self, path: str) -> bool:
        """Create directory if it doesn't exist."""
        self.call_log.append(("create_directory", path))
        if self.should_fail:
            return False
        # Mock implementation - just return True
        return True

    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
        """List files in directory matching pattern."""
        self.call_log.append(("list_files", directory, pattern))
        if self.should_fail:
            return []

        # Simple pattern matching for testing
        all_files = list(self.files.keys()) + list(self.binary_files.keys())
        dir_files = [f for f in all_files if f.startswith(directory)]

        if pattern:
            # Very simple pattern matching for testing
            dir_files = [f for f in dir_files if pattern.replace("*", "") in f]

        return dir_files

    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        self.call_log.append(("get_file_size", path))
        if path in self.files:
            return len(self.files[path].encode("utf-8"))
        elif path in self.binary_files:
            return len(self.binary_files[path])
        return 0

    def get_file_modified_time(self, path: str) -> datetime:
        """Get file last modified time."""
        self.call_log.append(("get_file_modified_time", path))
        # Return fixed time for testing
        return datetime(2024, 1, 1, 12, 0, 0)

    # Test helper methods
    def set_should_fail(self, should_fail: bool):
        """Control whether operations should fail."""
        self.should_fail = should_fail

    def add_test_file(self, path: str, content: str):
        """Add a test file."""
        self.files[path] = content

    def add_test_binary_file(self, path: str, content: bytes):
        """Add a test binary file."""
        self.binary_files[path] = content

    def get_call_log(self) -> List[Tuple]:
        """Get log of all file system calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()


class MockModel(ModelInterface):
    """Mock ML model for testing."""

    def __init__(self):
        self.trained = False
        self.model_path = None
        self.training_data = []
        self.call_log = []
        self.should_fail = False
        self.prediction_map = {
            "work email": ("Work", 0.95),
            "project": ("Work", 0.90),
            "deadline": ("Work", 0.85),
            "meeting": ("Work", 0.80),
            "personal email": ("Personal", 0.85),
            "family": ("Personal", 0.90),
            "dinner": ("Personal", 0.80),
            "weekend": ("Personal", 0.75),
            "spam email": ("SPAM", 0.95),
            "buy now": ("SPAM", 0.98),
            "limited offer": ("SPAM", 0.97),
            "win money": ("SPAM", 0.96),
            "amazing deal": ("SPAM", 0.94),
            "incredible opportunity": ("SPAM", 0.93),
        }

    def load_model(self, model_path: str) -> bool:
        """Load trained model from path."""
        self.call_log.append(("load_model", model_path))
        if self.should_fail:
            return False

        self.model_path = model_path
        self.trained = True
        return True

    def save_model(self, model_path: str) -> bool:
        """Save current model to path."""
        self.call_log.append(("save_model", model_path))
        if self.should_fail:
            return False

        self.model_path = model_path
        return True

    def train(
        self, training_data: List[Tuple[str, str]], epochs: int = 6, batch_size: int = 64
    ) -> TrainingMetrics:
        """Train model on labeled data."""
        self.call_log.append(("train", len(training_data), epochs, batch_size))
        if self.should_fail:
            raise Exception("Mock training failure")

        self.training_data = training_data
        self.trained = True

        # Mock training metrics
        unique_labels = list(set(label for _, label in training_data))
        return TrainingMetrics(
            accuracy=0.85,
            precision={label: 0.80 + (i * 0.05) for i, label in enumerate(unique_labels)},
            recall={label: 0.82 + (i * 0.03) for i, label in enumerate(unique_labels)},
            f1_score={label: 0.81 + (i * 0.04) for i, label in enumerate(unique_labels)},
            confusion_matrix=[[10, 2], [1, 12]],  # Simple 2x2 for testing
        )

    def predict(self, text: str) -> PredictionResult:
        """Predict label for given text."""
        self.call_log.append(("predict", text[:50]))  # Log first 50 chars
        if not self.trained or self.should_fail:
            raise Exception("Model not trained or mock failure")

        # Simple rule-based prediction for testing
        text_lower = text.lower()

        for keyword, (label, confidence) in self.prediction_map.items():
            if keyword in text_lower:
                return PredictionResult(
                    predicted_label=label,
                    confidence=confidence,
                    alternatives=[("Other", 1.0 - confidence)],
                    features_used=["mock_keyword_match"],
                )

        # Default prediction
        return PredictionResult(
            predicted_label="Unknown",
            confidence=0.5,
            alternatives=[("SPAM", 0.3), ("Personal", 0.2)],
            features_used=["mock_default"],
        )

    def predict_batch(self, texts: List[str]) -> List[PredictionResult]:
        """Predict labels for multiple texts."""
        self.call_log.append(("predict_batch", len(texts)))
        return [self.predict(text) for text in texts]

    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata and performance info."""
        self.call_log.append(("get_model_info",))
        return {
            "trained": self.trained,
            "model_path": self.model_path,
            "training_samples": len(self.training_data),
            "last_trained": "2024-01-01T10:00:00" if self.trained else None,
        }

    def is_trained(self) -> bool:
        """Check if model is trained and ready."""
        self.call_log.append(("is_trained",))
        return self.trained

    # Test helper methods
    def set_should_fail(self, should_fail: bool):
        """Control whether operations should fail."""
        self.should_fail = should_fail

    def set_prediction_map(self, prediction_map: Dict[str, Tuple[str, float]]):
        """Set custom prediction mapping for testing."""
        self.prediction_map = prediction_map

    def get_call_log(self) -> List[Tuple]:
        """Get log of all model calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()


class MockTextProcessor(TextProcessorInterface):
    """Mock text processor for testing."""

    def __init__(self):
        self.call_log = []
        self.should_fail = False

    def extract_features(self, text: str) -> Dict[str, Any]:
        """Extract features from text."""
        self.call_log.append(("extract_features", len(text)))
        if self.should_fail:
            return {}

        return {
            "word_count": len(text.split()),
            "char_count": len(text),
            "has_exclamation": "!" in text,
            "has_question": "?" in text,
            "all_caps_ratio": sum(1 for c in text if c.isupper()) / len(text) if text else 0,
        }

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        self.call_log.append(("clean_text", len(text)))
        if self.should_fail:
            return text

        # Simple cleaning for testing
        return text.strip().lower()

    def extract_email_body(self, raw_content: str) -> str:
        """Extract body text from raw email content."""
        self.call_log.append(("extract_email_body", len(raw_content)))
        if self.should_fail:
            return raw_content

        # Mock extraction - just return the content
        return raw_content

    def detect_language(self, text: str) -> str:
        """Detect text language."""
        self.call_log.append(("detect_language", len(text)))
        # Always return English for testing
        return "en"

    # Test helper methods
    def set_should_fail(self, should_fail: bool):
        """Control whether operations should fail."""
        self.should_fail = should_fail

    def get_call_log(self) -> List[Tuple]:
        """Get log of all text processing calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()


class MockConfiguration(ConfigurationInterface):
    """Mock configuration for testing."""

    def __init__(self):
        self.config_data = {
            "database.path": "test.db",
            "model.max_features": 1000,
            "thresholds.spam": 0.85,
            "thresholds.certain": 0.92,
            "gmail.sync_page_size": 100,
        }
        self.call_log = []
        self.should_fail = False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        self.call_log.append(("get", key, default))
        if self.should_fail:
            return default
        return self.config_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.call_log.append(("set", key, value))
        if not self.should_fail:
            self.config_data[key] = value

    def reload(self) -> None:
        """Reload configuration from source."""
        self.call_log.append(("reload",))
        # Mock reload - no-op for testing

    def validate(self) -> List[str]:
        """Validate configuration and return errors."""
        self.call_log.append(("validate",))
        if self.should_fail:
            return ["Mock validation error"]
        return []

    # Test helper methods
    def set_should_fail(self, should_fail: bool):
        """Control whether operations should fail."""
        self.should_fail = should_fail

    def set_config_data(self, config_data: Dict[str, Any]):
        """Set custom configuration data for testing."""
        self.config_data = config_data

    def get_call_log(self) -> List[Tuple]:
        """Get log of all configuration calls made."""
        return self.call_log.copy()

    def clear_call_log(self):
        """Clear the call log."""
        self.call_log.clear()


class MockLogger(LoggerInterface):
    """Mock logger for testing."""

    def __init__(self):
        self.logs = []
        self.call_log = []
        self._lock = threading.Lock()

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        with self._lock:
            self.logs.append(("DEBUG", message, kwargs))
            self.call_log.append(("debug", message))

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        with self._lock:
            self.logs.append(("INFO", message, kwargs))
            self.call_log.append(("info", message))

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        with self._lock:
            self.logs.append(("WARNING", message, kwargs))
            self.call_log.append(("warning", message))

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        with self._lock:
            self.logs.append(("ERROR", message, kwargs))
            self.call_log.append(("error", message))

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        with self._lock:
            self.logs.append(("CRITICAL", message, kwargs))
            self.call_log.append(("critical", message))

    # Test helper methods
    def get_logs(self, level: Optional[str] = None) -> List[Tuple]:
        """Get all logged messages, optionally filtered by level."""
        with self._lock:
            if level:
                return [log for log in self.logs if log[0] == level]
            return self.logs.copy()

    def clear_logs(self):
        """Clear all logged messages."""
        with self._lock:
            self.logs.clear()
            self.call_log.clear()

    def get_call_log(self) -> List[Tuple]:
        """Get log of all logging calls made."""
        with self._lock:
            return self.call_log.copy()
