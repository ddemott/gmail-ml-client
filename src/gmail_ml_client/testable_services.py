"""
Testable service implementations using dependency injection.
These services demonstrate proper separation of concerns for maximum testability.
"""

from dataclasses import dataclass
from typing import Any

from .interfaces import (
    ConfigurationInterface,
    DatabaseInterface,
    FileSystemInterface,
    GmailApiInterface,
    Interfaces,
    LoggerInterface,
    ModelInterface,
    TextProcessorInterface,
    inject_dependencies,
)


@dataclass
class ServiceResult:
    """Standard result object for all service operations."""

    success: bool
    data: Any = None
    message: str = ""
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    @classmethod
    def success_result(cls, data: Any = None, message: str = "") -> "ServiceResult":
        """Create a successful result."""
        return cls(success=True, data=data, message=message)

    @classmethod
    def error_result(cls, message: str, errors: list[str] | None = None) -> "ServiceResult":
        """Create an error result."""
        return cls(success=False, message=message, errors=errors or [message])


class GmailService:
    """Gmail service with dependency injection for testing."""

    def __init__(
        self,
        gmail_api: GmailApiInterface,
        database: DatabaseInterface,
        config: ConfigurationInterface,
        logger: LoggerInterface,
    ):
        self.gmail_api = gmail_api
        self.database = database
        self.config = config
        self.logger = logger

    @inject_dependencies(
        gmail_api=Interfaces.GMAIL_API,
        database=Interfaces.DATABASE,
        config=Interfaces.CONFIGURATION,
        logger=Interfaces.LOGGER,
    )
    def initialize(
        self,
        gmail_api: GmailApiInterface | None = None,
        database: DatabaseInterface | None = None,
        config: ConfigurationInterface | None = None,
        logger: LoggerInterface | None = None,
    ) -> ServiceResult:
        """Initialize Gmail service."""
        try:
            logger.info("Initializing Gmail service")

            # Authenticate with Gmail
            if not gmail_api.authenticate():
                return ServiceResult.error_result("Gmail authentication failed")

            # Initialize database
            db_path = config.get("database.path", "state.db")
            if not database.initialize(db_path):
                return ServiceResult.error_result("Database initialization failed")

            logger.info("Gmail service initialized successfully")
            return ServiceResult.success_result(message="Gmail service initialized")

        except Exception as e:
            logger.error(f"Gmail service initialization failed: {e}")
            return ServiceResult.error_result(f"Initialization failed: {str(e)}")

    def sync_emails(self, query: str | None = None, limit: int = 100) -> ServiceResult:
        """Sync emails from Gmail to database."""
        try:
            self.logger.info(f"Starting email sync with limit {limit}")

            # Get message IDs from Gmail
            message_ids = self.gmail_api.list_messages(query=query, max_results=limit)

            if not message_ids:
                return ServiceResult.success_result(data=[], message="No new messages to sync")

            # Fetch full message data
            messages = []
            failed_count = 0

            for msg_id in message_ids:
                try:
                    message = self.gmail_api.get_message(msg_id)
                    messages.append(message)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch message {msg_id}: {e}")
                    failed_count += 1

            # Store messages in database
            stored_count = self.database.store_messages(messages)

            result_data = {
                "total_fetched": len(message_ids),
                "successfully_stored": stored_count,
                "failed_fetches": failed_count,
                "messages": messages,
            }

            self.logger.info(f"Sync complete: {stored_count} stored, {failed_count} failed")
            return ServiceResult.success_result(
                data=result_data, message=f"Synced {stored_count} messages"
            )

        except Exception as e:
            self.logger.error(f"Email sync failed: {e}")
            return ServiceResult.error_result(f"Sync failed: {str(e)}")

    def create_labels(self, label_names: list[str]) -> ServiceResult:
        """Create Gmail labels."""
        try:
            created_labels = {}
            failed_labels = []

            for name in label_names:
                try:
                    label_id = self.gmail_api.create_label(name)
                    if label_id:
                        created_labels[name] = label_id
                        self.logger.info(f"Created label {name} with ID {label_id}")
                    else:
                        failed_labels.append(name)
                except Exception as e:
                    self.logger.error(f"Failed to create label {name}: {e}")
                    failed_labels.append(name)

            if failed_labels:
                return ServiceResult.error_result(
                    f"Failed to create labels: {failed_labels}",
                    [f"Label creation failed for: {', '.join(failed_labels)}"],
                )

            return ServiceResult.success_result(
                data=created_labels, message=f"Created {len(created_labels)} labels"
            )

        except Exception as e:
            self.logger.error(f"Label creation failed: {e}")
            return ServiceResult.error_result(f"Label creation failed: {str(e)}")


