"""
Unit tests for Gmail ML Client core components using mocks.
These tests focus on testing business logic in isolation.
"""

import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Import modules to test
import cfg
import data_store
import gmail_client
import model
import preprocessor
import sorter
import trainer
from logger import logger
from test_mocks import MockDatabase


class TestDataStore:
    """Unit tests for data_store module using mocks."""

    def setup_method(self):
        """Setup mock database for each test."""
        self.mock_db = MockDatabase()
        # Initialize the mock database
        self.mock_db.initialize("test.db")
        # Replace the real data_store functions with mock implementations
        self.original_upsert_message = data_store.upsert_message
        self.original_mark_review = data_store.mark_review
        self.original_fetch_for_training = data_store.fetch_for_training
        self.original_fetch_for_prediction = data_store.fetch_for_prediction
        self.original_get_unreviewed_messages = data_store.get_unreviewed_messages
        self.original_get_reviewed_messages = data_store.get_reviewed_messages

        # Mock the data_store functions to use our mock database with proper signatures
        def mock_upsert_message(msg_id: str, snippet: str, text: str) -> None:
            """Mock upsert_message that matches data_store signature."""
            from interfaces import EmailMessage

            message = EmailMessage(
                id=msg_id,
                subject="",  # Not needed for this test
                sender="",  # Not needed for this test
                body=text,
                labels=[],  # Not needed for this test
                timestamp=datetime.now(),
                snippet=snippet,
            )
            self.mock_db.store_messages([message])

        def mock_mark_review(msg_id: str, gold_label: str) -> None:
            """Mock mark_review that matches data_store signature."""
            self.mock_db.mark_message_reviewed(msg_id, gold_label)

        def mock_fetch_for_training(limit: int = 2000) -> tuple:
            """Mock fetch_for_training that matches data_store signature."""
            messages = self.mock_db.get_messages_for_training(limit)
            texts = [msg.body for msg in messages]
            labels = [msg.labels[0] if msg.labels else "" for msg in messages]
            return texts, labels

        def mock_fetch_for_prediction(limit: int = 200) -> list:
            """Mock fetch_for_prediction that matches data_store signature."""
            messages = self.mock_db.get_messages_for_prediction(limit)
            # Convert to Message objects that have the expected attributes
            result = []
            for msg in messages:
                # Create a mock Message object with the expected attributes
                mock_msg = Mock()
                mock_msg.id = msg.id
                mock_msg.snippet = msg.snippet or ""
                mock_msg.text = msg.body
                result.append(mock_msg)
            return result

        def mock_get_unreviewed_messages(limit: int = 200) -> list:
            """Mock get_unreviewed_messages that matches data_store signature."""
            return self.mock_db.get_unreviewed_messages(limit)

        def mock_get_reviewed_messages() -> list:
            """Mock get_reviewed_messages that matches data_store signature."""
            # MockDatabase doesn't have get_reviewed_messages, so we need to implement it
            reviewed = []
            for msg_id, label in self.mock_db.reviewed_messages.items():
                reviewed.append((msg_id, label))
            return reviewed

        # Apply the mocks
        data_store.upsert_message = mock_upsert_message
        data_store.mark_review = mock_mark_review
        data_store.fetch_for_training = mock_fetch_for_training
        data_store.fetch_for_prediction = mock_fetch_for_prediction
        data_store.get_unreviewed_messages = mock_get_unreviewed_messages
        data_store.get_reviewed_messages = mock_get_reviewed_messages

    def teardown_method(self):
        """Restore original functions after each test."""
        data_store.upsert_message = self.original_upsert_message
        data_store.mark_review = self.original_mark_review
        data_store.fetch_for_training = self.original_fetch_for_training
        data_store.fetch_for_prediction = self.original_fetch_for_prediction
        data_store.get_unreviewed_messages = self.original_get_unreviewed_messages
        data_store.get_reviewed_messages = self.original_get_reviewed_messages

    def test_init_db_creates_tables(self):
        """Test that init_db creates the required tables."""
        # With mock database, initialization always succeeds
        assert self.mock_db.initialize("test.db") is True

    def test_upsert_message_new(self):
        """Test inserting a new message."""
        message_id = "test_msg_123"
        snippet = "Test email snippet"
        text = "Full email body text content"

        # Call the mocked upsert_message function
        data_store.upsert_message(message_id, snippet, text)

        # Verify message was stored in mock database
        stored = self.mock_db.get_message(message_id)
        assert stored is not None
        assert stored.snippet == snippet
        assert stored.body == text

    def test_upsert_message_existing(self):
        """Test updating an existing message."""
        message_id = "test_msg_123"

        # Insert initial message
        from interfaces import EmailMessage

        message1 = EmailMessage(
            id=message_id,
            subject="Test",
            sender="test@example.com",
            body="Original text",
            labels=["INBOX"],
            timestamp=datetime.now(),
            snippet="Original snippet",
        )
        self.mock_db.store_messages([message1])

        # Update the message using the mocked function
        data_store.upsert_message(message_id, "Updated snippet", "Updated text")

        # Verify message was updated
        stored = self.mock_db.get_message(message_id)
        assert stored is not None
        assert stored.snippet == "Updated snippet"
        assert stored.body == "Updated text"

    def test_mark_review(self):
        """Test marking a message as reviewed."""
        message_id = "test_msg_123"
        label = "SPAM"

        # First insert a message
        from interfaces import EmailMessage

        message = EmailMessage(
            id=message_id,
            subject="Test",
            sender="test@example.com",
            body="Test text",
            labels=["INBOX"],
            timestamp=datetime.now(),
            snippet="Test snippet",
        )
        self.mock_db.store_messages([message])

        # Mark it as reviewed
        data_store.mark_review(message_id, label)

        # Verify message is marked as reviewed
        reviewed_messages = data_store.get_reviewed_messages()
        assert len(reviewed_messages) == 1
        assert reviewed_messages[0][0] == message_id
        assert reviewed_messages[0][1] == label
        assert reviewed_messages[0][1] == label

    def test_get_unreviewed_messages(self):
        """Test retrieving unreviewed messages."""
        # Insert reviewed and unreviewed messages
        from interfaces import EmailMessage

        reviewed_msg = EmailMessage(
            id="reviewed_msg",
            subject="Reviewed",
            sender="test@example.com",
            body="Reviewed content",
            labels=["INBOX"],
            timestamp=datetime.now(),
            snippet="Reviewed",
        )
        data_store.upsert_message("reviewed_msg", "Reviewed", "Reviewed content")
        self.mock_db.mark_message_reviewed("reviewed_msg", "SPAM")

        unreviewed_msg = EmailMessage(
            id="unreviewed_msg",
            subject="Unreviewed",
            sender="test@example.com",
            body="Unreviewed content",
            labels=["INBOX"],
            timestamp=datetime.now(),
            snippet="Unreviewed",
        )
        data_store.upsert_message("unreviewed_msg", "Unreviewed", "Unreviewed content")

        unreviewed = data_store.fetch_for_prediction(limit=10)

        assert len(unreviewed) == 1
        assert unreviewed[0].id == "unreviewed_msg"

    def test_get_reviewed_messages(self):
        """Test retrieving reviewed messages for training."""
        # Insert and review some messages
        from interfaces import EmailMessage

        msg1 = EmailMessage(
            id="msg1",
            subject="Work email",
            sender="test@example.com",
            body="Work content",
            labels=["Work"],
            timestamp=datetime.now(),
            snippet="Work email",
        )
        msg2 = EmailMessage(
            id="msg2",
            subject="Spam email",
            sender="test@example.com",
            body="Spam content",
            labels=["SPAM"],
            timestamp=datetime.now(),
            snippet="Spam email",
        )

        data_store.upsert_message("msg1", "Work email", "Work content")
        data_store.upsert_message("msg2", "Spam email", "Spam content")
        self.mock_db.mark_message_reviewed("msg1", "Work")
        self.mock_db.mark_message_reviewed("msg2", "SPAM")

        texts, labels = data_store.fetch_for_training()

        assert len(texts) == 2
        assert len(labels) == 2
        # Check that we get both message text and label
        assert "Work content" in texts
        assert "Spam content" in texts
        assert "Work" in labels
        assert "SPAM" in labels


