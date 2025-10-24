"""
Comprehensive test suite for Gmail ML Client using pytest and dependency injection.
Demonstrates proper unit testing with mocked dependencies.
"""

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest
from test_mocks import (
    MockConfiguration,
    MockDatabase,
    MockFileSystem,
    MockGmailApi,
    MockLogger,
    MockModel,
    MockTextProcessor,
)

# Import our testable components
from src.gmail_ml_client.interfaces import (
    EmailMessage,
    Interfaces,
    LabelInfo,
    PredictionResult,
    TrainingMetrics,
    configure_dependencies_for_testing,
    get_dependency,
)
from src.gmail_ml_client.testable_services import (
    ActionService,
    GmailService,
    PredictionService,
    ServiceResult,
    TrainingService,
)


@pytest.fixture
def setup_test_dependencies():
    """Setup test dependencies before each test."""
    configure_dependencies_for_testing()

    # Get mock instances for direct manipulation in tests
    gmail_api = get_dependency(Interfaces.GMAIL_API)
    database = get_dependency(Interfaces.DATABASE)
    file_system = get_dependency(Interfaces.FILE_SYSTEM)
    model = get_dependency(Interfaces.MODEL)
    text_processor = get_dependency(Interfaces.TEXT_PROCESSOR)
    config = get_dependency(Interfaces.CONFIGURATION)
    logger = get_dependency(Interfaces.LOGGER)

    # Clear any previous state
    gmail_api.clear_call_log()
    database.clear_call_log()
    file_system.clear_call_log()
    model.clear_call_log()
    text_processor.clear_call_log()
    config.clear_call_log()
    logger.clear_logs()

    return {
        "gmail_api": gmail_api,
        "database": database,
        "file_system": file_system,
        "model": model,
        "text_processor": text_processor,
        "config": config,
        "logger": logger,
    }


class TestGmailService:
    """Test cases for GmailService."""

    def test_initialize_success(self, setup_test_dependencies):
        """Test successful Gmail service initialization."""
        mocks = setup_test_dependencies
        service = GmailService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        result = service.initialize()

        assert result.success is True
        assert "Gmail service initialized" in result.message

        # Verify dependencies were called
        assert ("authenticate",) in mocks["gmail_api"].get_call_log()
        assert ("initialize", "test.db") in mocks["database"].get_call_log()

        # Verify logging
        logs = mocks["logger"].get_logs("INFO")
        assert any("Initializing Gmail service" in log[1] for log in logs)

    def test_initialize_gmail_auth_failure(self, setup_test_dependencies):
        """Test Gmail service initialization with authentication failure."""
        mocks = setup_test_dependencies
        mocks["gmail_api"].set_should_fail(True)

        service = GmailService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        result = service.initialize()

        assert result.success is False
        assert "Gmail authentication failed" in result.message

    def test_initialize_database_failure(self, setup_test_dependencies):
        """Test Gmail service initialization with database failure."""
        mocks = setup_test_dependencies
        mocks["database"].set_should_fail(True)

        service = GmailService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        result = service.initialize()

        assert result.success is False
        assert "Database initialization failed" in result.message

    def test_sync_emails_success(self, setup_test_dependencies):
        """Test successful email synchronization."""
        mocks = setup_test_dependencies

        # Clear any default messages and add test messages to mock Gmail API
        mocks["gmail_api"].clear_data()
        test_message = EmailMessage(
            id="test_msg_1",
            subject="Test Subject",
            sender="test@example.com",
            body="Test body content",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        mocks["gmail_api"].add_test_message(test_message)

        service = GmailService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        # Initialize the service first
        init_result = service.initialize()
        assert init_result.success is True

        # Ensure mocks are properly set
        mocks["gmail_api"].authenticated = True
        mocks["database"].initialized = True

        result = service.sync_emails(limit=10)

        assert result.success is True
        assert result.data["successfully_stored"] > 0
        assert "Synced" in result.message

        # Verify API calls
        call_log = mocks["gmail_api"].get_call_log()
        assert any("list_messages" in str(call) for call in call_log)
        assert any("get_message" in str(call) for call in call_log)

    def test_sync_emails_no_messages(self, setup_test_dependencies):
        """Test email sync when no messages are available."""
        mocks = setup_test_dependencies

        # Clear any default messages from mock Gmail API
        mocks["gmail_api"].clear_data()

        service = GmailService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        # Initialize the service first
        init_result = service.initialize()
        assert init_result.success is True

        # Ensure mocks are properly set
        mocks["gmail_api"].authenticated = True
        mocks["database"].initialized = True

        result = service.sync_emails(limit=10)

        assert result.success is True
        assert result.data == []
        assert "No new messages to sync" in result.message

    def test_create_labels_success(self, setup_test_dependencies):
        """Test successful label creation."""
        mocks = setup_test_dependencies

        service = GmailService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        # Ensure mocks are properly set
        mocks["gmail_api"].authenticated = True

        labels_to_create = ["Work", "Personal", "Finance"]
        result = service.create_labels(labels_to_create)

        assert result.success is True
        assert len(result.data) == len(labels_to_create)
        assert "Created 3 labels" in result.message

        # Verify all labels were created
        for label_name in labels_to_create:
            assert label_name in result.data


class TestPredictionService:
    """Test cases for PredictionService."""

    def test_predict_messages_success(self, setup_test_dependencies):
        """Test successful message prediction."""
        mocks = setup_test_dependencies

        # Initialize database
        mocks["database"].initialize("test.db")

        # Setup test data
        test_message = EmailMessage(
            id="test_msg_1",
            subject="work email",
            sender="boss@company.com",
            body="Please review the quarterly report",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        mocks["database"].add_test_message(test_message)
        mocks["model"].trained = True

        service = PredictionService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["config"],
            mocks["logger"],
        )

        result = service.predict_messages(limit=10)

        assert result.success is True
        assert len(result.data["predictions"]) > 0
        assert result.data["successful_predictions"] > 0

        # Verify the prediction contains expected fields
        prediction = result.data["predictions"][0]
        assert "message_id" in prediction
        assert "predicted_label" in prediction
        assert "confidence" in prediction
        assert "action" in prediction

    def test_predict_messages_untrained_model(self, setup_test_dependencies):
        """Test prediction with untrained model."""
        mocks = setup_test_dependencies
        mocks["model"].trained = False

        service = PredictionService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["config"],
            mocks["logger"],
        )

        result = service.predict_messages(limit=10)

        assert result.success is False
        assert "Model is not trained yet" in result.message

    def test_predict_messages_no_data(self, setup_test_dependencies):
        """Test prediction when no messages are available."""
        mocks = setup_test_dependencies
        mocks["model"].trained = True

        service = PredictionService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["config"],
            mocks["logger"],
        )

        result = service.predict_messages(limit=10)

        assert result.success is True
        assert result.data == []
        assert "No unreviewed messages found" in result.message


