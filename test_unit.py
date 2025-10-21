"""
Unit tests for Gmail ML Client core components using mocks.
These tests focus on testing business logic in isolation.
"""
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from typing import Dict, List, Any

# Import modules to test
import cfg
import data_store
import gmail_client
import model
import preprocessor
import sorter
import trainer
from logger import logger


class TestDataStore:
    """Unit tests for data_store module."""
    
    def setup_method(self):
        """Setup test database in memory for each test."""
        self.db_path = ":memory:"
        data_store.DATABASE_PATH = self.db_path
        data_store.init_db()
    
    def test_init_db_creates_tables(self):
        """Test that init_db creates the required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check messages table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        assert cursor.fetchone() is not None
        
        # Check reviews table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_upsert_message_new(self):
        """Test inserting a new message."""
        message_id = "test_msg_123"
        snippet = "Test email snippet"
        text = "Full email body text content"
        
        data_store.upsert_message(message_id, snippet, text)
        
        # Verify message was inserted
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == message_id
        assert result[1] == snippet
        assert result[2] == text
        assert result[3] is not None  # created_at
        
        conn.close()
    
    def test_upsert_message_existing(self):
        """Test updating an existing message."""
        message_id = "test_msg_123"
        
        # Insert initial message
        data_store.upsert_message(message_id, "Original snippet", "Original text")
        
        # Update the message
        data_store.upsert_message(message_id, "Updated snippet", "Updated text")
        
        # Verify only one record exists with updated content
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), snippet, text FROM messages WHERE id = ?", (message_id,))
        count, snippet, text = cursor.fetchone()
        
        assert count == 1
        assert snippet == "Updated snippet"
        assert text == "Updated text"
        
        conn.close()
    
    def test_mark_review(self):
        """Test marking a message as reviewed."""
        message_id = "test_msg_123"
        label = "SPAM"
        
        # First insert a message
        data_store.upsert_message(message_id, "Test snippet", "Test text")
        
        # Mark it as reviewed
        data_store.mark_review(message_id, label)
        
        # Verify review record
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reviews WHERE message_id = ?", (message_id,))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == message_id
        assert result[1] == label
        assert result[2] is not None  # reviewed_at
        
        conn.close()
    
    def test_get_unreviewed_messages(self):
        """Test retrieving unreviewed messages."""
        # Insert reviewed and unreviewed messages
        data_store.upsert_message("reviewed_msg", "Reviewed", "Reviewed content")
        data_store.upsert_message("unreviewed_msg", "Unreviewed", "Unreviewed content")
        data_store.mark_review("reviewed_msg", "SPAM")
        
        unreviewed = data_store.get_unreviewed_messages(limit=10)
        
        assert len(unreviewed) == 1
        assert unreviewed[0][0] == "unreviewed_msg"
    
    def test_get_reviewed_messages(self):
        """Test retrieving reviewed messages for training."""
        # Insert and review some messages
        data_store.upsert_message("msg1", "Work email", "Work content")
        data_store.upsert_message("msg2", "Spam email", "Spam content")
        data_store.mark_review("msg1", "Work")
        data_store.mark_review("msg2", "SPAM")
        
        reviewed = data_store.get_reviewed_messages()
        
        assert len(reviewed) == 2
        # Check that we get both message text and label
        texts = [r[0] for r in reviewed]
        labels = [r[1] for r in reviewed]
        
        assert "Work content" in texts
        assert "Spam content" in texts
        assert "Work" in labels
        assert "SPAM" in labels


class TestPreprocessor:
    """Unit tests for preprocessor module."""
    
    def test_extract_text_simple_message(self):
        """Test extracting text from a simple email message."""
        message = {
            'payload': {
                'body': {
                    'data': 'VGVzdCBlbWFpbCBib2R5'  # base64 encoded "Test email body"
                }
            }
        }
        
        result = preprocessor.extract_text(message)
        assert "Test email body" in result
    
    def test_extract_text_multipart_message(self):
        """Test extracting text from multipart email."""
        message = {
            'payload': {
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': 'UGxhaW4gdGV4dCBwYXJ0'  # base64 encoded "Plain text part"
                        }
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': 'PGh0bWw+SFRNTCBwYXJ0PC9odG1sPg=='  # base64 encoded "<html>HTML part</html>"
                        }
                    }
                ]
            }
        }
        
        result = preprocessor.extract_text(message)
        assert "Plain text part" in result
        assert "HTML part" in result
    
    def test_extract_text_empty_message(self):
        """Test extracting text from empty message."""
        message = {'payload': {}}
        
        result = preprocessor.extract_text(message)
        assert result == ""
    
    def test_clean_text(self):
        """Test text cleaning functionality."""
        dirty_text = "Hello! This has URLs: https://example.com and emails: test@example.com"
        
        # Mock the clean_text function if it exists
        if hasattr(preprocessor, 'clean_text'):
            cleaned = preprocessor.clean_text(dirty_text)
            # Basic assertion - the function should return a string
            assert isinstance(cleaned, str)
            assert len(cleaned) > 0


class TestModel:
    """Unit tests for model module."""
    
    def setup_method(self):
        """Setup for each test."""
        # Create temporary model path
        self.temp_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.temp_dir, "test_model")
        
        # Patch the model path
        self.original_path = model.MODEL_PATH if hasattr(model, 'MODEL_PATH') else None
        if hasattr(model, 'MODEL_PATH'):
            model.MODEL_PATH = self.model_path
    
    def teardown_method(self):
        """Cleanup after each test."""
        if self.original_path and hasattr(model, 'MODEL_PATH'):
            model.MODEL_PATH = self.original_path
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('model.tensorflow')
    def test_load_model_exists(self, mock_tf):
        """Test loading an existing model."""
        mock_tf.keras.models.load_model.return_value = Mock()
        
        # Create a dummy model file
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path + ".h5", 'w') as f:
            f.write("dummy model")
        
        result = model.load_model()
        
        assert result is not None
        mock_tf.keras.models.load_model.assert_called_once()
    
    @patch('model.tensorflow')
    def test_load_model_not_exists(self, mock_tf):
        """Test loading model when it doesn't exist."""
        result = model.load_model()
        
        # Should return None when model doesn't exist
        assert result is None
    
    @patch('model.tensorflow')
    def test_predict(self, mock_tf):
        """Test model prediction."""
        # Setup mock model
        mock_model = Mock()
        mock_model.predict.return_value = [[0.1, 0.9]]  # Mock prediction scores
        
        # Mock the vectorizer
        mock_vectorizer = Mock()
        mock_vectorizer.transform.return_value = [[1, 0, 1]]  # Mock vectorized text
        
        with patch.object(model, 'load_model', return_value=mock_model), \
             patch.object(model, 'load_vectorizer', return_value=mock_vectorizer):
            
            result = model.predict("test email text")
            
            assert result is not None
            assert len(result) == 2  # Should return predictions for 2 classes
            mock_model.predict.assert_called_once()
            mock_vectorizer.transform.assert_called_once()


