"""
Validation layer for data integrity and business rules.
Provides comprehensive validation for emails, predictions, and user inputs.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .logger import logger


class ValidationSeverity(Enum):
    """Severity levels for validation errors."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add an info message."""
        self.info.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result."""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)

    def get_all_messages(self) -> dict[str, list[str]]:
        """Get all messages grouped by severity."""
        return {"errors": self.errors, "warnings": self.warnings, "info": self.info}


class Validator(ABC):
    """Abstract base class for validators."""

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """Validate the given data."""
        pass


class EmailValidator(Validator):
    """Validates email data structure and content."""

    def __init__(self):
        self.email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        self.required_fields = {"id", "subject", "sender", "body"}
        self.max_subject_length = 998  # RFC 2822 limit
        self.max_body_length = 10 * 1024 * 1024  # 10MB limit

    def validate(self, email_data: dict[str, Any]) -> ValidationResult:
        """Validate email data."""
        result = ValidationResult(is_valid=True)

        # Check required fields
        missing_fields = self.required_fields - set(email_data.keys())
        if missing_fields:
            result.add_error(f"Missing required fields: {missing_fields}")

        # Validate email ID
        if "id" in email_data:
            if not email_data["id"] or not isinstance(email_data["id"], str):
                result.add_error("Email ID must be a non-empty string")

        # Validate subject
        if "subject" in email_data:
            subject = email_data["subject"]
            if subject and len(subject) > self.max_subject_length:
                result.add_error(f"Subject too long: {len(subject)} > {self.max_subject_length}")
            if not subject:
                result.add_warning("Subject is empty")

        # Validate sender
        if "sender" in email_data:
            sender = email_data["sender"]
            if sender:
                if not self._validate_email_address(sender):
                    result.add_error(f"Invalid sender email format: {sender}")
            else:
                result.add_error("Sender cannot be empty")

        # Validate body
        if "body" in email_data:
            body = email_data["body"]
            if body and len(body) > self.max_body_length:
                result.add_error(f"Body too long: {len(body)} > {self.max_body_length}")
            if not body:
                result.add_warning("Email body is empty")

        # Validate timestamp
        if "timestamp" in email_data:
            timestamp = email_data["timestamp"]
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    elif not isinstance(timestamp, datetime):
                        result.add_error("Timestamp must be a datetime object or ISO string")
                except ValueError:
                    result.add_error(f"Invalid timestamp format: {timestamp}")

        # Validate labels
        if "labels" in email_data:
            labels = email_data["labels"]
            if labels and not isinstance(labels, (list, set)):
                result.add_error("Labels must be a list or set")
            elif labels:
                for label in labels:
                    if not isinstance(label, str):
                        result.add_error(f"Label must be string, got {type(label)}")

        return result

    def _validate_email_address(self, email_addr: str) -> bool:
        """Validate email address format."""
        if not email_addr:
            return False

        # Extract email from "Name <email@domain.com>" format
        if "<" in email_addr and ">" in email_addr:
            email_addr = email_addr.split("<")[1].split(">")[0]

        return bool(self.email_pattern.match(email_addr))


class PredictionValidator(Validator):
    """Validates ML prediction results."""

    def __init__(self, valid_labels: set[str] | None = None):
        self.valid_labels = valid_labels or set()
        self.confidence_range = (0.0, 1.0)

    def validate(self, prediction_data: dict[str, Any]) -> ValidationResult:
        """Validate prediction data."""
        result = ValidationResult(is_valid=True)

        # Check required fields
        required_fields = {"predicted_label", "confidence", "email_id"}
        missing_fields = required_fields - set(prediction_data.keys())
        if missing_fields:
            result.add_error(f"Missing required prediction fields: {missing_fields}")
            return result

        # Validate predicted label
        predicted_label = prediction_data["predicted_label"]
        if not isinstance(predicted_label, str):
            result.add_error(f"Predicted label must be string, got {type(predicted_label)}")
        elif self.valid_labels and predicted_label not in self.valid_labels:
            result.add_error(f"Invalid predicted label: {predicted_label}")

        # Validate confidence
        confidence = prediction_data["confidence"]
        if not isinstance(confidence, (int, float)):
            result.add_error(f"Confidence must be numeric, got {type(confidence)}")
        elif not (self.confidence_range[0] <= confidence <= self.confidence_range[1]):
            result.add_error(f"Confidence {confidence} outside valid range {self.confidence_range}")
        elif confidence < 0.1:
            result.add_warning(f"Very low confidence: {confidence}")

        # Validate email ID
        email_id = prediction_data["email_id"]
        if not isinstance(email_id, str) or not email_id:
            result.add_error("Email ID must be a non-empty string")

        # Validate alternative predictions if present
        if "alternatives" in prediction_data:
            alternatives = prediction_data["alternatives"]
            if not isinstance(alternatives, list):
                result.add_error("Alternatives must be a list")
            else:
                for i, alt in enumerate(alternatives):
                    if not isinstance(alt, dict):
                        result.add_error(f"Alternative {i} must be a dictionary")
                        continue

                    if "label" not in alt or "confidence" not in alt:
                        result.add_error(f"Alternative {i} missing label or confidence")
                        continue

                    alt_confidence = alt["confidence"]
                    if not isinstance(alt_confidence, (int, float)):
                        result.add_error(f"Alternative {i} confidence must be numeric")
                    elif not (
                        self.confidence_range[0] <= alt_confidence <= self.confidence_range[1]
                    ):
                        result.add_error(f"Alternative {i} confidence outside valid range")

        return result


class LabelValidator(Validator):
    """Validates label operations and configurations."""

    def __init__(self, system_labels: set[str] | None = None):
        self.system_labels = system_labels or {
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
        self.label_name_pattern = re.compile(r"^[a-zA-Z0-9_\-\s]+$")
        self.max_label_length = 100

    def validate(self, label_data: str | dict[str, Any]) -> ValidationResult:
        """Validate label data."""
        result = ValidationResult(is_valid=True)

        if isinstance(label_data, str):
            # Single label name validation
            result.merge(self._validate_label_name(label_data))
        elif isinstance(label_data, dict):
            # Label creation/update data
            if "name" in label_data:
                result.merge(self._validate_label_name(label_data["name"]))
            else:
                result.add_error("Label data must include 'name' field")

            # Validate label visibility
            if "messageListVisibility" in label_data:
                visibility = label_data["messageListVisibility"]
                valid_visibility = ["show", "hide"]
                if visibility not in valid_visibility:
                    result.add_error(f"Invalid messageListVisibility: {visibility}")

            # Validate label list visibility
            if "labelListVisibility" in label_data:
                list_visibility = label_data["labelListVisibility"]
                valid_list_visibility = ["labelShow", "labelHide", "labelShowIfUnread"]
                if list_visibility not in valid_list_visibility:
                    result.add_error(f"Invalid labelListVisibility: {list_visibility}")
        else:
            result.add_error(f"Label data must be string or dict, got {type(label_data)}")

        return result

    def _validate_label_name(self, label_name: str) -> ValidationResult:
        """Validate individual label name."""
        result = ValidationResult(is_valid=True)

        if not label_name:
            result.add_error("Label name cannot be empty")
            return result

        if len(label_name) > self.max_label_length:
            result.add_error(f"Label name too long: {len(label_name)} > {self.max_label_length}")

        if not self.label_name_pattern.match(label_name):
            result.add_error(f"Invalid label name format: {label_name}")

        if label_name in self.system_labels:
            result.add_warning(f"Label name conflicts with system label: {label_name}")

        return result


class TrainingDataValidator(Validator):
    """Validates training data for ML models."""

    def __init__(self, min_samples_per_label: int = 5):
        self.min_samples_per_label = min_samples_per_label
        self.email_validator = EmailValidator()

    def validate(self, training_data: list[dict[str, Any]]) -> ValidationResult:
        """Validate training dataset."""
        result = ValidationResult(is_valid=True)

        if not training_data:
            result.add_error("Training data cannot be empty")
            return result

        if not isinstance(training_data, list):
            result.add_error("Training data must be a list")
            return result

        # Validate individual samples
        label_counts = {}
        for i, sample in enumerate(training_data):
            if not isinstance(sample, dict):
                result.add_error(f"Training sample {i} must be a dictionary")
                continue

            # Validate email data
            email_result = self.email_validator.validate(sample)
            if not email_result.is_valid:
                result.add_error(f"Sample {i} email validation failed: {email_result.errors}")

            # Check for labels
            if "labels" not in sample:
                result.add_error(f"Training sample {i} missing labels")
                continue

            labels = sample["labels"]
            if not labels:
                result.add_warning(f"Training sample {i} has no labels")
            else:
                for label in labels:
                    label_counts[label] = label_counts.get(label, 0) + 1

        # Check label distribution
        insufficient_labels = [
            label for label, count in label_counts.items() if count < self.min_samples_per_label
        ]

        if insufficient_labels:
            result.add_warning(
                f"Labels with insufficient samples ({self.min_samples_per_label}): {insufficient_labels}"
            )

        # Check for class imbalance
        if label_counts:
            max_count = max(label_counts.values())
            min_count = min(label_counts.values())
            imbalance_ratio = max_count / min_count if min_count > 0 else float("inf")

            if imbalance_ratio > 10:
                result.add_warning(f"High class imbalance detected: {imbalance_ratio:.2f}")

        result.add_info(
            f"Training data contains {len(training_data)} samples across {len(label_counts)} labels"
        )

        return result


class ValidationChain:
    """Chains multiple validators together."""

    def __init__(self):
        self.validators: list[tuple[str, Validator]] = []

    def add_validator(self, name: str, validator: Validator) -> "ValidationChain":
        """Add a validator to the chain."""
        self.validators.append((name, validator))
        return self

    def validate(self, data: Any) -> dict[str, ValidationResult]:
        """Run all validators in the chain."""
        results = {}

        for name, validator in self.validators:
            try:
                result = validator.validate(data)
                results[name] = result
                logger.debug(f"Validator {name}: {'PASS' if result.is_valid else 'FAIL'}")
            except Exception as e:
                error_result = ValidationResult(is_valid=False)
                error_result.add_error(f"Validator {name} failed: {str(e)}")
                results[name] = error_result
                logger.error(f"Validator {name} threw exception: {e}")

        return results

    def validate_all(self, data: Any) -> ValidationResult:
        """Run all validators and combine results."""
        combined_result = ValidationResult(is_valid=True)
        individual_results = self.validate(data)

        for name, result in individual_results.items():
            combined_result.merge(result)

        return combined_result


class ValidationRuleBuilder:
    """Builder for creating custom validation rules."""

    def __init__(self):
        self.rules: list[Callable[[Any], ValidationResult]] = []

    def add_rule(self, rule_func: Callable[[Any], ValidationResult]) -> "ValidationRuleBuilder":
        """Add a validation rule function."""
        self.rules.append(rule_func)
        return self

    def required_field(self, field_name: str, field_type: type = None) -> "ValidationRuleBuilder":
        """Add a required field rule."""

        def rule(data):
            result = ValidationResult(is_valid=True)
            if not isinstance(data, dict):
                result.add_error(f"Data must be dict to check required field {field_name}")
                return result

            if field_name not in data:
                result.add_error(f"Required field missing: {field_name}")
            elif field_type and not isinstance(data[field_name], field_type):
                result.add_error(f"Field {field_name} must be {field_type.__name__}")

            return result

        return self.add_rule(rule)

    def range_check(
        self, field_name: str, min_val: float, max_val: float
    ) -> "ValidationRuleBuilder":
        """Add a range validation rule."""

        def rule(data):
            result = ValidationResult(is_valid=True)
            if isinstance(data, dict) and field_name in data:
                value = data[field_name]
                if isinstance(value, (int, float)):
                    if not (min_val <= value <= max_val):
                        result.add_error(
                            f"Field {field_name} value {value} outside range [{min_val}, {max_val}]"
                        )
            return result

        return self.add_rule(rule)

    def build(self) -> Validator:
        """Build a validator from the rules."""

        class CustomValidator(Validator):
            def __init__(self, rules):
                self.rules = rules

            def validate(self, data):
                combined_result = ValidationResult(is_valid=True)
                for rule in self.rules:
                    result = rule(data)
                    combined_result.merge(result)
                return combined_result

        return CustomValidator(self.rules)


# Pre-configured validator instances
email_validator = EmailValidator()
prediction_validator = PredictionValidator()
label_validator = LabelValidator()
training_data_validator = TrainingDataValidator()


def validate_email(email_data: dict[str, Any]) -> ValidationResult:
    """Validate email data (convenience function)."""
    return email_validator.validate(email_data)


def validate_prediction(
    prediction_data: dict[str, Any], valid_labels: set[str] | None = None
) -> ValidationResult:
    """Validate prediction data (convenience function)."""
    if valid_labels:
        validator = PredictionValidator(valid_labels)
        return validator.validate(prediction_data)
    return prediction_validator.validate(prediction_data)


def validate_label(label_data: str | dict[str, Any]) -> ValidationResult:
    """Validate label data (convenience function)."""
    return label_validator.validate(label_data)


def validate_training_data(training_data: list[dict[str, Any]]) -> ValidationResult:
    """Validate training data (convenience function)."""
    return training_data_validator.validate(training_data)


def create_email_validation_chain() -> ValidationChain:
    """Create a validation chain for email processing."""
    return (
        ValidationChain()
        .add_validator("email_structure", EmailValidator())
        .add_validator("label_format", LabelValidator())
    )


def create_prediction_validation_chain(valid_labels: set[str] | None = None) -> ValidationChain:
    """Create a validation chain for prediction results."""
    return ValidationChain().add_validator("prediction_format", PredictionValidator(valid_labels))


def create_training_validation_chain() -> ValidationChain:
    """Create a validation chain for training data."""
    return (
        ValidationChain()
        .add_validator("training_data", TrainingDataValidator())
        .add_validator("email_structure", EmailValidator())
    )
