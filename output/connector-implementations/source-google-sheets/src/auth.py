"""
Authentication handling for Google Sheets connector.

This module provides authentication support for:
- Service Account credentials
- OAuth 2.0 credentials
- API Key authentication (public sheets only)
"""

from typing import Any, Dict, Optional
import json
import time
import logging
from abc import ABC, abstractmethod

from google.oauth2.service_account import Credentials as ServiceAccountCreds
from google.oauth2.credentials import Credentials as OAuth2Creds
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource

from .config import (
    GoogleSheetsConfig,
    ServiceAccountCredentials,
    OAuth2Credentials,
    APIKeyCredentials,
    CredentialsUnion,
)
from .utils import AuthenticationError

logger = logging.getLogger(__name__)


# Google Sheets API scopes
SCOPES_READONLY = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SCOPES_FULL = ["https://www.googleapis.com/auth/spreadsheets"]
DRIVE_READONLY = ["https://www.googleapis.com/auth/drive.readonly"]


class BaseAuthenticator(ABC):
    """Abstract base class for authentication handlers."""

    @abstractmethod
    def get_credentials(self) -> Any:
        """Get authenticated credentials."""
        pass

    @abstractmethod
    def build_service(self) -> Resource:
        """Build and return the Google Sheets API service."""
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        """Check if the current credentials are valid."""
        pass

    @abstractmethod
    def refresh(self) -> None:
        """Refresh the credentials if needed."""
        pass


class ServiceAccountAuthenticator(BaseAuthenticator):
    """Authenticator for service account credentials."""

    def __init__(
        self,
        credentials: ServiceAccountCredentials,
        scopes: Optional[list] = None
    ):
        """
        Initialize service account authenticator.

        Args:
            credentials: Service account credentials configuration
            scopes: List of OAuth scopes (defaults to readonly)
        """
        self.credentials_config = credentials
        self.scopes = scopes or SCOPES_READONLY
        self._credentials: Optional[ServiceAccountCreds] = None
        self._service: Optional[Resource] = None

    def get_credentials(self) -> ServiceAccountCreds:
        """
        Get service account credentials.

        Returns:
            Google ServiceAccountCredentials object

        Raises:
            AuthenticationError: If credentials are invalid
        """
        if self._credentials is None:
            try:
                credentials_dict = self.credentials_config.get_credentials_dict()
                self._credentials = ServiceAccountCreds.from_service_account_info(
                    credentials_dict,
                    scopes=self.scopes
                )
                logger.info("Service account credentials initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize service account credentials: {e}")
                raise AuthenticationError(f"Failed to initialize credentials: {e}")

        return self._credentials

    def build_service(self) -> Resource:
        """
        Build the Google Sheets API service.

        Returns:
            Google Sheets API service resource

        Raises:
            AuthenticationError: If service cannot be built
        """
        if self._service is None:
            try:
                credentials = self.get_credentials()
                self._service = build(
                    "sheets",
                    "v4",
                    credentials=credentials,
                    cache_discovery=False
                )
                logger.info("Google Sheets API service built successfully")
            except Exception as e:
                logger.error(f"Failed to build Sheets API service: {e}")
                raise AuthenticationError(f"Failed to build service: {e}")

        return self._service

    def is_valid(self) -> bool:
        """
        Check if credentials are valid.

        Returns:
            True if credentials are valid, False otherwise
        """
        if self._credentials is None:
            return False

        return self._credentials.valid and not self._credentials.expired

    def refresh(self) -> None:
        """
        Refresh the credentials if needed.

        Service account credentials typically don't need refresh
        as they are automatically refreshed by the client library.
        """
        if self._credentials is not None and self._credentials.expired:
            try:
                self._credentials.refresh(Request())
                logger.info("Service account credentials refreshed")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                raise AuthenticationError(f"Failed to refresh credentials: {e}")