class TestSorter:
    """Unit tests for sorter module."""
    
    @patch('sorter.data_store.get_unreviewed_messages')
    @patch('sorter.model.predict')
    def test_propose_with_messages(self, mock_predict, mock_get_unreviewed):
        """Test propose function with unreviewed messages."""
        # Mock unreviewed messages
        mock_get_unreviewed.return_value = [
            ("msg1", "Work email snippet", "Work email content"),
            ("msg2", "Spam email snippet", "Buy now! Limited time offer!")
        ]
        
        # Mock model predictions
        mock_predict.side_effect = [
            [0.2, 0.8],  # Work email: low spam, high work
            [0.9, 0.1]   # Spam email: high spam, low work
        ]
        
        proposals = sorter.propose(limit=10)
        
        assert len(proposals) == 2
        
        # Check first proposal (work email)
        work_proposal = proposals[0]
        assert work_proposal['id'] == 'msg1'
        assert work_proposal['spam_score'] == 0.2
        assert work_proposal['action'] in ['route', 'review']
        
        # Check second proposal (spam email)
        spam_proposal = proposals[1]
        assert spam_proposal['id'] == 'msg2'
        assert spam_proposal['spam_score'] == 0.9
        assert spam_proposal['action'] == 'trash'
    
    @patch('sorter.data_store.get_unreviewed_messages')
    def test_propose_no_messages(self, mock_get_unreviewed):
        """Test propose function with no unreviewed messages."""
        mock_get_unreviewed.return_value = []
        
        proposals = sorter.propose(limit=10)
        
        assert proposals == []
    
    @patch('sorter.model.predict')
    def test_classify_text_spam(self, mock_predict):
        """Test classifying spam text."""
        mock_predict.return_value = [0.95, 0.05]  # High spam score
        
        result = sorter.classify_text("Buy now! Limited time offer!")
        
        # Should detect as spam
        assert result['spam_score'] >= 0.5
        assert result['action'] == 'trash'
    
    @patch('sorter.model.predict')
    def test_classify_text_ham(self, mock_predict):
        """Test classifying legitimate text."""
        mock_predict.return_value = [0.1, 0.9]  # Low spam score
        
        result = sorter.classify_text("Meeting scheduled for tomorrow at 2 PM")
        
        # Should not be spam
        assert result['spam_score'] < 0.5
        assert result['action'] in ['route', 'review']