class PredictionService:
    """Prediction service with dependency injection for testing."""

    def __init__(
        self,
        database: DatabaseInterface,
        model: ModelInterface,
        text_processor: TextProcessorInterface,
        config: ConfigurationInterface,
        logger: LoggerInterface,
    ):
        self.database = database
        self.model = model
        self.text_processor = text_processor
        self.config = config
        self.logger = logger

    @inject_dependencies(
        database=Interfaces.DATABASE,
        model=Interfaces.MODEL,
        text_processor=Interfaces.TEXT_PROCESSOR,
        config=Interfaces.CONFIGURATION,
        logger=Interfaces.LOGGER,
    )
    def predict_messages(
        self,
        limit: int = 50,
        database: DatabaseInterface | None = None,
        model: ModelInterface | None = None,
        text_processor: TextProcessorInterface | None = None,
        config: ConfigurationInterface | None = None,
        logger: LoggerInterface | None = None,
    ) -> ServiceResult:
        """Generate predictions for unreviewed messages."""
        try:
            logger.info(f"Starting prediction for up to {limit} messages")

            # Check if model is trained
            if not model.is_trained():
                return ServiceResult.error_result("Model is not trained yet")

            # Get unreviewed messages
            messages = database.get_messages_for_prediction(limit)

            if not messages:
                return ServiceResult.success_result(data=[], message="No unreviewed messages found")

            # Generate predictions
            predictions = []
            failed_count = 0

            spam_threshold = config.get("thresholds.spam", 0.85)
            certain_threshold = config.get("thresholds.certain", 0.92)

            for message in messages:
                try:
                    # Process text
                    full_text = f"{message.subject} {message.body}"
                    cleaned_text = text_processor.clean_text(full_text)

                    # Get prediction
                    prediction = model.predict(cleaned_text)

                    # Determine action based on thresholds
                    action = "review"  # default
                    if (
                        prediction.predicted_label == "SPAM"
                        and prediction.confidence >= spam_threshold
                    ):
                        action = "trash"
                    elif prediction.confidence >= certain_threshold:
                        action = "route"

                    prediction_data = {
                        "message_id": message.id,
                        "subject": message.subject,
                        "sender": message.sender,
                        "predicted_label": prediction.predicted_label,
                        "confidence": prediction.confidence,
                        "action": action,
                        "alternatives": prediction.alternatives,
                        "spam_score": (
                            prediction.confidence if prediction.predicted_label == "SPAM" else 0.0
                        ),
                    }

                    predictions.append(prediction_data)

                    # Save prediction to database
                    database.save_prediction(message.id, prediction)

                except Exception as e:
                    logger.warning(f"Failed to predict message {message.id}: {e}")
                    failed_count += 1

            result_data = {
                "predictions": predictions,
                "total_processed": len(messages),
                "successful_predictions": len(predictions),
                "failed_predictions": failed_count,
            }

            logger.info(
                f"Prediction complete: {len(predictions)} predictions, {failed_count} failed"
            )
            return ServiceResult.success_result(
                data=result_data, message=f"Generated {len(predictions)} predictions"
            )

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return ServiceResult.error_result(f"Prediction failed: {str(e)}")


