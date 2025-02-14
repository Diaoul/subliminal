"""Exceptions for Subliminal."""


class Error(Exception):
    """Base class for exceptions in subliminal."""

    pass


class ArchiveError(Error):
    """Exception raised by reading an archive."""

    pass


class ProviderError(Error):
    """Exception raised by providers."""

    pass


class NotInitializedProviderError(ProviderError):
    """Exception raised by providers when not initialized."""

    pass


class ConfigurationError(ProviderError):
    """Exception raised by providers when badly configured."""

    pass


class AuthenticationError(ProviderError):
    """Exception raised by providers when authentication failed."""

    pass


class ServiceUnavailable(ProviderError):
    """Exception raised when status is '503 Service Unavailable'."""

    pass


class DownloadLimitExceeded(ProviderError):
    """Exception raised by providers when download limit is exceeded."""

    pass
