"""
Enhanced configuration management layer with proper separation of concerns.
Separates configuration loading, validation, and environment-specific settings.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .logger import logger


class Environment(Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class ThresholdConfig:
    """Configuration for decision thresholds."""

    spam: float = 0.85
    certain: float = 0.92

    def validate(self) -> list[str]:
        """Validate threshold configuration."""
        errors = []
        if not (0.0 <= self.spam <= 1.0):
            errors.append("spam threshold must be between 0.0 and 1.0")
        if not (0.0 <= self.certain <= 1.0):
            errors.append("certain threshold must be between 0.0 and 1.0")
        if self.spam >= self.certain:
            errors.append("certain threshold should be higher than spam threshold")
        return errors


@dataclass
class DatabaseConfig:
    """Configuration for database settings."""

    path: str = "state.db"
    connection_pool_size: int = 10
    echo_sql: bool = False

    def validate(self) -> list[str]:
        """Validate database configuration."""
        errors = []
        if not self.path:
            errors.append("database path cannot be empty")
        if self.connection_pool_size <= 0:
            errors.append("connection pool size must be positive")
        return errors


@dataclass
class ModelConfig:
    """Configuration for ML model settings."""

    artifacts_dir: str = "model_artifacts"
    max_features: int = 50000
    ngram_range: tuple = (1, 2)
    min_df: int = 2
    epochs: int = 6
    batch_size: int = 64

    def validate(self) -> list[str]:
        """Validate model configuration."""
        errors = []
        if not self.artifacts_dir:
            errors.append("model artifacts directory cannot be empty")
        if self.max_features <= 0:
            errors.append("max features must be positive")
        if self.epochs <= 0:
            errors.append("epochs must be positive")
        if self.batch_size <= 0:
            errors.append("batch size must be positive")
        return errors


@dataclass
class GmailConfig:
    """Configuration for Gmail API settings."""

    credentials_file: str = "credentials.json"
    token_file: str = "token.json"
    sync_page_size: int = 200
    rate_limit_per_second: int = 250
    rate_limit_per_day: int = 1000000000

    def validate(self) -> list[str]:
        """Validate Gmail configuration."""
        errors = []
        if not self.credentials_file:
            errors.append("credentials file path cannot be empty")
        if not self.token_file:
            errors.append("token file path cannot be empty")
        if self.sync_page_size <= 0:
            errors.append("sync page size must be positive")
        return errors


@dataclass
class LoggingConfig:
    """Configuration for logging settings."""

    level: str = "INFO"
    file_path: str = "logs/gmail_ml_client.log"
    console_level: str = "INFO"
    file_level: str = "DEBUG"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

    def validate(self) -> list[str]:
        """Validate logging configuration."""
        errors = []
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            errors.append(f"log level must be one of {valid_levels}")
        if self.console_level.upper() not in valid_levels:
            errors.append(f"console log level must be one of {valid_levels}")
        if self.file_level.upper() not in valid_levels:
            errors.append(f"file log level must be one of {valid_levels}")
        return errors


@dataclass
class LabelConfig:
    """Configuration for label management."""

    system_labels: set = field(
        default_factory=lambda: {
            "INBOX",
            "UNREAD",
            "STARRED",
            "IMPORTANT",
            "TRASH",
            "DRAFT",
            "SENT",
            "CATEGORY_PERSONAL",
            "CATEGORY_SOCIAL",
            "CATEGORY_PROMOTIONS",
            "CATEGORY_UPDATES",
            "CATEGORY_FORUMS",
            "SPAM",
            "CATEGORY_SPAM",
        }
    )
    junk_labels: set = field(default_factory=lambda: {"Junk", "JUNK", "Bulk", "Promotions:Spammy"})
    default_target_labels: list[str] = field(
        default_factory=lambda: [
            "Work",
            "Personal",
            "Receipts",
            "Finance",
            "Newsletters",
            "Social",
            "Updates",
        ]
    )

    def validate(self) -> list[str]:
        """Validate label configuration."""
        errors = []
        conflicts = set(self.default_target_labels) & self.system_labels
        if conflicts:
            errors.append(f"default target labels conflict with system labels: {conflicts}")
        return errors


@dataclass
class RulesConfig:
    """Configuration for classification rules."""

    include_rules: dict[str, list[str]] = field(
        default_factory=lambda: {
            "Receipts": ["receipt", "invoice", "order", "transaction", "purchase", "payment"],
            "Finance": ["bank", "statement", "due", "bill", "credit card", "mortgage"],
            "Newsletters": ["unsubscribe", "newsletter", "weekly", "digest"],
            "Social": ["followed you", "like", "commented", "mentioned you"],
            "Work": ["standup", "sprint", "jira", "pull request", "deployment", "oncall"],
            "Updates": ["update", "policy", "terms", "what's new", "changelog"],
        }
    )
    exclude_rules: dict[str, list[str]] = field(
        default_factory=lambda: {
            "Receipts": ["privacy policy", "terms of service"],
        }
    )

    def validate(self, target_labels: list[str]) -> list[str]:
        """Validate rules configuration."""
        errors = []
        for label in self.include_rules:
            if label not in target_labels:
                errors.append(f"include rule references unknown label: {label}")
        for label in self.exclude_rules:
            if label not in target_labels:
                errors.append(f"exclude rule references unknown label: {label}")
        return errors


@dataclass
class AppConfig:
    """Main application configuration."""

    environment: Environment = Environment.DEVELOPMENT
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    gmail: GmailConfig = field(default_factory=GmailConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    labels: LabelConfig = field(default_factory=LabelConfig)
    rules: RulesConfig = field(default_factory=RulesConfig)

    def validate(self) -> list[str]:
        """Validate entire configuration."""
        errors = []
        errors.extend(self.thresholds.validate())
        errors.extend(self.database.validate())
        errors.extend(self.model.validate())
        errors.extend(self.gmail.validate())
        errors.extend(self.logging.validate())
        errors.extend(self.labels.validate())
        errors.extend(self.rules.validate(self.labels.default_target_labels))
        return errors


class ConfigLoader(ABC):
    """Abstract base class for configuration loaders."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Load configuration from source."""
        pass


