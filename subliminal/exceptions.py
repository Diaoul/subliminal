# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class Error(Exception):
    """Base class for exceptions in subliminal"""
    pass


class ProviderError(Error):
    """Exception raised by providers"""
    pass


class ProviderConfigurationError(ProviderError):
    """Exception raised by providers when badly configured"""
    pass


class ProviderNotAvailable(ProviderError):
    """Exception raised by providers when unavailable"""
    pass


class InvalidSubtitle(ProviderError):
    """Exception raised by providers when the downloaded subtitle is invalid"""
    pass
