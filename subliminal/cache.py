# -*- coding: utf-8 -*-
import datetime

import six
from dogpile.cache import make_region
from dogpile.cache.util import function_key_generator

#: Expiration time for show caching
SHOW_EXPIRATION_TIME = datetime.timedelta(weeks=3).total_seconds()

#: Expiration time for episode caching
EPISODE_EXPIRATION_TIME = datetime.timedelta(days=3).total_seconds()

#: Expiration time for scraper searches
REFINER_EXPIRATION_TIME = datetime.timedelta(weeks=1).total_seconds()


def _to_native_str(value):
    if six.PY2:
        # In Python 2, the native string type is bytes
        if isinstance(value, six.text_type):  # unicode for Python 2
            return value.encode('utf-8')
        else:
            return six.binary_type(value)
    else:
        # In Python 3, the native string type is unicode
        if isinstance(value, six.binary_type):  # bytes for Python 3
            return value.decode('utf-8')
        else:
            return six.text_type(value)


def to_native_str_key_generator(namespace, fn, to_str=_to_native_str):
    return function_key_generator(namespace, fn, to_str)


region = make_region(function_key_generator=to_native_str_key_generator)
