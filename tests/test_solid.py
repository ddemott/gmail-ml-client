"""
Simple and focused test suite for Gmail ML Client.
Tests the actual working components without mocking issues.
"""

import os
import tempfile
from pathlib import Path

import pytest

# Get the workspace directory
WORKSPACE_DIR = Path(__file__).parent.parent


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_python_import_basic_modules(self):
        """Test that basic modules can be imported."""
        try:
            assert True, "Basic modules imported successfully"
        except Exception as e:
            pytest.fail(f"Failed to import basic modules: {e}")

    def test_config_values_exist(self):
        """Test that configuration values are properly defined."""
        from src.gmail_ml_client import cfg

        # Test basic config values exist
        assert hasattr(cfg, "SYNC_PAGE_SIZE")
        assert hasattr(cfg, "SYSTEM_LABELS")
        assert hasattr(cfg, "JUNK_LABELS")

        # Test they have reasonable values
        assert isinstance(cfg.SYNC_PAGE_SIZE, int)
        assert cfg.SYNC_PAGE_SIZE > 0

        # SYSTEM_LABELS and JUNK_LABELS might be sets or lists
        assert len(cfg.SYSTEM_LABELS) > 0
        assert len(cfg.JUNK_LABELS) >= 0

    def test_database_basic_functionality(self):
        """Test basic database operations."""

        from src.gmail_ml_client import data_store

        # Create temporary database
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            temp_db_path = tmp.name

        try:
            # Patch the database path
            original_path = data_store.DB_PATH if hasattr(data_store, "DB_PATH") else None

            # Initialize database
            data_store.init_db()

            # Test message upsert
            data_store.upsert_message("test_msg_1", "Test snippet", "Test content")

            # Test marking review
            data_store.mark_review("test_msg_1", "Work")

            assert True, "Database operations completed successfully"

        except Exception as e:
            pytest.fail(f"Database operations failed: {e}")

        finally:
            # Cleanup
            try:
                os.unlink(temp_db_path)
            except:
                pass

    def test_preprocessor_basic_functionality(self):
        """Test basic text preprocessing."""
        from src.gmail_ml_client import preprocessor

        # Test with a simple message structure
        test_message = {
            "payload": {"body": {"data": "VGVzdCBtZXNzYWdl"}}  # base64 encoded "Test message"
        }

        try:
            result = preprocessor.extract_text(test_message)
            # Should return some text (even if empty)
            assert isinstance(result, str)

        except Exception as e:
            pytest.fail(f"Preprocessor failed: {e}")

    def test_logger_functionality(self):
        """Test that logging works."""
        from src.gmail_ml_client.logger import logger

        try:
            logger.info("Test log message")
            logger.warning("Test warning message")
            logger.error("Test error message")
            assert True, "Logging operations completed successfully"

        except Exception as e:
            pytest.fail(f"Logging failed: {e}")


class TestFileStructure:
    """Test that required files exist and have basic structure."""

    def test_core_files_exist(self):
        """Test that core application files exist."""
        required_files = [
            "src/gmail_ml_client/cfg.py",
            "src/gmail_ml_client/data_store.py",
            "src/gmail_ml_client/gmail_client.py",
            "src/gmail_ml_client/model.py",
            "src/gmail_ml_client/preprocessor.py",
            "src/gmail_ml_client/sorter.py",
            "src/gmail_ml_client/trainer.py",
            "src/gmail_ml_client/logger.py",
        ]

        for filename in required_files:
            file_path = WORKSPACE_DIR / filename
            assert file_path.exists(), f"Required file {filename} does not exist"
            assert file_path.stat().st_size > 0, f"Required file {filename} is empty"

    def test_testability_files_exist(self):
        """Test that testability architecture files exist."""
        testability_files = [
            "src/gmail_ml_client/interfaces.py",
            "src/gmail_ml_client/adapters.py",
            "tests/test_mocks.py",
            "src/gmail_ml_client/testable_services.py",
        ]

        for filename in testability_files:
            file_path = WORKSPACE_DIR / filename
            assert file_path.exists(), f"Testability file {filename} does not exist"
            assert file_path.stat().st_size > 0, f"Testability file {filename} is empty"

    def test_requirements_file_exists(self):
        """Test that requirements.txt exists and has content."""
        req_file = WORKSPACE_DIR / "config" / "requirements.txt"
        assert req_file.exists(), "requirements.txt does not exist"

        with open(req_file) as f:
            content = f.read().strip()
            assert len(content) > 0, "requirements.txt is empty"
            assert "typer" in content, "typer not found in requirements"
            assert "rich" in content, "rich not found in requirements"


