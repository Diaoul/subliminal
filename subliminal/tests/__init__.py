#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TextTestRunner, TestSuite
from subliminal import cache_region
from . import test_providers, test_subliminal


cache_region.configure('dogpile.cache.memory', expiration_time=60 * 30)  # @UndefinedVariable
suite = TestSuite([test_providers.suite(), test_subliminal.suite()])


if __name__ == '__main__':
    TextTestRunner().run(suite)
