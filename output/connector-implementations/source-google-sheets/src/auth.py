"""
Authentication module for Google Sheets connector.

Supports multiple authentication methods:
- Service Account (recommended for server-to-server)
- OAuth2 (for user-delegated access)
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuth2Credentials_Google
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError, GoogleAuthError

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error
        self.message = message

    def __str__(self) -> str:
        if self.original_error:
            return f"{self.message}: {self.original_error}"
        return self.message


class GoogleSheetsAuthenticator(ABC):
    """Abstract base class for Google Sheets authentication."""

    # Required scopes for reading spreadsheets
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    def __init__(self, scopes: Optional[list[str]] = None):
        """
        Initialize authenticator with optional custom scopes.

        Args:
            scopes: List of OAuth scopes. Defaults to read-only spreadsheet access.
        """
        self.scopes = scopes or self.DEFAULT_SCOPES
        self._credentials: Optional[Any] = None

    @abstractmethod
    def authenticate(self) -> Any:
        """
        Perform authentication and return credentials.

        Returns:
            Google credentials object suitable for API client initialization.

        Raises:
            AuthenticationError: If authentication fails.
        """
        pass

    @abstractmethod
    def refresh_if_needed(self) -> bool:
        """
        Refresh credentials if expired.

        Returns:
            True if credentials were refreshed, False if still valid.

        Raises:
            AuthenticationError: If refresh fails.
        """
        pass

    @property
    def credentials(self) -> Any:
        """Get the current credentials, authenticating if needed."""
        if self._credentials is None:
            self.authenticate()
        return self._credentials

    @property
    def is_valid(self) -> bool:
        """Check if current credentials are valid."""
        if self._credentials is None:
            return False
        return self._credentials.valid


class ServiceAccountAuthenticator(GoogleSheetsAuthenticator):
    """
    Authenticator using Google Service Account credentials.

    This is the recommended authentication method for automated pipelines
    and server-to-server communication.

    Note: The spreadsheet must be shared with the service account email
    (found in the credentials JSON as 'client_email').
    """

    def __init__(
        self,
        credentials_info: Dict[str, Any],
        scopes: Optional[list[str]] = None,
    ):
        """
        Initialize with service account credentials.

        Args:
            credentials_info: Dictionary containing service account JSON key data.
                Must include 'type', 'project_id', 'private_key', 'client_email'.
            scopes: Optional list of OAuth scopes.

        Raises:
            AuthenticationError: If credentials_info is invalid.
        """
        super().__init__(scopes)
        self._validate_credentials_info(credentials_info)
        self._credentials_info = credentials_info

    @staticmethod
    def _validate_credentials_info(credentials_info: Dict[str, Any]) -> None:
        """Validate service account credentials structure."""
        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing = [f for f in required_fields if f not in credentials_info]

        if missing:
            raise AuthenticationError(
                f"Invalid service account credentials: missing fields {missing}"
            )

        if credentials_info.get("type") != "service_account":
            raise AuthenticationError(
                f"Invalid credentials type: expected 'service_account', "
                f"got '{credentials_info.get('type')}'"
            )

    @classmethod
    def from_json_file(
        cls,
        file_path: str,
        scopes: Optional[list[str]] = None,
    ) -> "ServiceAccountAuthenticator":
        """
        Create authenticator from a JSON key file.

        Args:
            file_path: Path to the service account JSON key file.
            scopes: Optional list of OAuth scopes.

        Returns:
            Configured ServiceAccountAuthenticator instance.

        Raises:
            AuthenticationError: If file cannot be read or is invalid.
        """
        try:
            with open(file_path, "r") as f:
                credentials_info = json.load(f)
            return cls(credentials_info, scopes)
        except FileNotFoundError:
            raise AuthenticationError(f"Credentials file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise AuthenticationError(f"Invalid JSON in credentials file", e)

    def authenticate(self) -> service_account.Credentials:
        """
        Authenticate using service account credentials.

        Returns:
            Google service account credentials object.

        Raises:
            AuthenticationError: If authentication fails.
        """
        try:
            self._credentials = service_account.Credentials.from_service_account_info(
                self._credentials_info,
                scopes=self.scopes,
            )
            logger.info(
                f"Authenticated as service account: "
                f"{self._credentials_info.get('client_email')}"
            )
            return self._credentials
        except ValueError as e:
            raise AuthenticationError("Failed to create service account credentials", e)

    def refresh_if_needed(self) -> bool:
        """
        Refresh credentials if expired.

        Service account credentials are automatically refreshed by the
        Google client library, but this method forces a refresh if needed.

        Returns:
            True if credentials were refreshed, False if still valid.
        """
        if self._credentials is None:
            self.authenticate()
            return True

        if not self._credentials.valid:
            try:
                self._credentials.refresh(Request())
                logger.debug("Service account credentials refreshed")
                return True
            except RefreshError as e:
                raise AuthenticationError("Failed to refresh credentials", e)

        return False

    @property
    def service_account_email(self) -> str:
        """Get the service account email address."""
        return self._credentials_info.get("client_email", "")

    @property
    def project_id(self) -> str:
        """Get the Google Cloud project ID."""
        return self._credentials_info.get("project_id", "")


class OAuth2Authenticator(GoogleSheetsAuthenticator):
    """
    Authenticator using OAuth2 credentials with refresh token.

    Use this for user-delegated access when the connector needs to
    access spreadsheets on behalf of a specific user.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        scopes: Optional[list[str]] = None,
    ):
        """
        Initialize with OAuth2 credentials.

        Args:
            client_id: OAuth2 client ID from Google Cloud Console.
            client_secret: OAuth2 client secret.
            refresh_token: Long-lived refresh token for the user.
            scopes: Optional list of OAuth scopes.
        """
        super().__init__(scopes)
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    def authenticate(self) -> OAuth2Credentials_Google:
        """
        Authenticate using OAuth2 credentials.

        Returns:
            Google OAuth2 credentials object.

        Raises:
            AuthenticationError: If authentication fails.
        """
        try:
            self._credentials = OAuth2Credentials_Google(
                token=None,  # Will be refreshed immediately
                refresh_token=self._refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self._client_id,
                client_secret=self._client_secret,
                scopes=self.scopes,
            )
            # Force initial token refresh
            self._credentials.refresh(Request())
            logger.info("OAuth2 authentication successful")
            return self._credentials
        except GoogleAuthError as e:
            raise AuthenticationError("OAuth2 authentication failed", e)

    def refresh_if_needed(self) -> bool:
        """
        Refresh OAuth2 credentials if expired.

        Returns:
            True if credentials were refreshed, False if still valid.

        Raises:
            AuthenticationError: If refresh fails.
        """
        if self._credentials is None:
            self.authenticate()
            return True

        if self._credentials.expired:
            try:
                self._credentials.refresh(Request())
                logger.debug("OAuth2 credentials refreshed")
                return True
            except RefreshError as e:
                raise AuthenticationError(
                    "Failed to refresh OAuth2 token. User may need to re-authorize.",
                    e,
                )

        return False