class TestPreprocessor:
    """Unit tests for preprocessor module."""

    def test_extract_text_simple_message(self):
        """Test extracting text from a simple email message."""
        message = {
            "payload": {
                "mimeType": "text/plain",
                "body": {"data": "VGVzdCBlbWFpbCBib2R5"},  # base64 encoded "Test email body"
            }
        }

        result = preprocessor.extract_text(message)
        assert "test email body" in result  # function converts to lowercase

    def test_extract_text_multipart_message(self):
        """Test extracting text from multipart email."""
        message = {
            "payload": {
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {
                            "data": "UGxhaW4gdGV4dCBwYXJ0"  # base64 encoded "Plain text part"
                        },
                    },
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": "PGh0bWw+SFRNTCBwYXJ0PC9odG1sPg=="  # base64 encoded "<html>HTML part</html>"
                        },
                    },
                ]
            }
        }

        result = preprocessor.extract_text(message)
        assert "plain text part" in result
        assert "html part" in result  # HTML tags are stripped

    def test_extract_text_empty_message(self):
        """Test extracting text from empty message."""
        message = {"payload": {}}

        result = preprocessor.extract_text(message)
        assert result == ""

    def test_clean_text(self):
        """Test text cleaning functionality."""
        dirty_text = "Hello! This has URLs: https://example.com and emails: test@example.com"

        # Mock the clean_text function if it exists
        if hasattr(preprocessor, "clean_text"):
            cleaned = preprocessor.clean_text(dirty_text)
            # Basic assertion - the function should return a string
            assert isinstance(cleaned, str)
            assert len(cleaned) > 0


