"""
Authentication handlers for Google Sheets API.

Supports Service Account and OAuth2 authentication methods.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class GoogleSheetsAuthenticator(ABC):
    """Abstract base class for Google Sheets authentication."""

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    @abstractmethod
    def get_credentials(self) -> Credentials:
        """
        Get Google API credentials.

        Returns:
            Credentials object for Google API authentication.

        Raises:
            AuthenticationError: If authentication fails.
        """
        pass

    @abstractmethod
    def refresh_credentials(self) -> Credentials:
        """
        Refresh expired credentials.

        Returns:
            Refreshed Credentials object.

        Raises:
            AuthenticationError: If refresh fails.
        """
        pass

    def validate(self) -> bool:
        """
        Validate that credentials can be obtained.

        Returns:
            True if credentials are valid.

        Raises:
            AuthenticationError: If validation fails.
        """
        try:
            creds = self.get_credentials()
            return creds is not None and creds.valid
        except Exception as e:
            raise AuthenticationError(
                f"Credential validation failed: {str(e)}",
                {"error_type": type(e).__name__},
            )


class ServiceAccountAuth(GoogleSheetsAuthenticator):
    """
    Service Account authentication for Google Sheets API.

    This is the recommended authentication method for automated/server-side
    applications. Requires sharing the spreadsheet with the service account email.
    """

    def __init__(
        self,
        service_account_info: Optional[Dict[str, Any]] = None,
        service_account_file: Optional[str] = None,
    ):
        """
        Initialize Service Account authentication.

        Args:
            service_account_info: Service account credentials as a dictionary.
            service_account_file: Path to the service account JSON key file.

        Raises:
            AuthenticationError: If neither credentials source is provided.
        """
        if not service_account_info and not service_account_file:
            raise AuthenticationError(
                "Must provide either service_account_info or service_account_file"
            )

        self._service_account_info = service_account_info
        self._service_account_file = service_account_file
        self._credentials: Optional[Credentials] = None

    def get_credentials(self) -> Credentials:
        """
        Get Service Account credentials.

        Returns:
            Service Account Credentials object.

        Raises:
            AuthenticationError: If credential creation fails.
        """
        if self._credentials is not None and self._credentials.valid:
            return self._credentials

        try:
            if self._service_account_info:
                self._credentials = (
                    service_account.Credentials.from_service_account_info(
                        self._service_account_info, scopes=self.SCOPES
                    )
                )
            elif self._service_account_file:
                self._credentials = (
                    service_account.Credentials.from_service_account_file(
                        self._service_account_file, scopes=self.SCOPES
                    )
                )

            return self._credentials

        except json.JSONDecodeError as e:
            raise AuthenticationError(
                "Invalid service account JSON format",
                {"error": str(e)},
            )
        except Exception as e:
            raise AuthenticationError(
                f"Failed to create service account credentials: {str(e)}",
                {"error_type": type(e).__name__},
            )

    def refresh_credentials(self) -> Credentials:
        """
        Refresh Service Account credentials.

        Service Account credentials are automatically refreshed by the Google
        auth library, so this method simply ensures we have valid credentials.

        Returns:
            Refreshed Credentials object.
        """
        if self._credentials is None:
            return self.get_credentials()

        if self._credentials.expired:
            self._credentials.refresh(Request())

        return self._credentials

    @property
    def service_account_email(self) -> Optional[str]:
        """
        Get the service account email address.

        Returns:
            The service account email if credentials are loaded, None otherwise.
        """
        if self._credentials:
            return self._credentials.service_account_email
        return None


class OAuth2Auth(GoogleSheetsAuthenticator):
    """
    OAuth2 authentication for Google Sheets API.

    Best for accessing user's personal spreadsheets with delegated access.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        access_token: Optional[str] = None,
    ):
        """
        Initialize OAuth2 authentication.

        Args:
            client_id: OAuth2 client ID.
            client_secret: OAuth2 client secret.
            refresh_token: OAuth2 refresh token.
            access_token: Optional existing access token.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token = access_token
        self._credentials: Optional[Credentials] = None

    def get_credentials(self) -> Credentials:
        """
        Get OAuth2 credentials.

        Returns:
            OAuth2 Credentials object.

        Raises:
            AuthenticationError: If credential creation fails.
        """
        if self._credentials is not None and self._credentials.valid:
            return self._credentials

        try:
            token_info = {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            }

            if self._access_token:
                token_info["token"] = self._access_token

            self._credentials = Credentials.from_authorized_user_info(
                token_info, scopes=self.SCOPES
            )

            # Refresh if expired or no access token
            if self._credentials.expired or not self._credentials.token:
                self._credentials.refresh(Request())

            return self._credentials

        except Exception as e:
            raise AuthenticationError(
                f"Failed to create OAuth2 credentials: {str(e)}",
                {"error_type": type(e).__name__},
            )

    def refresh_credentials(self) -> Credentials:
        """
        Refresh OAuth2 credentials.

        Returns:
            Refreshed Credentials object.

        Raises:
            AuthenticationError: If refresh fails.
        """
        if self._credentials is None:
            return self.get_credentials()

        try:
            if self._credentials.expired and self._credentials.refresh_token:
                self._credentials.refresh(Request())
            return self._credentials
        except Exception as e:
            raise AuthenticationError(
                f"Failed to refresh OAuth2 credentials: {str(e)}",
                {"error_type": type(e).__name__},
            )


def create_authenticator(
    auth_type: str, credentials: Dict[str, Any]
) -> GoogleSheetsAuthenticator:
    """
    Factory function to create the appropriate authenticator.

    Args:
        auth_type: Type of authentication ("service_account" or "oauth2").
        credentials: Dictionary containing authentication credentials.

    Returns:
        Appropriate GoogleSheetsAuthenticator instance.

    Raises:
        AuthenticationError: If auth_type is unknown or credentials are invalid.
    """
    if auth_type == "service_account":
        service_account_info = credentials.get("service_account_info")
        service_account_file = credentials.get("service_account_file")

        # Handle string JSON
        if isinstance(service_account_info, str):
            try:
                service_account_info = json.loads(service_account_info)
            except json.JSONDecodeError as e:
                raise AuthenticationError(
                    f"Invalid service account JSON: {str(e)}"
                )

        return ServiceAccountAuth(
            service_account_info=service_account_info,
            service_account_file=service_account_file,
        )

    elif auth_type == "oauth2":
        required_fields = ["client_id", "client_secret", "refresh_token"]
        missing = [f for f in required_fields if not credentials.get(f)]
        if missing:
            raise AuthenticationError(
                f"Missing required OAuth2 fields: {', '.join(missing)}"
            )

        return OAuth2Auth(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            refresh_token=credentials["refresh_token"],
            access_token=credentials.get("access_token"),
        )

    else:
        raise AuthenticationError(
            f"Unknown authentication type: {auth_type}",
            {"supported_types": ["service_account", "oauth2"]},
        )