class FileConfigLoader(ConfigLoader):
    """Loads configuration from JSON/YAML files."""

    def __init__(self, config_file: str):
        self.config_file = Path(config_file)

    def load(self) -> dict[str, Any]:
        """Load configuration from file."""
        if not self.config_file.exists():
            logger.info(f"Config file {self.config_file} not found, using defaults")
            return {}

        try:
            with open(self.config_file) as f:
                if self.config_file.suffix.lower() == ".json":
                    return json.load(f)
                else:
                    # Could add YAML support here
                    raise ValueError(f"Unsupported config file format: {self.config_file.suffix}")
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_file}: {e}")
            return {}


class EnvironmentConfigLoader(ConfigLoader):
    """Loads configuration from environment variables."""

    def __init__(self, prefix: str = "GMAIL_ML_"):
        self.prefix = prefix

    def load(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix) :].lower()

                # Convert string values to appropriate types
                if value.lower() in ("true", "false"):
                    config[config_key] = value.lower() == "true"
                elif value.isdigit():
                    config[config_key] = int(value)
                else:
                    try:
                        config[config_key] = float(value)
                    except ValueError:
                        config[config_key] = value

        return config


class ConfigurationManager:
    """Manages application configuration with multiple sources and validation."""

    def __init__(self):
        self._config: AppConfig | None = None
        self._loaders: list[ConfigLoader] = []

    def add_loader(self, loader: ConfigLoader) -> None:
        """Add a configuration loader."""
        self._loaders.append(loader)

    def load_config(self) -> AppConfig:
        """Load and merge configuration from all sources."""
        merged_config = {}

        # Load from all sources
        for loader in self._loaders:
            try:
                config_data = loader.load()
                merged_config.update(config_data)
            except Exception as e:
                logger.warning(f"Failed to load config from {loader.__class__.__name__}: {e}")

        # Create configuration object
        self._config = self._create_config_from_dict(merged_config)

        # Validate configuration
        errors = self._config.validate()
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"Configuration loaded successfully for {self._config.environment.value} environment"
        )
        return self._config

    def _create_config_from_dict(self, config_dict: dict[str, Any]) -> AppConfig:
        """Create AppConfig from dictionary with proper nesting."""
        # Extract environment
        env_str = config_dict.get("environment", "development")
        environment = Environment(env_str) if isinstance(env_str, str) else env_str

        # Create nested config objects
        thresholds = ThresholdConfig(
            spam=config_dict.get("spam_threshold", 0.85),
            certain=config_dict.get("certain_threshold", 0.92),
        )

        database = DatabaseConfig(
            path=config_dict.get("database_path", "state.db"),
            connection_pool_size=config_dict.get("db_pool_size", 10),
            echo_sql=config_dict.get("db_echo_sql", False),
        )

        model = ModelConfig(
            artifacts_dir=config_dict.get("model_dir", "model_artifacts"),
            max_features=config_dict.get("model_max_features", 50000),
            epochs=config_dict.get("model_epochs", 6),
            batch_size=config_dict.get("model_batch_size", 64),
        )

        gmail = GmailConfig(
            credentials_file=config_dict.get("gmail_credentials", "credentials.json"),
            token_file=config_dict.get("gmail_token", "token.json"),
            sync_page_size=config_dict.get("gmail_sync_size", 200),
        )

        logging_config = LoggingConfig(
            level=config_dict.get("log_level", "INFO"),
            file_path=config_dict.get("log_file", "logs/gmail_ml_client.log"),
            console_level=config_dict.get("console_log_level", "INFO"),
            file_level=config_dict.get("file_log_level", "DEBUG"),
        )

        labels = LabelConfig()  # Use defaults for now
        rules = RulesConfig()  # Use defaults for now

        return AppConfig(
            environment=environment,
            thresholds=thresholds,
            database=database,
            model=model,
            gmail=gmail,
            logging=logging_config,
            labels=labels,
            rules=rules,
        )

    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config

    def reload_config(self) -> AppConfig:
        """Reload configuration from all sources."""
        return self.load_config()


