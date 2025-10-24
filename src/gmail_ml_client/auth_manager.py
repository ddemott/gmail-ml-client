"""
Authentication and credential management layer.
Handles OAuth flows, token refresh, and secure credential storage.
"""

import hashlib
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .logger import logger


class AuthProvider(Enum):
    """Supported authentication providers."""

    GOOGLE_OAUTH = "google_oauth"
    SERVICE_ACCOUNT = "service_account"
    API_KEY = "api_key"


@dataclass
class AuthConfig:
    """Authentication configuration."""

    provider: AuthProvider
    credentials_file: str
    token_file: str
    scopes: list[str]
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None

    def validate(self) -> list[str]:
        """Validate authentication configuration."""
        errors = []
        if not self.credentials_file:
            errors.append("credentials file path cannot be empty")
        if not self.token_file:
            errors.append("token file path cannot be empty")
        if not self.scopes:
            errors.append("scopes cannot be empty")
        return errors


@dataclass
class TokenInfo:
    """Information about authentication tokens."""

    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str]
    token_type: str = "Bearer"

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at

    def expires_soon(self, threshold_minutes: int = 5) -> bool:
        """Check if token expires soon."""
        if not self.expires_at:
            return False
        threshold = datetime.utcnow() + timedelta(minutes=threshold_minutes)
        return self.expires_at <= threshold


class CredentialStore(ABC):
    """Abstract base class for credential storage."""

    @abstractmethod
    def store_credentials(self, key: str, credentials: dict[str, Any]) -> None:
        """Store credentials."""
        pass

    @abstractmethod
    def load_credentials(self, key: str) -> dict[str, Any] | None:
        """Load credentials."""
        pass

    @abstractmethod
    def delete_credentials(self, key: str) -> None:
        """Delete credentials."""
        pass

    @abstractmethod
    def list_keys(self) -> list[str]:
        """List all stored credential keys."""
        pass