class TrainingService:
    """Training service with dependency injection for testing."""

    def __init__(
        self,
        database: DatabaseInterface,
        model: ModelInterface,
        text_processor: TextProcessorInterface,
        file_system: FileSystemInterface,
        config: ConfigurationInterface,
        logger: LoggerInterface,
    ):
        self.database = database
        self.model = model
        self.text_processor = text_processor
        self.file_system = file_system
        self.config = config
        self.logger = logger

    @inject_dependencies(
        database=Interfaces.DATABASE,
        model=Interfaces.MODEL,
        text_processor=Interfaces.TEXT_PROCESSOR,
        file_system=Interfaces.FILE_SYSTEM,
        config=Interfaces.CONFIGURATION,
        logger=Interfaces.LOGGER,
    )
    def train_model(
        self,
        epochs: int = 6,
        batch_size: int = 64,
        database: DatabaseInterface | None = None,
        model: ModelInterface | None = None,
        text_processor: TextProcessorInterface | None = None,
        file_system: FileSystemInterface | None = None,
        config: ConfigurationInterface | None = None,
        logger: LoggerInterface | None = None,
    ) -> ServiceResult:
        """Train the ML model."""
        try:
            logger.info(f"Starting model training with {epochs} epochs, batch size {batch_size}")

            # Get training data
            training_messages = database.get_messages_for_training()

            if not training_messages:
                return ServiceResult.error_result("No training data available")

            # Check minimum samples per label
            label_counts = {}
            for message in training_messages:
                for label in message.labels:
                    label_counts[label] = label_counts.get(label, 0) + 1

            min_samples = config.get("training.min_samples_per_label", 5)
            insufficient_labels = [
                label for label, count in label_counts.items() if count < min_samples
            ]

            if insufficient_labels:
                return ServiceResult.error_result(
                    f"Insufficient training data for labels: {insufficient_labels}. "
                    f"Need at least {min_samples} samples per label."
                )

            # Prepare training data
            training_pairs = []
            for message in training_messages:
                full_text = f"{message.subject} {message.body}"
                cleaned_text = text_processor.clean_text(full_text)

                # Use the first label as the primary label for training
                primary_label = message.labels[0] if message.labels else "Unknown"
                training_pairs.append((cleaned_text, primary_label))

            # Train the model
            metrics = model.train(training_pairs, epochs=epochs, batch_size=batch_size)

            # Save the model
            model_path = config.get("model.artifacts_dir", "model_artifacts")
            file_system.create_directory(model_path)

            full_model_path = f"{model_path}/trained_model.pkl"
            if not model.save_model(full_model_path):
                logger.warning("Failed to save trained model")

            result_data = {
                "training_samples": len(training_pairs),
                "label_counts": label_counts,
                "metrics": {
                    "accuracy": metrics.accuracy,
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "f1_score": metrics.f1_score,
                },
                "model_path": full_model_path,
            }

            logger.info(f"Training complete. Accuracy: {metrics.accuracy:.3f}")
            return ServiceResult.success_result(
                data=result_data, message=f"Model trained with {len(training_pairs)} samples"
            )

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return ServiceResult.error_result(f"Training failed: {str(e)}")


