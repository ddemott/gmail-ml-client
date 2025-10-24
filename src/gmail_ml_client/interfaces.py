"""
Abstract interfaces for external dependencies to enable comprehensive testing.
Separates business logic from external systems (Gmail API, database, file system).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


# Data Transfer Objects for clean interface boundaries
@dataclass
class EmailMessage:
    """Clean email data structure."""

    id: str
    subject: str
    sender: str
    body: str
    labels: list[str]
    timestamp: datetime
    thread_id: str | None = None
    snippet: str | None = None


@dataclass
class LabelInfo:
    """Gmail label information."""

    id: str
    name: str
    type: str
    messages_total: int | None = None
    messages_unread: int | None = None


@dataclass
class PredictionResult:
    """ML prediction result."""

    predicted_label: str
    confidence: float
    alternatives: list[tuple[str, float]]
    features_used: list[str]


@dataclass
class TrainingMetrics:
    """Training performance metrics."""

    accuracy: float
    precision: dict[str, float]
    recall: dict[str, float]
    f1_score: dict[str, float]
    confusion_matrix: list[list[int]]


# Abstract Interfaces for External Dependencies
class GmailApiInterface(ABC):
    """Abstract interface for Gmail API operations."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        pass

    @abstractmethod
    def get_labels(self) -> list[LabelInfo]:
        """Get all Gmail labels."""
        pass

    @abstractmethod
    def create_label(self, name: str) -> str:
        """Create a new label and return its ID."""
        pass

    @abstractmethod
    def list_messages(self, query: str | None = None, max_results: int = 100) -> list[str]:
        """List message IDs matching query."""
        pass

    @abstractmethod
    def get_message(self, message_id: str) -> EmailMessage:
        """Get full message data."""
        pass

    @abstractmethod
    def modify_message_labels(
        self, message_id: str, add_labels: list[str], remove_labels: list[str]
    ) -> bool:
        """Modify message labels."""
        pass

    @abstractmethod
    def trash_message(self, message_id: str) -> bool:
        """Move message to trash."""
        pass

    @abstractmethod
    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limit status."""
        pass


class DatabaseInterface(ABC):
    """Abstract interface for database operations."""

    @abstractmethod
    def initialize(self, connection_string: str) -> bool:
        """Initialize database connection."""
        pass

    @abstractmethod
    def store_messages(self, messages: list[EmailMessage]) -> int:
        """Store messages and return count of successfully stored."""
        pass

    @abstractmethod
    def get_message(self, message_id: str) -> EmailMessage | None:
        """Get a single message by ID."""
        pass

    @abstractmethod
    def get_messages_for_training(self, limit: int | None = None) -> list[EmailMessage]:
        """Get messages with user-reviewed labels for training."""
        pass

    @abstractmethod
    def get_messages_for_prediction(self, limit: int | None = None) -> list[EmailMessage]:
        """Get unreviewed messages for prediction."""
        pass

    @abstractmethod
    def mark_message_reviewed(self, message_id: str, label: str) -> bool:
        """Mark message as reviewed with given label."""
        pass

    @abstractmethod
    def save_prediction(self, message_id: str, prediction: PredictionResult) -> bool:
        """Save prediction result for message."""
        pass

    @abstractmethod
    def get_training_stats(self) -> dict[str, Any]:
        """Get training data statistics."""
        pass


class FileSystemInterface(ABC):
    """Abstract interface for file system operations."""

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read text file content."""
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> bool:
        """Write content to text file."""
        pass

    @abstractmethod
    def read_binary_file(self, path: str) -> bytes:
        """Read binary file content."""
        pass

    @abstractmethod
    def write_binary_file(self, path: str, content: bytes) -> bool:
        """Write binary content to file."""
        pass

    @abstractmethod
    def create_directory(self, path: str) -> bool:
        """Create directory if it doesn't exist."""
        pass

    @abstractmethod
    def list_files(self, directory: str, pattern: str | None = None) -> list[str]:
        """List files in directory matching pattern."""
        pass

    @abstractmethod
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        pass

    @abstractmethod
    def get_file_modified_time(self, path: str) -> datetime:
        """Get file last modified time."""
        pass