class TestTrainingService:
    """Test cases for TrainingService."""

    def test_train_model_success(self, setup_test_dependencies):
        """Test successful model training."""
        mocks = setup_test_dependencies

        # Initialize database
        mocks["database"].initialize("test.db")
        mocks["config"].set("training.min_samples_per_label", 2)

        # Setup training data
        training_messages = [
            EmailMessage(
                id=f"msg_{i}",
                subject=f"Test subject {i}",
                sender=f"test{i}@example.com",
                body=f"Test body content {i}",
                labels=["Work"] if i % 2 == 0 else ["Personal"],
                timestamp=datetime.now(),
            )
            for i in range(10)
        ]

        for msg in training_messages:
            mocks["database"].add_test_message(msg, is_reviewed=True, review_label=msg.labels[0])

        service = TrainingService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["file_system"],
            mocks["config"],
            mocks["logger"],
        )

        result = service.train_model(epochs=3, batch_size=32)

        assert result.success is True
        assert result.data["training_samples"] == 10
        assert "accuracy" in result.data["metrics"]
        assert "Model trained" in result.message

        # Verify model was trained and saved
        model_calls = mocks["model"].get_call_log()
        assert any("train" in str(call) for call in model_calls)
        assert any("save_model" in str(call) for call in model_calls)

    def test_train_model_no_data(self, setup_test_dependencies):
        """Test training when no training data is available."""
        mocks = setup_test_dependencies

        service = TrainingService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["file_system"],
            mocks["config"],
            mocks["logger"],
        )

        result = service.train_model()

        assert result.success is False
        assert "No training data available" in result.message

    def test_train_model_insufficient_data(self, setup_test_dependencies):
        """Test training with insufficient data per label."""
        mocks = setup_test_dependencies

        # Initialize database
        mocks["database"].initialize("test.db")

        # Add only a few samples (less than minimum required)
        training_messages = [
            EmailMessage(
                id="msg_1",
                subject="Test subject",
                sender="test@example.com",
                body="Test body content",
                labels=["Work"],
                timestamp=datetime.now(),
            )
        ]

        mocks["database"].add_test_message(
            training_messages[0], is_reviewed=True, review_label="Work"
        )

        service = TrainingService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["file_system"],
            mocks["config"],
            mocks["logger"],
        )

        result = service.train_model()

        assert result.success is False
        assert "Insufficient training data" in result.message