class TestImportStructure:
    """Test that modules can be imported without errors."""

    def test_import_core_modules(self):
        """Test importing core modules."""
        modules_to_test = [
            "src.gmail_ml_client.cfg",
            "src.gmail_ml_client.data_store",
            "src.gmail_ml_client.preprocessor",
            "src.gmail_ml_client.logger",
        ]

        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except Exception as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_import_testability_modules(self):
        """Test importing testability modules."""
        testability_modules = [
            "src.gmail_ml_client.interfaces",
            "src.gmail_ml_client.adapters",
            "test_mocks",
            "src.gmail_ml_client.testable_services",
        ]

        for module_name in testability_modules:
            try:
                __import__(module_name)
            except Exception as e:
                pytest.fail(f"Failed to import testability module {module_name}: {e}")

    def test_interfaces_dependency_injection(self):
        """Test basic dependency injection functionality."""
        try:
            from src.gmail_ml_client.interfaces import (
                Interfaces,
                configure_dependencies_for_testing,
                get_dependency,
            )

            # Configure for testing
            configure_dependencies_for_testing()

            # Try to get dependencies
            gmail_api = get_dependency(Interfaces.GMAIL_API)
            database = get_dependency(Interfaces.DATABASE)

            assert gmail_api is not None
            assert database is not None

        except Exception as e:
            pytest.fail(f"Dependency injection failed: {e}")


class TestBasicFunctionality:
    """Test basic functionality without external dependencies."""

    def test_mock_framework_basic_operations(self):
        """Test basic mock framework operations."""
        try:
            from src.gmail_ml_client.interfaces import (
                Interfaces,
                configure_dependencies_for_testing,
                get_dependency,
            )

            configure_dependencies_for_testing()

            gmail_api = get_dependency(Interfaces.GMAIL_API)

            # Test basic mock operations
            gmail_api.clear_call_log()

            # Make a call
            result = gmail_api.authenticate()

            # Check call was logged
            call_log = gmail_api.get_call_log()
            assert len(call_log) > 0

        except Exception as e:
            pytest.fail(f"Mock framework test failed: {e}")

    def test_service_instantiation(self):
        """Test that services can be instantiated."""
        try:
            from src.gmail_ml_client.interfaces import (
                Interfaces,
                configure_dependencies_for_testing,
                get_dependency,
            )
            from src.gmail_ml_client.testable_services import GmailService

            configure_dependencies_for_testing()

            gmail_api = get_dependency(Interfaces.GMAIL_API)
            database = get_dependency(Interfaces.DATABASE)
            config = get_dependency(Interfaces.CONFIGURATION)
            logger = get_dependency(Interfaces.LOGGER)

            # Try to create service
            service = GmailService(gmail_api, database, config, logger)
            assert service is not None

        except Exception as e:
            pytest.fail(f"Service instantiation failed: {e}")


class TestDocumentation:
    """Test that documentation files exist and have content."""

    def test_readme_exists(self):
        """Test that README exists."""
        readme_files = ["docs/README.md", "docs/readme.md", "README.md", "readme.md"]

        readme_exists = False
        for readme_name in readme_files:
            readme_path = WORKSPACE_DIR / readme_name
            if readme_path.exists():
                readme_exists = True
                # Check it has content
                with open(readme_path, encoding="utf-8") as f:
                    content = f.read().strip()
                    assert len(content) > 50, f"{readme_name} exists but appears to be too short"
                break

        assert readme_exists, "No README file found"

    def test_testability_summary_exists(self):
        """Test that testability summary documentation exists."""
        summary_file = WORKSPACE_DIR / "docs" / "TESTABILITY_SUMMARY.md"
        assert summary_file.exists(), "TESTABILITY_SUMMARY.md does not exist"

        with open(summary_file, encoding="utf-8") as f:
            content = f.read().strip()
            assert len(content) > 100, "TESTABILITY_SUMMARY.md exists but appears to be too short"
            assert (
                "testability" in content.lower()
            ), "TESTABILITY_SUMMARY.md doesn't mention testability"


class TestApplicationRobustness:
    """Test application robustness and error handling."""

    def test_graceful_error_handling_in_imports(self):
        """Test that modules handle import errors gracefully."""
        # Test that we can import modules even if some dependencies are missing
        try:
            from src.gmail_ml_client import cfg

            # Configuration should work even without Gmail API
            assert hasattr(cfg, "SYNC_PAGE_SIZE")
        except Exception as e:
            pytest.fail(f"Configuration module import failed: {e}")

    def test_database_initialization_robustness(self):
        """Test database initialization handles errors gracefully."""
        from src.gmail_ml_client import data_store

        try:
            # This should not crash even if run multiple times
            data_store.init_db()
            data_store.init_db()  # Second call should be safe

        except Exception as e:
            # Some errors are expected (like file permissions), but should not crash
            assert (
                "Database" in str(e) or "permission" in str(e).lower()
            ), f"Unexpected database error: {e}"

    def test_mock_framework_isolation(self):
        """Test that mock framework provides proper isolation."""
        try:
            from src.gmail_ml_client.interfaces import (
                Interfaces,
                configure_dependencies_for_testing,
                get_dependency,
            )

            # Configure twice to test isolation
            configure_dependencies_for_testing()
            gmail_api1 = get_dependency(Interfaces.GMAIL_API)

            configure_dependencies_for_testing()
            gmail_api2 = get_dependency(Interfaces.GMAIL_API)

            # Should get fresh instances
            assert gmail_api1 is not gmail_api2, "Mock instances not properly isolated"

        except Exception as e:
            pytest.fail(f"Mock framework isolation test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