class TestTrainer:
    """Unit tests for trainer module."""
    
    @patch('trainer.data_store.get_reviewed_messages')
    @patch('trainer.model.train_model')
    def test_train_from_feedback_success(self, mock_train_model, mock_get_reviewed):
        """Test successful training from feedback."""
        # Mock training data
        mock_get_reviewed.return_value = [
            ("Work email content", "Work"),
            ("Personal email content", "Personal"),
            ("Spam email content", "SPAM"),
            ("Another work email", "Work")
        ]
        
        # Mock training results
        mock_train_model.return_value = {
            'accuracy': 0.95,
            'loss': 0.05,
            'epochs': 5
        }
        
        report, classes = trainer.train_from_feedback(epochs=5)
        
        assert report is not None
        assert classes is not None
        assert len(classes) >= 3  # Should have at least Work, Personal, SPAM
        mock_train_model.assert_called_once()
    
    @patch('trainer.data_store.get_reviewed_messages')
    def test_train_from_feedback_no_data(self, mock_get_reviewed):
        """Test training with no reviewed data."""
        mock_get_reviewed.return_value = []
        
        with pytest.raises(Exception):
            trainer.train_from_feedback(epochs=5)
    
    @patch('trainer.data_store.get_reviewed_messages')
    def test_train_from_feedback_insufficient_data(self, mock_get_reviewed):
        """Test training with insufficient data per class."""
        # Only one sample per class
        mock_get_reviewed.return_value = [
            ("Work email content", "Work"),
            ("Spam email content", "SPAM")
        ]
        
        # Should handle insufficient data gracefully
        try:
            report, classes = trainer.train_from_feedback(epochs=1)
            assert report is not None
        except Exception as e:
            # It's acceptable to raise an exception for insufficient data
            assert "insufficient" in str(e).lower() or "data" in str(e).lower()