# Global configuration manager instance
config_manager = ConfigurationManager()

# Add default loaders
config_manager.add_loader(FileConfigLoader("config.json"))
config_manager.add_loader(EnvironmentConfigLoader())


def get_config() -> AppConfig:
    """Get the current application configuration."""
    return config_manager.get_config()


def load_config() -> AppConfig:
    """Load application configuration from all sources."""
    return config_manager.load_config()


def reload_config() -> AppConfig:
    """Reload application configuration."""
    return config_manager.reload_config()


# Backward compatibility functions (for existing code)
def get_thresholds() -> dict[str, float]:
    """Get decision thresholds (backward compatible)."""
    config = get_config()
    return {"spam": config.thresholds.spam, "certain": config.thresholds.certain}


def get_system_labels() -> set:
    """Get system labels (backward compatible)."""
    return get_config().labels.system_labels


def get_default_target_labels() -> list[str]:
    """Get default target labels (backward compatible)."""
    return get_config().labels.default_target_labels


def get_rules_include() -> dict[str, list[str]]:
    """Get include rules (backward compatible)."""
    return get_config().rules.include_rules


def get_rules_exclude() -> dict[str, list[str]]:
    """Get exclude rules (backward compatible)."""
    return get_config().rules.exclude_rules


def get_db_path() -> str:
    """Get database path (backward compatible)."""
    return get_config().database.path


def get_model_dir() -> str:
    """Get model directory (backward compatible)."""
    return get_config().model.artifacts_dir


def get_sync_page_size() -> int:
    """Get sync page size (backward compatible)."""
    return get_config().gmail.sync_page_size
