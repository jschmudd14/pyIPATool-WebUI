"""Exception hierarchy for the App Store service layer."""

from __future__ import annotations

from typing import Any, Optional


class AppStoreError(RuntimeError):
    """Base error that carries optional metadata from upstream responses."""

    def __init__(self, message: str, *, metadata: Optional[Any] = None) -> None:
        super().__init__(message)
        self.metadata = metadata


class AuthCodeRequiredError(AppStoreError):
    pass


class PasswordTokenExpiredError(AppStoreError):
    pass


class LicenseRequiredError(AppStoreError):
    pass


class TemporarilyUnavailableError(AppStoreError):
    pass


class SubscriptionRequiredError(AppStoreError):
    pass


class InvalidCredentialsError(AppStoreError):
    pass
