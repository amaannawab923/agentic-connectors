"""
Authentication module for the Notion source connector.

This module handles authentication with the Notion API, supporting both
internal integration tokens and OAuth 2.0 authentication methods.
"""

import base64
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests

from .config import TokenCredentials, OAuth2Credentials, NotionConfig
from .utils import NotionAuthenticationError

logger = logging.getLogger(__name__)


# =============================================================================
# Base Authenticator
# =============================================================================


class NotionAuthenticator(ABC):
    """
    Abstract base class for Notion authentication handlers.

    All authentication methods must implement the get_auth_headers method
    to provide the necessary headers for API requests.
    """

    NOTION_VERSION = "2022-06-28"
    BASE_URL = "https://api.notion.com/v1"

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Returns:
            Dictionary of HTTP headers for authentication
        """
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        """
        Check if the current authentication is valid.

        Returns:
            True if authentication is valid, False otherwise
        """
        pass

    @abstractmethod
    def refresh_if_needed(self) -> bool:
        """
        Refresh authentication if needed.

        Returns:
            True if refresh was successful or not needed, False otherwise
        """
        pass

    def get_base_headers(self) -> Dict[str, str]:
        """
        Get base headers required for all Notion API requests.

        Returns:
            Dictionary of base HTTP headers
        """
        return {
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }


# =============================================================================
# Token Authentication (Internal Integration)
# =============================================================================


class TokenAuthenticator(NotionAuthenticator):
    """
    Authentication handler for internal integration tokens.

    Internal integration tokens are static tokens that don't expire and
    are used for single-workspace integrations.
    """

    def __init__(self, credentials: TokenCredentials):
        """
        Initialize token authentication.

        Args:
            credentials: TokenCredentials with the token
        """
        self.token = credentials.token
        self._validated = False

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers with Bearer token.

        Returns:
            Dictionary of HTTP headers including Authorization
        """
        headers = self.get_base_headers()
        headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def is_valid(self) -> bool:
        """
        Check if the token is valid by making a test request.

        Returns:
            True if token is valid, False otherwise
        """
        if self._validated:
            return True

        try:
            response = requests.get(
                f"{self.BASE_URL}/users/me",
                headers=self.get_auth_headers(),
                timeout=30,
            )
            self._validated = response.ok
            return self._validated
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False

    def refresh_if_needed(self) -> bool:
        """
        Internal tokens don't expire, so no refresh is needed.

        Returns:
            Always True
        """
        return True

    def get_bot_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated bot.

        Returns:
            Bot user information from Notion API

        Raises:
            NotionAuthenticationError: If the request fails
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/users/me",
                headers=self.get_auth_headers(),
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            raise NotionAuthenticationError(
                f"Failed to get bot info: {e}",
                status_code=e.response.status_code if e.response else None,
            )


# =============================================================================
# OAuth 2.0 Authentication
# =============================================================================


