# coding=utf-8

import pytest

from dogpile.cache import make_region
from subliminal.cache import region

region_default = make_region()


@region_default.cache_on_arguments()
def search_default(value):
    return value


@region.cache_on_arguments()
def search(value):
    return value


def test_dogpile_cache_on_arguments_unicode_failure():
    with pytest.raises(UnicodeEncodeError):
        search_default(u'The Simpsons-S12E09-HOMЯ')


def test_dogpile_cache_on_arguments_unicode_to_native_str():
    value = u'The Simpsons-S12E09-HOMЯ'
    search(value)


def test_dogpile_cache_on_arguments_bytestring_to_native_str():
    value_bytes = b'The Simpsons-S12E09-HOM\xd0\xaf'
    search(value_bytes)