class ModelInterface(ABC):
    """Abstract interface for ML model operations."""

    @abstractmethod
    def load_model(self, model_path: str) -> bool:
        """Load trained model from path."""
        pass

    @abstractmethod
    def save_model(self, model_path: str) -> bool:
        """Save current model to path."""
        pass

    @abstractmethod
    def train(
        self, training_data: list[tuple[str, str]], epochs: int = 6, batch_size: int = 64
    ) -> TrainingMetrics:
        """Train model on labeled data."""
        pass

    @abstractmethod
    def predict(self, text: str) -> PredictionResult:
        """Predict label for given text."""
        pass

    @abstractmethod
    def predict_batch(self, texts: list[str]) -> list[PredictionResult]:
        """Predict labels for multiple texts."""
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get model metadata and performance info."""
        pass

    @abstractmethod
    def is_trained(self) -> bool:
        """Check if model is trained and ready."""
        pass


class TextProcessorInterface(ABC):
    """Abstract interface for text processing operations."""

    @abstractmethod
    def extract_features(self, text: str) -> dict[str, Any]:
        """Extract features from text."""
        pass

    @abstractmethod
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        pass

    @abstractmethod
    def extract_email_body(self, raw_content: str) -> str:
        """Extract body text from raw email content."""
        pass

    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect text language."""
        pass


class ConfigurationInterface(ABC):
    """Abstract interface for configuration management."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        pass

    @abstractmethod
    def reload(self) -> None:
        """Reload configuration from source."""
        pass

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate configuration and return errors."""
        pass


class LoggerInterface(ABC):
    """Abstract interface for logging operations."""

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        pass

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        pass

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        pass

    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        pass


# Dependency Container for Dependency Injection
class DependencyContainer:
    """Container for managing dependencies and enabling dependency injection."""

    def __init__(self):
        self._dependencies: dict[str, Any] = {}
        self._singletons: dict[str, Any] = {}

    def register(self, interface_name: str, implementation: Any, singleton: bool = True) -> None:
        """Register an implementation for an interface."""
        if singleton:
            self._singletons[interface_name] = implementation
        else:
            self._dependencies[interface_name] = implementation

    def get(self, interface_name: str) -> Any:
        """Get implementation for interface."""
        if interface_name in self._singletons:
            return self._singletons[interface_name]
        elif interface_name in self._dependencies:
            return self._dependencies[interface_name]
        else:
            raise ValueError(f"No implementation registered for {interface_name}")

    def has(self, interface_name: str) -> bool:
        """Check if interface is registered."""
        return interface_name in self._dependencies or interface_name in self._singletons


# Global dependency container
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    return _container


def register_dependency(interface_name: str, implementation: Any, singleton: bool = True) -> None:
    """Register a dependency implementation."""
    _container.register(interface_name, implementation, singleton)


def get_dependency(interface_name: str) -> Any:
    """Get a dependency implementation."""
    return _container.get(interface_name)


# Decorator for dependency injection
def inject_dependencies(**dependencies):
    """Decorator to inject dependencies into function/method."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Inject dependencies that aren't already provided
            for dep_name, interface_name in dependencies.items():
                if dep_name not in kwargs:
                    kwargs[dep_name] = get_dependency(interface_name)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Interface name constants for type safety
class Interfaces:
    """Constants for interface names to avoid string literals."""

    GMAIL_API = "gmail_api"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    MODEL = "model"
    TEXT_PROCESSOR = "text_processor"
    CONFIGURATION = "configuration"
    LOGGER = "logger"


# Configuration function for setting up default implementations
def configure_dependencies_for_production():
    """Configure dependencies for production use."""
    from adapters import (
        ConfigurationAdapter,
        DatabaseAdapter,
        FileSystemAdapter,
        GmailApiAdapter,
        LoggerAdapter,
        ModelAdapter,
        TextProcessorAdapter,
    )

    register_dependency(Interfaces.GMAIL_API, GmailApiAdapter())
    register_dependency(Interfaces.DATABASE, DatabaseAdapter())
    register_dependency(Interfaces.FILE_SYSTEM, FileSystemAdapter())
    register_dependency(Interfaces.MODEL, ModelAdapter())
    register_dependency(Interfaces.TEXT_PROCESSOR, TextProcessorAdapter())
    register_dependency(Interfaces.CONFIGURATION, ConfigurationAdapter())
    register_dependency(Interfaces.LOGGER, LoggerAdapter())


def configure_dependencies_for_testing():
    """Configure dependencies for testing with mocks."""
    from test_mocks import (
        MockConfiguration,
        MockDatabase,
        MockFileSystem,
        MockGmailApi,
        MockLogger,
        MockModel,
        MockTextProcessor,
    )

    register_dependency(Interfaces.GMAIL_API, MockGmailApi())
    register_dependency(Interfaces.DATABASE, MockDatabase())
    register_dependency(Interfaces.FILE_SYSTEM, MockFileSystem())
    register_dependency(Interfaces.MODEL, MockModel())
    register_dependency(Interfaces.TEXT_PROCESSOR, MockTextProcessor())
    register_dependency(Interfaces.CONFIGURATION, MockConfiguration())
    register_dependency(Interfaces.LOGGER, MockLogger())
