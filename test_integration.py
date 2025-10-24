"""
Integration tests for Gmail ML Client.
These tests verify that multiple components work together correctly.
"""

import os
import shutil
import sqlite3
import tempfile
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import modules for integration testing
import cfg
import data_store
import gmail_client
import model
import preprocessor
import sorter
import trainer
from interfaces import Interfaces, configure_dependencies_for_testing, get_dependency
from testable_services import ActionService, GmailService, PredictionService, TrainingService


class TestDataStorePersistence:
    """Integration tests for data persistence across operations."""

    def setup_method(self):
        """Setup test environment for each test."""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        import cfg

        cfg.DB_PATH = self.db_path
        data_store.init_db()

    def teardown_method(self):
        """Cleanup after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_message_lifecycle(self):
        """Test complete message lifecycle: insert -> review -> retrieve."""
        message_id = "test_msg_123"
        snippet = "Test email about work"
        text = "This is an important work email about the quarterly report."

        # 1. Insert message
        data_store.upsert_message(message_id, snippet, text)

        # 2. Verify message is unreviewed
        unreviewed = data_store.get_unreviewed_messages(limit=10)
        assert len(unreviewed) == 1
        assert unreviewed[0][0] == message_id

        # 3. Mark as reviewed
        data_store.mark_review(message_id, "Work")

        # 4. Verify no longer in unreviewed
        unreviewed_after = data_store.get_unreviewed_messages(limit=10)
        assert len(unreviewed_after) == 0

        # 5. Verify in reviewed messages
        reviewed = data_store.get_reviewed_messages()
        assert len(reviewed) == 1
        assert reviewed[0][1] == "Work"  # Label should be "Work"

    def test_multiple_message_operations(self):
        """Test operations with multiple messages."""
        # Insert multiple messages
        messages = [
            ("msg1", "Work email 1", "Important project update"),
            ("msg2", "Personal email", "Family dinner plans"),
            ("msg3", "Spam email", "Buy now! Limited time offer!"),
            ("msg4", "Work email 2", "Meeting scheduled for tomorrow"),
        ]

        for msg_id, snippet, text in messages:
            data_store.upsert_message(msg_id, snippet, text)

        # Review some messages
        data_store.mark_review("msg1", "Work")
        data_store.mark_review("msg3", "SPAM")

        # Check unreviewed count
        unreviewed = data_store.get_unreviewed_messages(limit=10)
        assert len(unreviewed) == 2  # msg2 and msg4

        # Check reviewed count
        reviewed = data_store.get_reviewed_messages()
        assert len(reviewed) == 2  # msg1 and msg3

        # Verify specific labels
        reviewed_labels = [r[1] for r in reviewed]
        assert "Work" in reviewed_labels
        assert "SPAM" in reviewed_labels


class TestEmailProcessingWorkflow:
    """Integration tests for email processing workflow."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        import cfg

        cfg.DB_PATH = self.db_path
        data_store.init_db()

    def teardown_method(self):
        """Cleanup after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_email_extraction_and_storage(self):
        """Test extracting text from email and storing in database."""
        # Mock Gmail message
        mock_message = {
            "id": "test_msg_123",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Work Email"},
                    {"name": "From", "value": "boss@company.com"},
                ],
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {
                            "data": "SW1wb3J0YW50IHdvcmsgdXBkYXRlIGFib3V0IHRoZSBwcm9qZWN0"  # "Important work update about the project"
                        },
                    }
                ],
            },
            "snippet": "Important work update...",
        }

        # Extract text
        extracted_text = preprocessor.extract_text(mock_message)
        assert "important work update" in extracted_text

        # Store in database
        data_store.upsert_message(mock_message["id"], mock_message["snippet"], extracted_text)

        # Verify storage
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (mock_message["id"],))
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == mock_message["id"]
        assert "important work update" in result[2]

        conn.close()

    @patch("sorter.predict")
    def test_prediction_workflow(self, mock_predict):
        """Test complete prediction workflow."""
        # Setup test data
        data_store.upsert_message("msg1", "Work email", "Project meeting tomorrow")
        data_store.upsert_message("msg2", "Spam email", "Buy now! Limited offer!")

        # Mock model predictions - predict returns (labels, conf, spam_scores)
        mock_predict.return_value = (
            ["Work", "SPAM"],  # labels
            [0.9, 0.95],  # confidence scores
            [0.1, 0.95],  # spam scores
        )

        # Run predictions
        proposals = sorter.propose(limit=10)

        assert len(proposals) == 2

        # Check work email proposal
        work_proposal = next(p for p in proposals if p["id"] == "msg1")
        assert work_proposal["spam_score"] == 0.1
        assert work_proposal["action"] in ["route", "review"]

        # Check spam email proposal
        spam_proposal = next(p for p in proposals if p["id"] == "msg2")
        assert spam_proposal["spam_score"] == 0.95
        assert spam_proposal["action"] == "trash"


class TestTestableServicesIntegration:
    """Integration tests for the new testable services architecture."""

    def setup_method(self):
        """Setup test dependencies."""
        configure_dependencies_for_testing()

        # Get mocks for manipulation
        self.gmail_api = get_dependency(Interfaces.GMAIL_API)
        self.database = get_dependency(Interfaces.DATABASE)
        self.file_system = get_dependency(Interfaces.FILE_SYSTEM)
        self.model = get_dependency(Interfaces.MODEL)
        self.text_processor = get_dependency(Interfaces.TEXT_PROCESSOR)
        self.config = get_dependency(Interfaces.CONFIGURATION)
        self.logger = get_dependency(Interfaces.LOGGER)

        # Clear state
        self.gmail_api.clear_call_log()
        self.gmail_api.clear_data()
        self.database.clear_call_log()
        self.database.clear_data()
        self.file_system.clear_call_log()
        self.model.clear_call_log()
        self.text_processor.clear_call_log()
        self.config.clear_call_log()
        self.logger.clear_logs()

    def test_email_sync_to_prediction_workflow(self):
        """Test complete workflow from sync to prediction."""
        from datetime import datetime

        from interfaces import EmailMessage

        # 1. Setup test messages in Gmail API mock
        test_messages = [
            EmailMessage(
                id="work_msg_1",
                subject="Project Update",
                sender="manager@company.com",
                body="Please review the quarterly report and provide feedback",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
            EmailMessage(
                id="spam_msg_1",
                subject="Get Rich Quick!",
                sender="spam@malicious.com",
                body="Click here to win millions! Limited time offer!",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
        ]

        for msg in test_messages:
            self.gmail_api.add_test_message(msg)

        # 2. Sync emails using GmailService
        gmail_service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        init_result = gmail_service.initialize()
        assert init_result.success

        sync_result = gmail_service.sync_emails(limit=10)
        assert sync_result.success
        assert sync_result.data["successfully_stored"] == 2

        # 3. Train model with some reviewed data
        self.database.mark_message_reviewed("work_msg_1", "Work")
        self.database.mark_message_reviewed("spam_msg_1", "SPAM")
        self.model.trained = True

        # 4. Run predictions on new messages
        # Add a new unreviewed message
        new_message = EmailMessage(
            id="new_msg_1",
            subject="Important Meeting",
            sender="colleague@company.com",
            body="Team meeting scheduled for tomorrow at 2 PM",
            labels=["INBOX"],
            timestamp=datetime.now(),
        )
        self.gmail_api.add_test_message(new_message)

        # Sync the new message
        sync_result2 = gmail_service.sync_emails(limit=10)
        assert sync_result2.success

        # Run predictions
        prediction_service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        predict_result = prediction_service.predict_messages(limit=10)
        assert predict_result.success
        assert predict_result.data["successful_predictions"] >= 1

        # Verify predictions contain expected fields
        predictions = predict_result.data["predictions"]
        assert len(predictions) >= 1

        for prediction in predictions:
            assert "message_id" in prediction
            assert "predicted_label" in prediction
            assert "confidence" in prediction
            assert "action" in prediction

    def test_training_to_prediction_workflow(self):
        """Test workflow from training to making predictions."""
        from datetime import datetime

        from interfaces import EmailMessage

        # Initialize database
        self.database.initialize("test.db")

        # Configure minimum samples for testing
        self.config.set("training.min_samples_per_label", 2)

        # 1. Add training data
        training_messages = [
            ("work_msg_1", "Work content about projects", "Work"),
            ("work_msg_2", "Meeting agenda for next week", "Work"),
            ("personal_msg_1", "Family dinner plans", "Personal"),
            ("personal_msg_2", "Weekend hiking trip", "Personal"),
            ("spam_msg_1", "Buy now! Limited offer!", "SPAM"),
            ("spam_msg_2", "Click here to win money!", "SPAM"),
        ]

        for msg_id, content, label in training_messages:
            msg = EmailMessage(
                id=msg_id,
                subject=f"Subject for {msg_id}",
                sender="test@example.com",
                body=content,
                labels=["INBOX"],
                timestamp=datetime.now(),
            )
            self.database.add_test_message(msg, is_reviewed=True, review_label=label)

        # 2. Train model
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
        assert train_result.data["training_samples"] == 6
        assert "accuracy" in train_result.data["metrics"]

        # 3. Add new messages for prediction
        prediction_messages = [
            EmailMessage(
                id="pred_msg_1",
                subject="Project deadline",
                sender="boss@company.com",
                body="The project deadline has been moved to next Friday",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
            EmailMessage(
                id="pred_msg_2",
                subject="Amazing deal!",
                sender="marketing@spam.com",
                body="Don't miss this incredible opportunity! Act now!",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
        ]

        for msg in prediction_messages:
            self.database.add_test_message(msg, is_reviewed=False)

        # 4. Make predictions
        prediction_service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        predict_result = prediction_service.predict_messages(limit=10)
        assert predict_result.success
        assert predict_result.data["successful_predictions"] == 2

        # 5. Verify predictions make sense
        predictions = predict_result.data["predictions"]
        assert len(predictions) == 2

        # Find work-related prediction
        work_prediction = next(p for p in predictions if p["message_id"] == "pred_msg_1")
        assert work_prediction["predicted_label"] == "Work"
        assert work_prediction["confidence"] > 0.5

        # Find spam prediction
        spam_prediction = next(p for p in predictions if p["message_id"] == "pred_msg_2")
        assert spam_prediction["predicted_label"] == "SPAM"
        assert spam_prediction["action"] == "trash"

    def test_end_to_end_email_management(self):
        """Test complete end-to-end email management workflow."""
        from datetime import datetime

        from interfaces import EmailMessage

        # 1. Initialize Gmail service
        gmail_service = GmailService(self.gmail_api, self.database, self.config, self.logger)

        init_result = gmail_service.initialize()
        assert init_result.success

        # 2. Add and sync initial messages
        initial_messages = [
            EmailMessage(
                id="init_work_1",
                subject="Quarterly Report",
                sender="finance@company.com",
                body="Please review the quarterly financial report",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
            EmailMessage(
                id="init_spam_1",
                subject="You've Won!",
                sender="lottery@fake.com",
                body="Congratulations! You've won a million dollars!",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
        ]

        for msg in initial_messages:
            self.gmail_api.add_test_message(msg)

        sync_result = gmail_service.sync_emails(limit=10)
        assert sync_result.success
        assert sync_result.data["successfully_stored"] == 2

        # 3. Manually review some messages for training
        self.database.mark_message_reviewed("init_work_1", "Work")
        self.database.mark_message_reviewed("init_spam_1", "SPAM")

        # Configure minimum samples for testing
        self.config.set("training.min_samples_per_label", 1)

        # 4. Train the model
        training_service = TrainingService(
            self.database,
            self.model,
            self.text_processor,
            self.file_system,
            self.config,
            self.logger,
        )

        train_result = training_service.train_model(epochs=1)
        assert train_result.success

        # 5. Add new messages that need classification
        new_messages = [
            EmailMessage(
                id="new_work_1",
                subject="Team Meeting",
                sender="team@company.com",
                body="Weekly team meeting scheduled for tomorrow",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
            EmailMessage(
                id="new_spam_1",
                subject="Urgent: Claim Your Prize",
                sender="scam@malicious.com",
                body="Act fast! Your prize is waiting. Click now!",
                labels=["INBOX"],
                timestamp=datetime.now(),
            ),
        ]

        for msg in new_messages:
            self.gmail_api.add_test_message(msg)

        # Sync new messages
        sync_result2 = gmail_service.sync_emails(limit=10)
        assert sync_result2.success

        # 6. Generate predictions
        prediction_service = PredictionService(
            self.database, self.model, self.text_processor, self.config, self.logger
        )

        predict_result = prediction_service.predict_messages(limit=10)
        assert predict_result.success
        assert predict_result.data["successful_predictions"] == 2

        # 7. Apply actions based on predictions
        action_service = ActionService(self.gmail_api, self.database, self.config, self.logger)

        # First do a dry run
        dry_run_result = action_service.apply_actions(dry_run=True, limit=10)
        assert dry_run_result.success
        assert dry_run_result.data["dry_run"] is True

        # Then apply actions for real
        apply_result = action_service.apply_actions(dry_run=False, limit=10)
        assert apply_result.success
        assert apply_result.data["dry_run"] is False

        # 8. Verify actions were taken
        gmail_calls = self.gmail_api.get_call_log()

        # Should have made some action calls (trash_message or modify_message_labels)
        action_calls = [
            call
            for call in gmail_calls
            if "trash_message" in str(call) or "modify_message_labels" in str(call)
        ]
        assert len(action_calls) > 0

        # Verify logging throughout the process
        all_logs = self.logger.get_logs()
        assert len(all_logs) > 0

        # Should have logs from each service
        log_messages = [log[1] for log in all_logs]
        assert any("Gmail service" in msg for msg in log_messages)
        assert any("Training" in msg for msg in log_messages)
        assert any("Prediction" in msg for msg in log_messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