class OAuth2Authenticator(NotionAuthenticator):
    """
    Authentication handler for OAuth 2.0.

    OAuth 2.0 is used for public integrations that access multiple
    users' workspaces. Access tokens may expire and need refresh.
    """

    TOKEN_URL = "https://api.notion.com/v1/oauth/token"
    AUTH_URL = "https://api.notion.com/v1/oauth/authorize"

    def __init__(self, credentials: OAuth2Credentials):
        """
        Initialize OAuth 2.0 authentication.

        Args:
            credentials: OAuth2Credentials with tokens and client info
        """
        self.client_id = credentials.client_id
        self.client_secret = credentials.client_secret
        self.access_token = credentials.access_token
        self.refresh_token = credentials.refresh_token
        self.token_expiry = credentials.token_expiry
        self._validated = False

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers with OAuth access token.

        Returns:
            Dictionary of HTTP headers including Authorization
        """
        headers = self.get_base_headers()
        headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def is_valid(self) -> bool:
        """
        Check if the access token is valid.

        Returns:
            True if token is valid and not expired, False otherwise
        """
        # Check expiry if available
        if self.token_expiry:
            if datetime.utcnow() >= self.token_expiry:
                logger.warning("OAuth access token has expired")
                return False

        if self._validated:
            return True

        # Validate with API call
        try:
            response = requests.get(
                f"{self.BASE_URL}/users/me",
                headers=self.get_auth_headers(),
                timeout=30,
            )
            self._validated = response.ok
            return self._validated
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False

    def refresh_if_needed(self) -> bool:
        """
        Refresh the access token if it's expired or about to expire.

        Note: Notion's OAuth tokens currently don't expire, but this
        implementation is ready for if they add token expiration.

        Returns:
            True if refresh was successful or not needed
        """
        if not self.token_expiry:
            return True

        # Refresh if token expires within 5 minutes
        if datetime.utcnow() + timedelta(minutes=5) < self.token_expiry:
            return True

        if not self.refresh_token:
            logger.warning("Token expired but no refresh token available")
            return False

        return self._refresh_token()

    def _refresh_token(self) -> bool:
        """
        Perform token refresh.

        Returns:
            True if refresh was successful
        """
        try:
            # Create Basic auth header
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            response = requests.post(
                self.TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json",
                },
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]

            if "refresh_token" in data:
                self.refresh_token = data["refresh_token"]

            if "expires_in" in data:
                self.token_expiry = datetime.utcnow() + timedelta(
                    seconds=data["expires_in"]
                )

            self._validated = True
            logger.info("Successfully refreshed OAuth token")
            return True

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False

    @classmethod
    def exchange_code(
        cls,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> OAuth2Credentials:
        """
        Exchange an authorization code for tokens.

        This is used in the OAuth flow after the user authorizes the app.

        Args:
            code: Authorization code from Notion
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Redirect URI used in authorization

        Returns:
            OAuth2Credentials with the tokens

        Raises:
            NotionAuthenticationError: If the exchange fails
        """
        try:
            # Create Basic auth header
            auth_string = f"{client_id}:{client_secret}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            response = requests.post(
                cls.TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json",
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # Calculate token expiry if provided
            token_expiry = None
            if "expires_in" in data:
                token_expiry = datetime.utcnow() + timedelta(
                    seconds=data["expires_in"]
                )

            return OAuth2Credentials(
                auth_type="oauth2",
                client_id=client_id,
                client_secret=client_secret,
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_expiry=token_expiry,
            )

        except requests.HTTPError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass

            raise NotionAuthenticationError(
                f"Code exchange failed: {error_data.get('error_description', str(e))}",
                status_code=e.response.status_code if e.response else None,
                code=error_data.get("error"),
            )

    @classmethod
    def get_authorization_url(
        cls,
        client_id: str,
        redirect_uri: str,
        state: Optional[str] = None,
        owner: str = "user",
    ) -> str:
        """
        Generate the OAuth authorization URL.

        Args:
            client_id: OAuth client ID
            redirect_uri: Where to redirect after authorization
            state: Optional state parameter for CSRF protection
            owner: Owner type ('user' or 'workspace')

        Returns:
            Authorization URL string
        """
        from urllib.parse import urlencode

        params = {
            "client_id": client_id,
            "response_type": "code",
            "owner": owner,
            "redirect_uri": redirect_uri,
        }

        if state:
            params["state"] = state

        return f"{cls.AUTH_URL}?{urlencode(params)}"


# =============================================================================
# Factory Function
# =============================================================================


def create_authenticator(config: NotionConfig) -> NotionAuthenticator:
    """
    Create the appropriate authenticator based on configuration.

    Args:
        config: NotionConfig with credentials

    Returns:
        Appropriate NotionAuthenticator instance

    Raises:
        ValueError: If credential type is not supported
    """
    credentials = config.credentials

    if isinstance(credentials, TokenCredentials):
        return TokenAuthenticator(credentials)
    elif isinstance(credentials, OAuth2Credentials):
        return OAuth2Authenticator(credentials)
    else:
        raise ValueError(f"Unsupported credential type: {type(credentials)}")