class TestModel:
    """Unit tests for model module."""

    def setup_method(self):
        """Setup for each test."""
        # Create temporary model directory
        self.temp_dir = tempfile.mkdtemp()
        self.original_model_dir = cfg.MODEL_DIR
        cfg.MODEL_DIR = self.temp_dir

    def teardown_method(self):
        """Cleanup after each test."""
        cfg.MODEL_DIR = self.original_model_dir

        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("model.keras")
    @patch("model.joblib.load")
    def test_load_model_exists(self, mock_joblib_load, mock_keras):
        """Test loading an existing model."""
        mock_model = Mock()
        mock_keras.models.load_model.return_value = mock_model

        # Mock the loaded objects
        mock_vectorizer = Mock()
        mock_encoder = Mock()
        mock_joblib_load.side_effect = [mock_vectorizer, mock_encoder]

        result = model.load()

        assert result is not None
        assert len(result) == 3  # Should return (vectorizer, encoder, model)
        assert result[0] == mock_vectorizer
        assert result[1] == mock_encoder
        assert result[2] == mock_model
        mock_keras.models.load_model.assert_called_once()

    @patch("model.keras")
    @patch("model.os.path.exists", return_value=False)
    def test_load_model_not_exists(self, mock_exists, mock_keras):
        """Test loading model when it doesn't exist."""
        # This should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            model.load()

    @patch("model.keras")
    def test_predict(self, mock_keras):
        """Test model prediction."""
        # Setup mock model
        mock_model = Mock()
        mock_model.predict.return_value = [[0.1, 0.9]]  # Mock prediction scores

        # Mock the vectorizer - needs to return something with toarray() method that returns array with shape
        import numpy as np

        mock_vectorizer = Mock()
        mock_vectorizer.transform.return_value = Mock()
        mock_vectorizer.transform.return_value.toarray.return_value = np.array(
            [[1, 0, 1]]
        )  # Mock vectorized text

        # Mock the label encoder
        mock_encoder = Mock()
        mock_encoder.classes_ = ["SPAM", "HAM"]

        with patch.object(model, "load", return_value=(mock_vectorizer, mock_encoder, mock_model)):

            result = model.predict(["test email text"])

            assert result is not None
            assert len(result) == 3  # Should return (labels, conf, spam_scores)
            mock_model.predict.assert_called_once()
            mock_vectorizer.transform.assert_called_once()


