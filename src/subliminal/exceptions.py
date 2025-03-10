"""Exceptions for Subliminal."""


class Error(Exception):
    """Base class for exceptions in subliminal."""

    pass


class ArchiveError(Error):
    """Exception raised by reading an archive."""

    pass


class GuessingError(Error, ValueError):
    """ValueError raised when guessit cannot guess a video."""

    pass


class ProviderError(Error):
    """Exception raised by providers."""

    pass


class NotInitializedProviderError(ProviderError):
    """Exception raised by providers when not initialized."""

    pass


class DiscardingError(ProviderError):
    """Exception raised by providers that should lead to discard this provider."""

    pass


class ConfigurationError(DiscardingError):
    """Exception raised by providers when badly configured."""

    pass


class AuthenticationError(DiscardingError):
    """Exception raised by providers when authentication failed."""

    pass


class ServiceUnavailable(DiscardingError):
    """Exception raised when status is '503 Service Unavailable'."""

    pass


class DownloadLimitExceeded(DiscardingError):
    """Exception raised by providers when download limit is exceeded."""

    pass