class OAuth2Authenticator(BaseAuthenticator):
    """Authenticator for OAuth 2.0 credentials."""

    TOKEN_URI = "https://oauth2.googleapis.com/token"

    def __init__(
        self,
        credentials: OAuth2Credentials,
        scopes: Optional[list] = None
    ):
        """
        Initialize OAuth2 authenticator.

        Args:
            credentials: OAuth2 credentials configuration
            scopes: List of OAuth scopes (defaults to readonly)
        """
        self.credentials_config = credentials
        self.scopes = scopes or SCOPES_READONLY
        self._credentials: Optional[OAuth2Creds] = None
        self._service: Optional[Resource] = None

    def get_credentials(self) -> OAuth2Creds:
        """
        Get OAuth2 credentials.

        Returns:
            Google OAuth2Credentials object

        Raises:
            AuthenticationError: If credentials are invalid
        """
        if self._credentials is None:
            try:
                self._credentials = OAuth2Creds(
                    token=self.credentials_config.access_token,
                    refresh_token=self.credentials_config.refresh_token,
                    client_id=self.credentials_config.client_id,
                    client_secret=self.credentials_config.client_secret,
                    token_uri=self.TOKEN_URI,
                    scopes=self.scopes
                )

                # Refresh to get valid access token if needed
                if not self._credentials.valid:
                    self.refresh()

                logger.info("OAuth2 credentials initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OAuth2 credentials: {e}")
                raise AuthenticationError(f"Failed to initialize credentials: {e}")

        return self._credentials

    def build_service(self) -> Resource:
        """
        Build the Google Sheets API service.

        Returns:
            Google Sheets API service resource

        Raises:
            AuthenticationError: If service cannot be built
        """
        if self._service is None:
            try:
                credentials = self.get_credentials()
                self._service = build(
                    "sheets",
                    "v4",
                    credentials=credentials,
                    cache_discovery=False
                )
                logger.info("Google Sheets API service built successfully")
            except Exception as e:
                logger.error(f"Failed to build Sheets API service: {e}")
                raise AuthenticationError(f"Failed to build service: {e}")

        return self._service

    def is_valid(self) -> bool:
        """
        Check if credentials are valid.

        Returns:
            True if credentials are valid, False otherwise
        """
        if self._credentials is None:
            return False

        return self._credentials.valid and not self._credentials.expired

    def refresh(self) -> None:
        """
        Refresh the OAuth2 credentials.

        Raises:
            AuthenticationError: If refresh fails
        """
        if self._credentials is not None:
            try:
                self._credentials.refresh(Request())
                logger.info("OAuth2 credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh OAuth2 credentials: {e}")
                raise AuthenticationError(f"Failed to refresh credentials: {e}")


class APIKeyAuthenticator(BaseAuthenticator):
    """Authenticator for API Key (public sheets only)."""

    def __init__(self, credentials: APIKeyCredentials):
        """
        Initialize API Key authenticator.

        Args:
            credentials: API Key credentials configuration
        """
        self.credentials_config = credentials
        self._service: Optional[Resource] = None

    def get_credentials(self) -> str:
        """
        Get API key.

        Returns:
            API key string
        """
        return self.credentials_config.api_key

    def build_service(self) -> Resource:
        """
        Build the Google Sheets API service with API key.

        Returns:
            Google Sheets API service resource

        Raises:
            AuthenticationError: If service cannot be built
        """
        if self._service is None:
            try:
                self._service = build(
                    "sheets",
                    "v4",
                    developerKey=self.credentials_config.api_key,
                    cache_discovery=False
                )
                logger.info("Google Sheets API service built with API key")
            except Exception as e:
                logger.error(f"Failed to build Sheets API service: {e}")
                raise AuthenticationError(f"Failed to build service: {e}")

        return self._service

    def is_valid(self) -> bool:
        """
        Check if API key is valid.

        API keys don't expire, so we return True.
        Actual validation happens on API call.

        Returns:
            True (API keys don't expire)
        """
        return True

    def refresh(self) -> None:
        """API keys don't need refresh."""
        pass


class GoogleSheetsAuthenticator:
    """
    Factory class for creating the appropriate authenticator.

    This class examines the credentials type and creates the
    appropriate authenticator instance.
    """

    def __init__(
        self,
        config: GoogleSheetsConfig,
        scopes: Optional[list] = None
    ):
        """
        Initialize the authenticator factory.

        Args:
            config: Google Sheets configuration
            scopes: Optional list of OAuth scopes
        """
        self.config = config
        self.scopes = scopes or SCOPES_READONLY
        self._authenticator: Optional[BaseAuthenticator] = None

    def get_authenticator(self) -> BaseAuthenticator:
        """
        Get the appropriate authenticator based on credentials type.

        Returns:
            Authenticator instance

        Raises:
            AuthenticationError: If credentials type is unknown
        """
        if self._authenticator is not None:
            return self._authenticator

        credentials = self.config.credentials

        if isinstance(credentials, ServiceAccountCredentials):
            self._authenticator = ServiceAccountAuthenticator(
                credentials,
                self.scopes
            )
        elif isinstance(credentials, OAuth2Credentials):
            self._authenticator = OAuth2Authenticator(
                credentials,
                self.scopes
            )
        elif isinstance(credentials, APIKeyCredentials):
            self._authenticator = APIKeyAuthenticator(credentials)
        else:
            raise AuthenticationError(
                f"Unknown credentials type: {type(credentials).__name__}"
            )

        return self._authenticator

    def build_service(self) -> Resource:
        """
        Build and return the Google Sheets API service.

        Returns:
            Google Sheets API service resource
        """
        authenticator = self.get_authenticator()
        return authenticator.build_service()

    def is_valid(self) -> bool:
        """
        Check if current credentials are valid.

        Returns:
            True if credentials are valid
        """
        if self._authenticator is None:
            return False
        return self._authenticator.is_valid()

    def refresh(self) -> None:
        """Refresh credentials if needed."""
        if self._authenticator is not None:
            self._authenticator.refresh()
