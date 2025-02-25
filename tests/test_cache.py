from unittest.mock import Mock

import pytest
from dogpile.cache import make_region

# A Mock version is already provided in conftest.py so no need to configure it again
from subliminal.cache import region as region_custom

# Core test
pytestmark = pytest.mark.core

# Configure default dogpile cache
region_dogpile = make_region()
region_dogpile.configure('dogpile.cache.null')
region_dogpile.configure = Mock()  # type: ignore[method-assign]


str_object = 'The Simpsons-S12E09-HOMЯ'
bytes_object = b'The Simpsons-S12E09-HOM\xd0\xaf'
namespace = 'namespace'
expected_key = 'tests.test_cache:fn|namespace|The Simpsons-S12E09-HOMЯ'  # Key is expected as native string


def fn() -> None:
    pass


def test_dogpile_cache_key_generator_unicode_string() -> None:
    key = region_dogpile.function_key_generator(namespace, fn)(str_object)
    assert key == expected_key
    assert isinstance(key, str)


def test_dogpile_cache_key_generator_byte_string() -> None:
    key = region_dogpile.function_key_generator(namespace, fn)(bytes_object)
    assert key == 'tests.test_cache:fn|namespace|' + str(b'The Simpsons-S12E09-HOM\xd0\xaf')
    assert key != expected_key  # Key is not as expected
    assert isinstance(key, str)


def test_custom_cache_key_generator_unicode_string() -> None:
    key = region_custom.function_key_generator(namespace, fn)(str_object)
    assert key == expected_key
    assert isinstance(key, str)


def test_custom_cache_key_generator_byte_string() -> None:
    key = region_custom.function_key_generator(namespace, fn)(bytes_object)
    assert key == expected_key
    assert isinstance(key, str)