def create_authenticator(
    credentials_config: Dict[str, Any],
    scopes: Optional[list[str]] = None,
) -> GoogleSheetsAuthenticator:
    """
    Factory function to create the appropriate authenticator.

    Args:
        credentials_config: Dictionary containing authentication configuration.
            For service account: Include full service account JSON.
            For OAuth2: Include 'client_id', 'client_secret', 'refresh_token'.
        scopes: Optional list of OAuth scopes.

    Returns:
        Configured authenticator instance.

    Raises:
        AuthenticationError: If credentials configuration is invalid.
    """
    auth_type = credentials_config.get("auth_type", "service_account")

    if auth_type == "service_account":
        # Extract nested credentials if present
        creds = credentials_config.get("credentials", credentials_config)
        return ServiceAccountAuthenticator(creds, scopes)

    elif auth_type == "oauth2":
        required = ["client_id", "client_secret", "refresh_token"]
        missing = [f for f in required if f not in credentials_config]
        if missing:
            raise AuthenticationError(
                f"OAuth2 credentials missing required fields: {missing}"
            )
        return OAuth2Authenticator(
            client_id=credentials_config["client_id"],
            client_secret=credentials_config["client_secret"],
            refresh_token=credentials_config["refresh_token"],
            scopes=scopes,
        )

    else:
        raise AuthenticationError(
            f"Unknown authentication type: {auth_type}. "
            f"Supported types: 'service_account', 'oauth2'"
        )