class ActionService:
    """Action service with dependency injection for testing."""

    def __init__(
        self,
        gmail_api: GmailApiInterface,
        database: DatabaseInterface,
        config: ConfigurationInterface,
        logger: LoggerInterface,
    ):
        self.gmail_api = gmail_api
        self.database = database
        self.config = config
        self.logger = logger

    @inject_dependencies(
        gmail_api=Interfaces.GMAIL_API,
        database=Interfaces.DATABASE,
        config=Interfaces.CONFIGURATION,
        logger=Interfaces.LOGGER,
    )
    def apply_actions(
        self,
        dry_run: bool = True,
        limit: int = 100,
        gmail_api: GmailApiInterface | None = None,
        database: DatabaseInterface | None = None,
        config: ConfigurationInterface | None = None,
        logger: LoggerInterface | None = None,
    ) -> ServiceResult:
        """Apply predicted actions to Gmail messages."""
        try:
            logger.info(f"Applying actions (dry_run={dry_run}, limit={limit})")

            # Get messages for prediction to find actions
            messages = database.get_messages_for_prediction(limit)

            if not messages:
                return ServiceResult.success_result(
                    data={"applied_count": 0, "actions": []},
                    message="No messages requiring actions",
                )

            applied_actions = []
            applied_count = 0
            failed_count = 0

            spam_threshold = config.get("thresholds.spam", 0.85)
            certain_threshold = config.get("thresholds.certain", 0.92)

            for message in messages:
                try:
                    # This would normally get the saved prediction from database
                    # For this example, we'll simulate a simple prediction
                    action_taken = None

                    # Simulate checking prediction confidence
                    # In real implementation, would get from database.get_prediction(message.id)
                    if (
                        "spam" in message.subject.lower()
                        or "prize" in message.subject.lower()
                        or "claim" in message.body.lower()
                    ):
                        confidence = 0.9
                        if confidence >= spam_threshold:
                            action_taken = "trash"
                            if not dry_run:
                                success = gmail_api.trash_message(message.id)
                                if success:
                                    applied_count += 1
                                else:
                                    failed_count += 1
                    elif (
                        any(label in ["Work", "Personal", "Finance"] for label in message.labels)
                        or "meeting" in message.subject.lower()
                        or "team" in message.body.lower()
                    ):
                        confidence = 0.95
                        if confidence >= certain_threshold:
                            target_label = (
                                "Work"
                                if "meeting" in message.subject.lower()
                                or "team" in message.body.lower()
                                else (message.labels[0] if message.labels else "Personal")
                            )
                            action_taken = f"route_to_{target_label}"
                            if not dry_run:
                                success = gmail_api.modify_message_labels(
                                    message.id, add_labels=[target_label], remove_labels=["INBOX"]
                                )
                                if success:
                                    applied_count += 1
                                else:
                                    failed_count += 1

                    if action_taken:
                        applied_actions.append(
                            {
                                "message_id": message.id,
                                "subject": message.subject,
                                "action": action_taken,
                                "dry_run": dry_run,
                            }
                        )

                except Exception as e:
                    logger.warning(f"Failed to apply action to message {message.id}: {e}")
                    failed_count += 1

            result_data = {
                "applied_count": applied_count if not dry_run else len(applied_actions),
                "failed_count": failed_count,
                "dry_run": dry_run,
                "actions": applied_actions,
            }

            action_word = "simulated" if dry_run else "applied"
            logger.info(
                f"Actions {action_word}: {len(applied_actions)} total, {failed_count} failed"
            )

            return ServiceResult.success_result(
                data=result_data,
                message=f"{action_word.capitalize()} {len(applied_actions)} actions",
            )

        except Exception as e:
            logger.error(f"Action application failed: {e}")
            return ServiceResult.error_result(f"Action application failed: {str(e)}")


# Factory functions for creating services with injected dependencies
def create_gmail_service() -> GmailService:
    """Create Gmail service with injected dependencies."""
    from .interfaces import Interfaces, get_dependency

    return GmailService(
        gmail_api=get_dependency(Interfaces.GMAIL_API),
        database=get_dependency(Interfaces.DATABASE),
        config=get_dependency(Interfaces.CONFIGURATION),
        logger=get_dependency(Interfaces.LOGGER),
    )


def create_prediction_service() -> PredictionService:
    """Create prediction service with injected dependencies."""
    from .interfaces import Interfaces, get_dependency

    return PredictionService(
        database=get_dependency(Interfaces.DATABASE),
        model=get_dependency(Interfaces.MODEL),
        text_processor=get_dependency(Interfaces.TEXT_PROCESSOR),
        config=get_dependency(Interfaces.CONFIGURATION),
        logger=get_dependency(Interfaces.LOGGER),
    )


def create_training_service() -> TrainingService:
    """Create training service with injected dependencies."""
    from .interfaces import Interfaces, get_dependency

    return TrainingService(
        database=get_dependency(Interfaces.DATABASE),
        model=get_dependency(Interfaces.MODEL),
        text_processor=get_dependency(Interfaces.TEXT_PROCESSOR),
        file_system=get_dependency(Interfaces.FILE_SYSTEM),
        config=get_dependency(Interfaces.CONFIGURATION),
        logger=get_dependency(Interfaces.LOGGER),
    )


def create_action_service() -> ActionService:
    """Create action service with injected dependencies."""
    from .interfaces import Interfaces, get_dependency

    return ActionService(
        gmail_api=get_dependency(Interfaces.GMAIL_API),
        database=get_dependency(Interfaces.DATABASE),
        config=get_dependency(Interfaces.CONFIGURATION),
        logger=get_dependency(Interfaces.LOGGER),
    )
