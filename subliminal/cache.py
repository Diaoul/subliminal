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


def _to_native_str(value):
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return str(value)


def to_native_str_key_generator(namespace, fn, to_str=_to_native_str):
    return function_key_generator(namespace, fn, to_str)


region = make_region(function_key_generator=to_native_str_key_generator)