class TestGmailClient:
    """Unit tests for gmail_client module."""
    
    @patch('gmail_client.build')
    def test_get_service_success(self, mock_build):
        """Test successful Gmail service creation."""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        with patch('gmail_client.authenticate') as mock_auth:
            mock_auth.return_value = Mock()
            
            service = gmail_client.get_service()
            
            assert service is not None
            mock_build.assert_called_once()
    
    @patch('gmail_client.get_service')
    def test_list_messages(self, mock_get_service):
        """Test listing Gmail messages."""
        # Mock service response
        mock_service = Mock()
        mock_messages_list = Mock()
        mock_service.users().messages().list.return_value = mock_messages_list
        mock_messages_list.execute.return_value = {
            'messages': [
                {'id': 'msg1', 'threadId': 'thread1'},
                {'id': 'msg2', 'threadId': 'thread2'}
            ]
        }
        
        mock_get_service.return_value = mock_service
        
        messages = gmail_client.list_messages(max_results=10)
        
        assert len(messages) == 2
        assert messages[0]['id'] == 'msg1'
        assert messages[1]['id'] == 'msg2'
    
    @patch('gmail_client.get_service')
    def test_get_message(self, mock_get_service):
        """Test getting a specific Gmail message."""
        mock_service = Mock()
        mock_message_get = Mock()
        mock_service.users().messages().get.return_value = mock_message_get
        mock_message_get.execute.return_value = {
            'id': 'msg1',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'From', 'value': 'test@example.com'}
                ],
                'body': {'data': 'VGVzdCBib2R5'}
            }
        }
        
        mock_get_service.return_value = mock_service
        
        message = gmail_client.get_message('msg1')
        
        assert message['id'] == 'msg1'
        assert 'payload' in message
        mock_service.users().messages().get.assert_called_once_with(userId='me', id='msg1')
    
    @patch('gmail_client.get_service')
    def test_trash_message(self, mock_get_service):
        """Test trashing a Gmail message."""
        mock_service = Mock()
        mock_trash = Mock()
        mock_service.users().messages().trash.return_value = mock_trash
        mock_trash.execute.return_value = {'id': 'msg1'}
        
        mock_get_service.return_value = mock_service
        
        result = gmail_client.trash_message('msg1')
        
        assert result['id'] == 'msg1'
        mock_service.users().messages().trash.assert_called_once_with(userId='me', id='msg1')
    
    @patch('gmail_client.get_service')
    def test_modify_labels(self, mock_get_service):
        """Test modifying message labels."""
        mock_service = Mock()
        mock_modify = Mock()
        mock_service.users().messages().modify.return_value = mock_modify
        mock_modify.execute.return_value = {'id': 'msg1'}
        
        mock_get_service.return_value = mock_service
        
        result = gmail_client.modify_labels('msg1', add=['INBOX'], remove=['SPAM'])
        
        assert result['id'] == 'msg1'
        mock_service.users().messages().modify.assert_called_once()
        
        # Check the call arguments
        call_args = mock_service.users().messages().modify.call_args
        assert call_args[1]['userId'] == 'me'
        assert call_args[1]['id'] == 'msg1'
        assert 'addLabelIds' in call_args[1]['body']
        assert 'removeLabelIds' in call_args[1]['body']


class TestConfiguration:
    """Unit tests for configuration module."""
    
    def test_system_labels_defined(self):
        """Test that system labels are properly defined."""
        assert hasattr(cfg, 'SYSTEM_LABELS')
        assert isinstance(cfg.SYSTEM_LABELS, list)
        assert len(cfg.SYSTEM_LABELS) > 0
        
        # Check for common system labels
        system_labels = [label.upper() for label in cfg.SYSTEM_LABELS]
        assert 'INBOX' in system_labels
        assert 'SPAM' in system_labels
    
    def test_junk_labels_defined(self):
        """Test that junk labels are properly defined."""
        assert hasattr(cfg, 'JUNK_LABELS')
        assert isinstance(cfg.JUNK_LABELS, list)
    
    def test_sync_page_size_defined(self):
        """Test that sync page size is properly defined."""
        assert hasattr(cfg, 'SYNC_PAGE_SIZE')
        assert isinstance(cfg.SYNC_PAGE_SIZE, int)
        assert cfg.SYNC_PAGE_SIZE > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])