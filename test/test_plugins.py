#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import unittest
import logging
import os


logging.basicConfig(level=logging.DEBUG, format='%(name)-24s %(levelname)-8s %(message)s')
test_folder = u'/your/path/here/videos/'
test_file = u'/your/path/here/videos/the.big.bang.theory.s04e01.hdtv.xvid-fqm.avi'
cache_dir = u'/tmp/sublicache'
if not os.path.exists(cache_dir):
    os.mkdir(cache_dir)


class Addic7edTestCase(unittest.TestCase):
    def setUp(self):
        from subliminal.plugins import Addic7ed
        self.config = {'multi': True, 'cache_dir': cache_dir, 'files_mode': -1}
        self.plugin = Addic7ed(self.config)
        self.languages = set(['en', 'fr'])

    def test_list(self):
        list = self.plugin.list(test_file, self.languages)
        assert list

    def test_download(self):
        subtitle = self.plugin.list(test_file, self.languages)[0]
        if os.path.exists(subtitle.path):
            os.remove(subtitle.path)
        download = self.plugin.download(subtitle)
        assert download


class BierDopjeTestCase(unittest.TestCase):
    def setUp(self):
        from subliminal.plugins import BierDopje
        self.config = {'multi': True, 'cache_dir': cache_dir, 'files_mode': -1}
        self.plugin = BierDopje(self.config)
        self.languages = set(['en', 'fr'])

    def test_list(self):
        list = self.plugin.list(test_file, self.languages)
        assert list

    def test_download(self):
        subtitle = self.plugin.list(test_file, self.languages)[0]
        if os.path.exists(subtitle.path):
            os.remove(subtitle.path)
        download = self.plugin.download(subtitle)
        assert download


class OpenSubtitlesTestCase(unittest.TestCase):
    def setUp(self):
        from subliminal.plugins import OpenSubtitles
        self.config = {'multi': True, 'cache_dir': cache_dir, 'files_mode': -1}
        self.plugin = OpenSubtitles(self.config)
        self.languages = set(['en', 'fr'])

    def test_list(self):
        list = self.plugin.list(test_file, self.languages)
        assert list

    def test_download(self):
        subtitle = self.plugin.list(test_file, self.languages)[0]
        if os.path.exists(subtitle.path):
            os.remove(subtitle.path)
        download = self.plugin.download(subtitle)
        assert download


class SubsWikiTestCase(unittest.TestCase):
    def setUp(self):
        from subliminal.plugins import SubsWiki
        self.config = {'multi': True, 'cache_dir': cache_dir, 'files_mode': -1}
        self.plugin = SubsWiki(self.config)
        self.languages = set(['en', 'fr', 'es', 'pt'])

    def test_list(self):
        list = self.plugin.list(test_file, self.languages)
        assert list

    def test_download(self):
        subtitle = self.plugin.list(test_file, self.languages)[0]
        if os.path.exists(subtitle.path):
            os.remove(subtitle.path)
        download = self.plugin.download(subtitle)
        assert download


class SubtitulosTestCase(unittest.TestCase):
    def setUp(self):
        from subliminal.plugins import Subtitulos
        self.config = {'multi': True, 'cache_dir': cache_dir, 'files_mode': -1}
        self.plugin = Subtitulos(self.config)
        self.languages = set(['en', 'fr', 'es', 'pt'])

    def test_list(self):
        list = self.plugin.list(test_file, self.languages)
        assert list

    def test_download(self):
        subtitle = self.plugin.list(test_file, self.languages)[0]
        if os.path.exists(subtitle.path):
            os.remove(subtitle.path)
        download = self.plugin.download(subtitle)
        assert download


class TheSubDBTestCase(unittest.TestCase):
    def setUp(self):
        from subliminal.plugins import TheSubDB
        self.config = {'multi': True, 'cache_dir': cache_dir, 'files_mode': -1}
        self.plugin = TheSubDB(self.config)
        self.languages = set(['en', 'fr', 'es', 'pt'])

    def test_list(self):
        list = self.plugin.list(test_file, self.languages)
        assert list

    def test_download(self):
        subtitle = self.plugin.list(test_file, self.languages)[0]
        if os.path.exists(subtitle.path):
            os.remove(subtitle.path)
        download = self.plugin.download(subtitle)
        assert download


if __name__ == "__main__":
    unittest.main()