class TestActionService:
    """Test cases for ActionService."""

    def test_apply_actions_dry_run(self, setup_test_dependencies):
        """Test action application in dry run mode."""
        mocks = setup_test_dependencies

        # Initialize database
        mocks["database"].initialize("test.db")

        # Add test messages
        spam_message = EmailMessage(
            id="spam_msg",
            subject="Get rich quick spam email!",
            sender="spam@bad.com",
            body="Click here to win money",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        mocks["database"].add_test_message(spam_message)

        service = ActionService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        result = service.apply_actions(dry_run=True, limit=10)

        assert result.success is True
        assert result.data["dry_run"] is True
        assert len(result.data["actions"]) > 0

        # In dry run mode, no actual Gmail API calls for modifications should be made
        gmail_calls = mocks["gmail_api"].get_call_log()
        assert not any("trash_message" in str(call) for call in gmail_calls)
        assert not any("modify_message_labels" in str(call) for call in gmail_calls)

    def test_apply_actions_real_run(self, setup_test_dependencies):
        """Test action application in real mode."""
        mocks = setup_test_dependencies

        # Initialize database
        mocks["database"].initialize("test.db")

        # Add test messages
        spam_message = EmailMessage(
            id="spam_msg",
            subject="Get rich quick spam email!",
            sender="spam@bad.com",
            body="Click here to win money",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        mocks["database"].add_test_message(spam_message)

        service = ActionService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        result = service.apply_actions(dry_run=False, limit=10)

        assert result.success is True
        assert result.data["dry_run"] is False

        # In real mode, actual Gmail API calls should be made
        gmail_calls = mocks["gmail_api"].get_call_log()
        assert any("trash_message" in str(call) for call in gmail_calls)

    def test_apply_actions_no_messages(self, setup_test_dependencies):
        """Test action application when no messages are available."""
        mocks = setup_test_dependencies

        service = ActionService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        result = service.apply_actions(dry_run=True, limit=10)

        assert result.success is True
        assert result.data["applied_count"] == 0
        assert "No messages requiring actions" in result.message


class TestIntegration:
    """Integration tests that test multiple services working together."""

    def test_full_workflow(self, setup_test_dependencies):
        """Test a complete workflow: sync -> train -> predict -> apply."""
        mocks = setup_test_dependencies

        # Initialize database and set config
        mocks["database"].initialize("test.db")
        mocks["config"].set("training.min_samples_per_label", 1)

        # Setup test data
        test_messages = [
            EmailMessage(
                id=f"msg_{i}",
                subject="work email" if i % 2 == 0 else "spam email",
                sender=f"test{i}@example.com",
                body="Important work content" if i % 2 == 0 else "Buy now!",
                labels=["INBOX"],
                timestamp=datetime.now(),
            )
            for i in range(6)
        ]

        for msg in test_messages:
            mocks["gmail_api"].add_test_message(msg)

        # Step 1: Initialize and sync emails
        gmail_service = GmailService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        init_result = gmail_service.initialize()
        assert init_result.success

        sync_result = gmail_service.sync_emails(limit=10)
        assert sync_result.success
        assert sync_result.data["successfully_stored"] == 6

        # Step 2: Mark some messages as reviewed for training
        for i, msg in enumerate(test_messages[:4]):  # Review first 4 messages
            label = "Work" if i % 2 == 0 else "SPAM"
            mocks["database"].mark_message_reviewed(msg.id, label)

        # Step 3: Train model
        training_service = TrainingService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["file_system"],
            mocks["config"],
            mocks["logger"],
        )

        train_result = training_service.train_model(epochs=2)
        assert train_result.success
        assert train_result.data["training_samples"] == 4

        # Step 4: Generate predictions
        prediction_service = PredictionService(
            mocks["database"],
            mocks["model"],
            mocks["text_processor"],
            mocks["config"],
            mocks["logger"],
        )

        predict_result = prediction_service.predict_messages(limit=10)
        assert predict_result.success
        # Should predict on the 2 unreviewed messages
        assert predict_result.data["successful_predictions"] == 2

        # Step 5: Apply actions
        action_service = ActionService(
            mocks["gmail_api"], mocks["database"], mocks["config"], mocks["logger"]
        )

        apply_result = action_service.apply_actions(dry_run=True, limit=10)
        assert apply_result.success

        # Verify the complete workflow
        assert init_result.success
        assert sync_result.success
        assert train_result.success
        assert predict_result.success
        assert apply_result.success


if __name__ == "__main__":
    # Run tests if this file is executed directly
    pytest.main([__file__, "-v"])