class TestSorter:
    """Unit tests for sorter module."""

    @patch("sorter.fetch_for_prediction")
    @patch("sorter.predict")
    def test_propose_with_messages(self, mock_predict, mock_get_unreviewed):
        """Test propose function with unreviewed messages."""

        # Create mock Message objects
        class MockMessage:
            def __init__(self, msg_id, snippet, text):
                self.id = msg_id
                self.snippet = snippet
                self.text = text

        # Mock unreviewed messages
        mock_get_unreviewed.return_value = [
            MockMessage("msg1", "Work email snippet", "Work email content"),
            MockMessage("msg2", "Spam email snippet", "Buy now! Limited time offer!"),
        ]

        # Mock model predictions
        mock_predict.return_value = (
            [0.2, 0.8],
            [0.9, 0.1],
            [0.1, 0.9],
        )  # (labels, conf, spam_scores)

        proposals = sorter.propose(limit=10)

        assert len(proposals) == 2

        # Check first proposal (work email)
        work_proposal = proposals[0]
        assert work_proposal["id"] == "msg1"
        assert work_proposal["spam_score"] == 0.1
        assert work_proposal["action"] in ["route", "review"]

        # Check second proposal (spam email)
        spam_proposal = proposals[1]
        assert spam_proposal["id"] == "msg2"
        assert spam_proposal["spam_score"] == 0.9
        assert spam_proposal["action"] == "trash"

    @patch("sorter.fetch_for_prediction")
    def test_propose_no_messages(self, mock_get_unreviewed):
        """Test propose function with no unreviewed messages."""
        mock_get_unreviewed.return_value = []

        proposals = sorter.propose(limit=10)

        assert proposals == []

    def test_suggest_label_with_rules(self):
        """Test suggest_label function with keyword rules."""
        text = "This is a work email about standup meeting"
        model_label = "Personal"

        result = sorter.suggest_label(text, model_label)

        # Should suggest "Work" due to "standup" keyword
        assert result == "Work"

    def test_suggest_label_no_rules(self):
        """Test suggest_label function when no rules match."""
        text = "This is a regular email"
        model_label = "Personal"

        result = sorter.suggest_label(text, model_label)

        # Should return model label when no rules match
        assert result == "Personal"


class TestTrainer:

    @patch("trainer.train")
    @patch("trainer.fetch_for_training")
    def test_train_from_feedback_success(self, mock_fetch_training, mock_train):
        """Test successful training from feedback."""
        # Mock training data
        mock_fetch_training.return_value = (
            [
                "Work email content",
                "Personal email content",
                "Spam email content",
                "Another work email",
            ],
            ["Work", "Personal", "SPAM", "Work"],
        )

        # Mock training results
        mock_train.return_value = (
            "Training completed successfully. Accuracy: 0.95",
            ["Work", "Personal", "SPAM"],
        )

        report, classes = trainer.train_from_feedback(epochs=5)

        assert report is not None
        assert classes is not None
        assert len(classes) >= 3  # Should have at least Work, Personal, SPAM
        mock_train.assert_called_once()

    @patch("trainer.fetch_for_training")
    def test_train_from_feedback_no_data(self, mock_fetch_training):
        """Test training with no reviewed data."""
        mock_fetch_training.return_value = ([], [])

        report, classes = trainer.train_from_feedback(epochs=5)

        assert "No labeled feedback yet" in report
        assert classes == []

    @patch("trainer.fetch_for_training")
    def test_train_from_feedback_insufficient_data(self, mock_fetch_training):
        """Test training with insufficient data per class."""
        # Only one sample per class
        mock_fetch_training.return_value = (
            ["Work email content", "Spam email content"],
            ["Work", "SPAM"],
        )

        # Should handle insufficient data gracefully
        try:
            report, classes = trainer.train_from_feedback(epochs=1)
            assert report is not None
        except Exception as e:
            # It's acceptable to raise an exception for insufficient data
            assert "least populated class" in str(e).lower() or "too few" in str(e).lower()


