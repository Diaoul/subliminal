# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Subliminal.  If not, see <http://www.gnu.org/licenses/>.
import logging
import re
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass


__all__ = ['PluginConfig', 'get_keywords', 'split_keyword', 'NullHandler']


class PluginConfig(object):
    def __init__(self, multi=None, cache_dir=None, filemode=None):
        self.multi = multi
        self.cache_dir = cache_dir
        self.filemode = filemode


def get_keywords(guess):
    keywords = set()
    for k in ['releaseGroup', 'screenSize', 'videoCodec', 'format']:
        if k in guess:
            keywords = keywords | split_keyword(guess[k].lower())
    return keywords


def split_keyword(keyword):
    split = set(re.findall(r'\w+', keyword))
    return split
