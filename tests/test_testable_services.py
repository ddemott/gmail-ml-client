"""
Comprehensive test suite for Gmail ML Client using the testable services architecture.
This focuses on testing the new testable components that we built.
"""

import pytest

# Import our testable components
from src.gmail_ml_client.interfaces import (
    EmailMessage,
    Interfaces,
    configure_dependencies_for_testing,
    get_dependency,
)
from src.gmail_ml_client.testable_services import (
    ActionService,
    GmailService,
    PredictionService,
    TrainingService,
)


class TestTestableServicesWithMocks:
    """Test the testable services using the mock framework."""

    def setup_method(self):
        """Setup test dependencies before each test."""
        configure_dependencies_for_testing()

        # Get mock instances for direct manipulation in tests
        self.gmail_api = get_dependency(Interfaces.GMAIL_API)
        self.database = get_dependency(Interfaces.DATABASE)
        self.file_system = get_dependency(Interfaces.FILE_SYSTEM)
        self.model = get_dependency(Interfaces.MODEL)
        self.text_processor = get_dependency(Interfaces.TEXT_PROCESSOR)
        self.config = get_dependency(Interfaces.CONFIGURATION)
        self.logger = get_dependency(Interfaces.LOGGER)

        # Clear any previous state
        self._clear_all_mocks()

    def _clear_all_mocks(self):
        """Clear state from all mocks."""
        self.gmail_api.clear_call_log()
        self.database.clear_call_log()
        self.file_system.clear_call_log()
        self.model.clear_call_log()
        self.text_processor.clear_call_log()
        self.config.clear_call_log()
        self.logger.clear_logs()


