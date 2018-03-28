# coding=utf-8

from datetime import timedelta

import pytest
import six
from dogpile.cache import make_region

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from subliminal.cache import region

# Configure default dogpile cache
region_dogpile = make_region()
region_dogpile.configure('dogpile.cache.null')
region_dogpile.configure = Mock()

unicode_string = u'The Simpsons-S12E09-HOMЯ'
byte_string = b'The Simpsons-S12E09-HOM\xd0\xaf'


@region_dogpile.cache_on_arguments(expiration_time=timedelta(seconds=10).total_seconds())
def dogpile_cache(value):
    return value


@region.cache_on_arguments(expiration_time=timedelta(seconds=10).total_seconds())
def custom_cache(value):
    return value


def test_dogpile_cache_on_arguments_unicode_string():
    if six.PY2:
        with pytest.raises(UnicodeEncodeError):
            dogpile_cache(unicode_string)
    else:
        dogpile_cache(unicode_string)


def test_dogpile_cache_on_arguments_byte_string():
    if six.PY2:
        dogpile_cache(byte_string)
    else:
        with pytest.raises(UnicodeEncodeError):
            dogpile_cache(byte_string)


def test_custom_cache_on_arguments_unicode_string():
    custom_cache(unicode_string)


def test_custom_cache_on_arguments_byte_string():
    custom_cache(byte_string)