class FileCredentialStore(CredentialStore):
    """File-based credential storage with encryption."""

    def __init__(self, storage_dir: str = ".auth"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._ensure_secure_permissions()

    def _ensure_secure_permissions(self) -> None:
        """Ensure storage directory has secure permissions."""
        try:
            # On Unix-like systems, restrict permissions
            if hasattr(os, "chmod"):
                os.chmod(self.storage_dir, 0o700)
        except Exception as e:
            logger.warning(f"Could not set secure permissions on {self.storage_dir}: {e}")

    def _get_file_path(self, key: str) -> Path:
        """Get file path for credential key."""
        # Hash the key to avoid filesystem issues
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.storage_dir / f"{key_hash}.cred"

    def _encrypt_data(self, data: bytes) -> bytes:
        """Simple XOR encryption (replace with proper encryption in production)."""
        # This is a basic implementation - use proper encryption libraries in production
        key = os.environ.get("GMAIL_ML_CRYPT_KEY", "default_key_change_me").encode()
        key = (key * (len(data) // len(key) + 1))[: len(data)]
        return bytes(a ^ b for a, b in zip(data, key, strict=False))

    def _decrypt_data(self, data: bytes) -> bytes:
        """Simple XOR decryption."""
        return self._encrypt_data(data)  # XOR is symmetric

    def store_credentials(self, key: str, credentials: dict[str, Any]) -> None:
        """Store credentials to encrypted file."""
        try:
            file_path = self._get_file_path(key)
            data = json.dumps(credentials).encode()
            encrypted_data = self._encrypt_data(data)

            with open(file_path, "wb") as f:
                f.write(encrypted_data)

            # Set secure file permissions
            if hasattr(os, "chmod"):
                os.chmod(file_path, 0o600)

            logger.debug(f"Stored credentials for key: {key}")
        except Exception as e:
            logger.error(f"Failed to store credentials for {key}: {e}")
            raise

    def load_credentials(self, key: str) -> dict[str, Any] | None:
        """Load credentials from encrypted file."""
        try:
            file_path = self._get_file_path(key)
            if not file_path.exists():
                return None

            with open(file_path, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self._decrypt_data(encrypted_data)
            credentials = json.loads(decrypted_data.decode())

            logger.debug(f"Loaded credentials for key: {key}")
            return credentials
        except Exception as e:
            logger.error(f"Failed to load credentials for {key}: {e}")
            return None

    def delete_credentials(self, key: str) -> None:
        """Delete credentials file."""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted credentials for key: {key}")
        except Exception as e:
            logger.error(f"Failed to delete credentials for {key}: {e}")

    def list_keys(self) -> list[str]:
        """List all stored credential keys."""
        # This is a limitation of the hashed approach - we can't reverse the hash
        # In a production system, you'd store a mapping file or use a different approach
        return [f.stem for f in self.storage_dir.glob("*.cred")]


class AuthenticationManager:
    """Manages authentication flows and credential lifecycle."""

    def __init__(self, config: AuthConfig, credential_store: CredentialStore | None = None):
        self.config = config
        self.credential_store = credential_store or FileCredentialStore()
        self._current_credentials: Credentials | None = None
        self._service_cache: dict[str, Any] = {}

    def authenticate(self, force_refresh: bool = False) -> Credentials:
        """Authenticate and return valid credentials."""
        if not force_refresh and self._current_credentials and self._current_credentials.valid:
            return self._current_credentials

        # Try to load existing credentials
        stored_creds = self.credential_store.load_credentials(self.config.token_file)
        if stored_creds and not force_refresh:
            try:
                creds = Credentials.from_authorized_user_info(stored_creds, self.config.scopes)
                if creds.valid:
                    self._current_credentials = creds
                    return creds
                elif creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    self._save_credentials(creds)
                    self._current_credentials = creds
                    return creds
            except Exception as e:
                logger.warning(f"Failed to use stored credentials: {e}")

        # Perform new authentication flow
        if self.config.provider == AuthProvider.GOOGLE_OAUTH:
            return self._authenticate_oauth()
        else:
            raise ValueError(f"Unsupported auth provider: {self.config.provider}")

    def _authenticate_oauth(self) -> Credentials:
        """Perform OAuth 2.0 authentication flow."""
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.config.credentials_file, self.config.scopes
            )

            creds = flow.run_local_server(port=0)
            self._save_credentials(creds)
            self._current_credentials = creds

            logger.info("OAuth authentication completed successfully")
            return creds
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            raise

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to storage."""
        try:
            creds_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
            }
            self.credential_store.store_credentials(self.config.token_file, creds_data)
            logger.debug("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def get_service(self, service_name: str, version: str, force_refresh: bool = False) -> Any:
        """Get authenticated Google API service."""
        cache_key = f"{service_name}_{version}"

        if not force_refresh and cache_key in self._service_cache:
            return self._service_cache[cache_key]

        try:
            creds = self.authenticate(force_refresh)
            service = build(service_name, version, credentials=creds)
            self._service_cache[cache_key] = service

            logger.debug(f"Created {service_name} v{version} service")
            return service
        except Exception as e:
            logger.error(f"Failed to create {service_name} service: {e}")
            raise

    def refresh_credentials(self) -> Credentials:
        """Force refresh of credentials."""
        return self.authenticate(force_refresh=True)

    def revoke_credentials(self) -> None:
        """Revoke and delete stored credentials."""
        try:
            if self._current_credentials:
                # Try to revoke the token
                try:
                    self._current_credentials.revoke(Request())
                    logger.info("Credentials revoked successfully")
                except Exception as e:
                    logger.warning(f"Failed to revoke credentials: {e}")

            # Delete stored credentials
            self.credential_store.delete_credentials(self.config.token_file)

            # Clear cache
            self._current_credentials = None
            self._service_cache.clear()

            logger.info("Credentials cleared successfully")
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")

    def get_token_info(self) -> TokenInfo | None:
        """Get information about current token."""
        if not self._current_credentials:
            return None

        return TokenInfo(
            access_token=self._current_credentials.token,
            refresh_token=self._current_credentials.refresh_token,
            expires_at=self._current_credentials.expiry,
            scopes=list(self._current_credentials.scopes or []),
            token_type="Bearer",
        )

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self._current_credentials is not None and self._current_credentials.valid

    def validate_scopes(self, required_scopes: list[str]) -> bool:
        """Validate that current credentials have required scopes."""
        if not self._current_credentials or not self._current_credentials.scopes:
            return False

        current_scopes = set(self._current_credentials.scopes)
        required_scopes_set = set(required_scopes)

        return required_scopes_set.issubset(current_scopes)


class AuthenticationFactory:
    """Factory for creating authentication managers."""

    @staticmethod
    def create_gmail_auth(
        credentials_file: str = "credentials.json",
        token_file: str = "token.json",
        credential_store: CredentialStore | None = None,
    ) -> AuthenticationManager:
        """Create authentication manager for Gmail API."""
        config = AuthConfig(
            provider=AuthProvider.GOOGLE_OAUTH,
            credentials_file=credentials_file,
            token_file=token_file,
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.labels",
            ],
        )

        return AuthenticationManager(config, credential_store)

    @staticmethod
    def create_custom_auth(
        provider: AuthProvider,
        credentials_file: str,
        token_file: str,
        scopes: list[str],
        credential_store: CredentialStore | None = None,
    ) -> AuthenticationManager:
        """Create custom authentication manager."""
        config = AuthConfig(
            provider=provider,
            credentials_file=credentials_file,
            token_file=token_file,
            scopes=scopes,
        )

        return AuthenticationManager(config, credential_store)


# Global authentication manager instance
_default_auth_manager: AuthenticationManager | None = None


def get_auth_manager() -> AuthenticationManager:
    """Get the default authentication manager."""
    global _default_auth_manager
    if _default_auth_manager is None:
        _default_auth_manager = AuthenticationFactory.create_gmail_auth()
    return _default_auth_manager


def authenticate() -> Credentials:
    """Authenticate using default manager."""
    return get_auth_manager().authenticate()


def get_gmail_service():
    """Get authenticated Gmail service."""
    return get_auth_manager().get_service("gmail", "v1")


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return get_auth_manager().is_authenticated()


def revoke_authentication() -> None:
    """Revoke current authentication."""
    get_auth_manager().revoke_credentials()


# Backward compatibility function
def build_service():
    """Build Gmail service (backward compatible)."""
    return get_gmail_service()
