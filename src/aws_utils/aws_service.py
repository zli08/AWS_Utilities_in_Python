"""
Base class for AWS service wrappers.
Provides configuration, session management, and shared utilities.
"""

import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class AWSConfig:
    """Holds AWS configuration (region, profile, etc.)."""

    def __init__(self, region_name: Optional[str] = None,
                 profile_name: Optional[str] = None,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 aws_session_token: Optional[str] = None):
        self.region_name = region_name
        self.profile_name = profile_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token

    def get_session(self) -> boto3.Session:
        """Create a boto3 session with the configured settings."""
        return boto3.Session(
            region_name=self.region_name,
            profile_name=self.profile_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token
        )


class AWSService:
    """
    Base class for all AWS service wrappers.
    Subclasses should call super().__init__() and then initialize their own client.
    """

    def __init__(self, config: Optional[AWSConfig] = None):
        self.config = config or AWSConfig()
        self.session = self.config.get_session()
        self._client = None   # To be set by subclass
        self._resource = None # Optional

    @property
    def client(self):
        """Lazily get the boto3 client for this service."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self):
        """Override in subclass to return the correct boto3 client."""
        raise NotImplementedError("Subclass must implement _create_client")

    @property
    def resource(self):
        """Lazily get the boto3 resource (if used)."""
        if self._resource is None:
            self._resource = self._create_resource()
        return self._resource

    def _create_resource(self):
        """Override in subclass if a resource is needed."""
        return None

    @staticmethod
    def _handle_error(method_name: str, error: ClientError):
        """Log a client error."""
        logger.error(f"{method_name} failed: {error}")
        # Could add more sophisticated error handling (e.g., re-raise with custom exception)