class TestGmailService(TestTestableServicesWithMocks):
    """Test cases for TestableGmailService."""

    def test_initialize_success(self):
        """Test successful Gmail service initialization."""
        service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        result = service.initialize()

        assert result.success is True
        assert "Gmail service initialized" in result.message

        # Verify dependencies were called
        assert ("authenticate",) in self.gmail_api.get_call_log()
        assert ("initialize", "test.db") in self.database.get_call_log()

        # Verify logging
        logs = self.logger.get_logs("INFO")
        assert any("Initializing Gmail service" in log[1] for log in logs)

    def test_initialize_gmail_auth_failure(self):
        """Test Gmail service initialization with authentication failure."""
        self.gmail_api.set_should_fail(True)

        service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        result = service.initialize()

        assert result.success is False
        assert "Gmail authentication failed" in result.message

    def test_sync_emails_success(self):
        """Test successful email synchronization."""
        from datetime import datetime

        # Add test messages to mock Gmail API
        test_message = EmailMessage(
            id="test_msg_1",
            subject="Test Subject",
            sender="test@example.com",
            body="Test body content",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        self.gmail_api.add_test_message(test_message)

        service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        # Initialize the service first
        init_result = service.initialize()
        assert init_result.success

        # Ensure mocks are properly set
        self.gmail_api.authenticated = True
        self.database.initialized = True

        result = service.sync_emails(limit=10)

        assert result.success is True
        assert result.data["successfully_stored"] > 0
        assert "Synced" in result.message

        # Verify API calls
        call_log = self.gmail_api.get_call_log()
        assert any("list_messages" in str(call) for call in call_log)
        assert any("get_message" in str(call) for call in call_log)

    def test_sync_emails_no_messages(self):
        """Test email sync when no messages are available."""
        service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        # Initialize the service first
        init_result = service.initialize()
        assert init_result.success

        # Ensure mocks are properly set
        self.gmail_api.authenticated = True
        self.database.initialized = True

        # Clear any default messages from the mock
        self.gmail_api.clear_data()

        result = service.sync_emails(limit=10)

        assert result.success is True
        # When no messages, data is an empty list
        assert result.data == []
        assert "No new messages to sync" in result.message

    def test_create_labels_success(self):
        """Test successful label creation."""
        service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        # Initialize the service first to ensure authentication
        init_result = service.initialize()
        assert init_result.success

        labels_to_create = ["Work", "Personal", "Finance"]
        result = service.create_labels(labels_to_create)

        assert result.success is True
        assert len(result.data) == len(labels_to_create)
        assert "Created 3 labels" in result.message

        # Verify all labels were created
        for label_name in labels_to_create:
            assert label_name in result.data


class TestPredictionService(TestTestableServicesWithMocks):
    """Test cases for TestablePredictionService."""

    def test_predict_messages_success(self):
        """Test successful message prediction."""
        from datetime import datetime

        # Setup test data
        test_message = EmailMessage(
            id="test_msg_1",
            subject="work email",
            sender="boss@company.com",
            body="Please review the quarterly report",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        self.database.add_test_message(test_message)
        self.model.trained = True

        # Initialize database
        self.database.initialize("test.db")

        service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        result = service.predict_messages(limit=10)

        assert result.success is True
        assert isinstance(result.data, dict)
        assert len(result.data["predictions"]) > 0
        assert result.data["successful_predictions"] > 0

        # Verify the prediction contains expected fields
        prediction = result.data["predictions"][0]
        assert "message_id" in prediction
        assert "predicted_label" in prediction
        assert "confidence" in prediction
        assert "action" in prediction

    def test_predict_messages_untrained_model(self):
        """Test prediction with untrained model."""
        self.model.trained = False

        service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        result = service.predict_messages(limit=10)

        assert result.success is False
        assert "Model is not trained yet" in result.message

    def test_predict_messages_no_data(self):
        """Test prediction when no messages are available."""
        self.model.trained = True

        service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        result = service.predict_messages(limit=10)

        assert result.success is True
        assert result.data == []
        assert "No unreviewed messages found" in result.message


class TestTrainingService(TestTestableServicesWithMocks):
    """Test cases for TestableTrainingService."""

    def test_train_model_success(self):
        """Test successful model training."""
        from datetime import datetime

        # Setup training data with enough samples per label
        training_messages = []
        for i in range(10):  # 10 messages total
            if i < 5:  # 5 Work messages
                label = "Work"
            else:  # 5 Personal messages
                label = "Personal"
            msg = EmailMessage(
                id=f"msg_{i}",
                subject=f"Test subject {i}",
                sender=f"test{i}@example.com",
                body=f"Test body content {i}",
                labels=[label],
                timestamp=datetime.now(),
            )
            training_messages.append(msg)

        for msg in training_messages:
            self.database.add_test_message(msg, is_reviewed=True, review_label=msg.labels[0])

        # Initialize database
        self.database.initialize("test.db")

        service = TrainingService(
            self.database,
            self.model,
            self.text_processor,
            self.file_system,
            self.config,
            self.logger,
        )

        result = service.train_model(epochs=3, batch_size=32)

        assert result.success is True
        assert result.data["training_samples"] == 10
        assert "accuracy" in result.data["metrics"]
        assert "Model trained" in result.message

        # Verify model was trained and saved
        model_calls = self.model.get_call_log()
        assert any("train" in str(call) for call in model_calls)
        assert any("save_model" in str(call) for call in model_calls)

    def test_train_model_no_data(self):
        """Test training when no training data is available."""
        service = TrainingService(
            self.database,
            self.model,
            self.text_processor,
            self.file_system,
            self.config,
            self.logger,
        )

        result = service.train_model()

        assert result.success is False
        assert "No training data available" in result.message


class TestActionService(TestTestableServicesWithMocks):
    """Test cases for TestableActionService."""

    def test_apply_actions_dry_run(self):
        """Test action application in dry run mode."""
        from datetime import datetime

        # Add test messages to both API and database
        spam_message = EmailMessage(
            id="spam_msg",
            subject="Get rich quick spam email!",
            sender="spam@bad.com",
            body="Click here to win money",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        self.gmail_api.add_test_message(spam_message)
        self.database.add_test_message(spam_message)

        # Initialize database
        self.database.initialize("test.db")

        service = ActionService(self.gmail_api, self.database, self.config, self.logger)

        result = service.apply_actions(dry_run=True, limit=10)

        assert result.success is True
        assert "dry_run" in result.data
        assert result.data["dry_run"] is True
        assert len(result.data["actions"]) > 0

        # In dry run mode, no actual Gmail API calls for modifications should be made
        gmail_calls = self.gmail_api.get_call_log()
        assert not any("trash_message" in str(call) for call in gmail_calls)
        assert not any("modify_message_labels" in str(call) for call in gmail_calls)

    def test_apply_actions_real_run(self):
        """Test action application in real mode."""
        from datetime import datetime

        # Add test messages to both API and database
        spam_message = EmailMessage(
            id="spam_msg",
            subject="Get rich quick spam email!",
            sender="spam@bad.com",
            body="Click here to win money",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        self.gmail_api.add_test_message(spam_message)
        self.database.add_test_message(spam_message)

        # Initialize database
        self.database.initialize("test.db")

        service = ActionService(self.gmail_api, self.database, self.config, self.logger)

        result = service.apply_actions(dry_run=False, limit=10)

        assert result.success is True
        assert "dry_run" in result.data
        assert result.data["dry_run"] is False

        # In real mode, actual Gmail API calls should be made
        gmail_calls = self.gmail_api.get_call_log()
        assert any("trash_message" in str(call) for call in gmail_calls)


class TestIntegrationWorkflows(TestTestableServicesWithMocks):
    """Integration tests that test multiple services working together."""

    def test_complete_email_management_workflow(self):
        """Test a complete workflow: sync -> train -> predict -> apply."""
        from datetime import datetime

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
            for i in range(10)  # Create 10 messages to ensure minimum samples
        ]

        for msg in test_messages:
            self.gmail_api.add_test_message(msg)

        # Step 1: Initialize and sync emails
        gmail_service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        init_result = gmail_service.initialize()
        assert init_result.success

        sync_result = gmail_service.sync_emails(limit=10)
        assert sync_result.success
        assert sync_result.data["successfully_stored"] == 10

        # Step 2: Mark some messages as reviewed for training (provide enough samples per label)
        for i in range(10):  # Review first 10 messages to ensure minimum samples (5 Work, 5 SPAM)
            if i < 5:  # 5 Work messages
                label = "Work"
            else:  # 5 SPAM messages
                label = "SPAM"
            self.database.mark_message_reviewed(test_messages[i].id, label)

        # Step 3: Train model
        training_service = TrainingService(
            self.database,
            self.model,
            self.text_processor,
            self.file_system,
            self.config,
            self.logger,
        )

        train_result = training_service.train_model(epochs=2)
        assert train_result.success
        assert train_result.data["training_samples"] == 10

        # Step 4: Generate predictions
        prediction_service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        predict_result = prediction_service.predict_messages(limit=10)
        assert predict_result.success
        # All messages are reviewed, so no predictions to make
        assert predict_result.data == []

        # Step 5: Apply actions
        action_service = ActionService(self.gmail_api, self.database, self.config, self.logger)

        apply_result = action_service.apply_actions(dry_run=True, limit=10)
        assert apply_result.success

        # Verify the complete workflow
        assert init_result.success
        assert sync_result.success
        assert train_result.success
        assert predict_result.success
        assert apply_result.success

    def test_error_handling_workflow(self):
        """Test error handling throughout the workflow."""
        # Test Gmail API failure
        self.gmail_api.set_should_fail(True)

        gmail_service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        init_result = gmail_service.initialize()
        assert not init_result.success
        assert "Gmail authentication failed" in init_result.message

        # Test training with no data
        training_service = TrainingService(
            self.database,
            self.model,
            self.text_processor,
            self.file_system,
            self.config,
            self.logger,
        )

        train_result = training_service.train_model()
        assert not train_result.success
        assert "No training data available" in train_result.message

        # Test prediction with untrained model
        self.model.trained = False

        prediction_service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        predict_result = prediction_service.predict_messages(limit=10)
        assert not predict_result.success
        assert "Model is not trained yet" in predict_result.message


class TestMockFunctionality:
    """Test the mock framework itself to ensure it's working correctly."""

    def setup_method(self):
        """Setup test dependencies."""
        configure_dependencies_for_testing()
        self.gmail_api = get_dependency(Interfaces.GMAIL_API)
        self.database = get_dependency(Interfaces.DATABASE)

    def test_mock_call_logging(self):
        """Test that mock call logging works."""
        # Clear previous calls
        self.gmail_api.clear_call_log()

        # Make some calls
        self.gmail_api.authenticate()
        self.gmail_api.list_messages(max_results=10)

        # Verify calls were logged
        call_log = self.gmail_api.get_call_log()
        assert len(call_log) == 2
        assert ("authenticate",) in call_log
        assert ("list_messages", None, 10) in call_log

    def test_mock_failure_simulation(self):
        """Test that mock failure simulation works."""
        # Enable failure mode
        self.gmail_api.set_should_fail(True)

        # Calls should now fail (return False instead of raising)
        result = self.gmail_api.authenticate()
        assert result is False

        # Disable failure mode
        self.gmail_api.set_should_fail(False)

        # Calls should work again
        result = self.gmail_api.authenticate()
        assert result is True

    def test_mock_data_management(self):
        """Test mock data management functionality."""
        from datetime import datetime

        # Initialize database
        self.database.initialize("test.db")

        # Add test message
        test_message = EmailMessage(
            id="test_msg",
            subject="Test",
            sender="test@example.com",
            body="Test body",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )

        self.database.add_test_message(test_message)

        # Verify message can be retrieved
        messages = self.database.get_unreviewed_messages(limit=10)
        assert len(messages) == 1
        assert messages[0][0] == "test_msg"  # messages is list of (id, snippet) tuples

        # Mark as reviewed
        self.database.mark_message_reviewed("test_msg", "Work")

        # Should no longer be in unreviewed
        unreviewed = self.database.get_unreviewed_messages(limit=10)
        assert len(unreviewed) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
