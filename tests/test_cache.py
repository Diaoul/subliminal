# coding=utf-8

import pytest
import six
from dogpile.cache import make_region

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

# A Mock version is already provided in conftest.py so no need to configure it again
from subliminal.cache import region as region_custom

# Configure default dogpile cache
region_dogpile = make_region()
region_dogpile.configure('dogpile.cache.null')
region_dogpile.configure = Mock()

unicode_string = u'The Simpsons-S12E09-HOMЯ'
byte_string = b'The Simpsons-S12E09-HOM\xd0\xaf'
namespace = 'namespace'
expected_key = 'test_cache:fn|namespace|The Simpsons-S12E09-HOMЯ'  # Key is expected as native string


def fn():
    pass


def test_dogpile_cache_key_generator_unicode_string():
    if six.PY2:
        with pytest.raises(UnicodeEncodeError):
            region_dogpile.function_key_generator(namespace, fn)(unicode_string)
    else:
        key = region_dogpile.function_key_generator(namespace, fn)(unicode_string)
        assert key == expected_key
        assert isinstance(key, six.text_type)  # In Python 3, the native string type is unicode


def test_dogpile_cache_key_generator_byte_string():
    key = region_dogpile.function_key_generator(namespace, fn)(byte_string)
    if six.PY2:
        assert key == expected_key
        assert isinstance(key, six.binary_type)  # In Python 2, the native string type is bytes
    else:
        assert key == 'test_cache:fn|namespace|' + str(b'The Simpsons-S12E09-HOM\xd0\xaf')
        assert key != expected_key  # Key is not as expected
        assert isinstance(key, six.text_type)  # In Python 3, the native string type is unicode


def test_custom_cache_key_generator_unicode_string():
    key = region_custom.function_key_generator(namespace, fn)(unicode_string)
    assert key == expected_key
    if six.PY2:
        assert isinstance(key, six.binary_type)  # In Python 2, the native string type is bytes
    else:
        assert isinstance(key, six.text_type)  # In Python 3, the native string type is unicode


def test_custom_cache_key_generator_byte_string():
    key = region_custom.function_key_generator(namespace, fn)(byte_string)
    assert key == expected_key
    if six.PY2:
        assert isinstance(key, six.binary_type)  # In Python 2, the native string type is bytes
    else:
        assert isinstance(key, six.text_type)  # In Python 3, the native string type is unicode
