"""Caching structure."""

from __future__ import annotations

import datetime

from dogpile.cache import make_region
from dogpile.cache.util import function_key_generator

#: Expiration time for show caching
SHOW_EXPIRATION_TIME = datetime.timedelta(weeks=3).total_seconds()

#: Expiration time for episode caching
EPISODE_EXPIRATION_TIME = datetime.timedelta(days=3).total_seconds()

#: Expiration time for scraper searches
REFINER_EXPIRATION_TIME = datetime.timedelta(weeks=1).total_seconds()


def _to_native_str(value: str | bytes) -> str:
    """Convert bytes to str."""
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return str(value)


def to_native_str_key_generator(namespace, fn, to_str=_to_native_str):  # type: ignore[no-untyped-def]  # noqa: ANN201, ANN001
    """Convert bytes to str, generator."""
    return function_key_generator(namespace, fn, to_str)  # type: ignore[no-untyped-call]


region = make_region(function_key_generator=to_native_str_key_generator)
