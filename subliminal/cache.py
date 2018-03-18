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


def _to_byte_str(value):
    if isinstance(value, six.text_type):
        return value.encode('utf-8')
    else:
        return six.binary_type(value)


def _to_byte_str_key_generator(namespace, fn, to_str=_to_byte_str):
    return function_key_generator(namespace, fn, to_str)


region = make_region(function_key_generator=_to_byte_str_key_generator)