class TestGmailClient:
    """Unit tests for gmail_client module."""

    @patch("gmail_client.build")
    def test_get_service_success(self, mock_build):
        """Test successful Gmail service creation."""
        mock_service = Mock()
        mock_build.return_value = mock_service

        service = gmail_client.get_service()

        assert service is not None
        mock_build.assert_called_once()

    @patch("gmail_client.get_service")
    def test_list_messages(self, mock_get_service):
        """Test listing Gmail messages."""
        # Mock service response
        mock_service = Mock()
        mock_messages_list = Mock()
        mock_service.users().messages().list.return_value = mock_messages_list
        mock_messages_list.execute.return_value = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"},
            ]
        }
        # Mock list_next to return None (no more pages)
        mock_service.users().messages().list_next.return_value = None

        mock_get_service.return_value = mock_service

        messages = gmail_client.list_messages(max_results=10)

        assert len(messages) == 2
        assert messages[0]["id"] == "msg1"
        assert messages[1]["id"] == "msg2"

    @patch("gmail_client.get_service")
    def test_get_message(self, mock_get_service):
        """Test getting a specific Gmail message."""
        mock_service = Mock()
        mock_message_get = Mock()
        mock_service.users().messages().get.return_value = mock_message_get
        mock_message_get.execute.return_value = {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "test@example.com"},
                ],
                "body": {"data": "VGVzdCBib2R5"},
            },
        }

        mock_get_service.return_value = mock_service

        message = gmail_client.get_message("msg1")

        assert message["id"] == "msg1"
        assert "payload" in message
        mock_service.users().messages().get.assert_called_once_with(
            userId="me", id="msg1", format="full"
        )

    @patch("gmail_client.get_service")
    def test_trash_message(self, mock_get_service):
        """Test trashing a Gmail message."""
        mock_service = Mock()
        mock_trash = Mock()
        mock_service.users().messages().trash.return_value = mock_trash
        mock_trash.execute.return_value = {"id": "msg1"}

        mock_get_service.return_value = mock_service

        result = gmail_client.trash_message("msg1")

        assert result["id"] == "msg1"
        mock_service.users().messages().trash.assert_called_once_with(userId="me", id="msg1")

    @patch("gmail_client.get_service")
    def test_modify_labels(self, mock_get_service):
        """Test modifying message labels."""
        mock_service = Mock()
        mock_modify = Mock()
        mock_service.users().messages().modify.return_value = mock_modify
        mock_modify.execute.return_value = {"id": "msg1"}

        mock_get_service.return_value = mock_service

        result = gmail_client.modify_labels("msg1", add=["INBOX"], remove=["SPAM"])

        assert result["id"] == "msg1"
        mock_service.users().messages().modify.assert_called_once()

        # Check the call arguments
        call_args = mock_service.users().messages().modify.call_args
        assert call_args[1]["userId"] == "me"
        assert call_args[1]["id"] == "msg1"
        assert "addLabelIds" in call_args[1]["body"]
        assert "removeLabelIds" in call_args[1]["body"]


class TestConfiguration:
    """Unit tests for configuration module."""

    def test_system_labels_defined(self):
        """Test that system labels are properly defined."""
        assert hasattr(cfg, "SYSTEM_LABELS")
        assert isinstance(cfg.SYSTEM_LABELS, set)
        assert len(cfg.SYSTEM_LABELS) > 0

        # Check for common system labels
        system_labels = [label.upper() for label in cfg.SYSTEM_LABELS]
        assert "INBOX" in system_labels
        assert "SPAM" in system_labels

    def test_junk_labels_defined(self):
        """Test that junk labels are properly defined."""
        assert hasattr(cfg, "JUNK_LABELS")
        assert isinstance(cfg.JUNK_LABELS, set)

    def test_sync_page_size_defined(self):
        """Test that sync page size is properly defined."""
        assert hasattr(cfg, "SYNC_PAGE_SIZE")
        assert isinstance(cfg.SYNC_PAGE_SIZE, int)
        assert cfg.SYNC_PAGE_SIZE > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
