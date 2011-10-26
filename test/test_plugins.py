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
from subliminal.utils import PluginConfig
from subliminal.plugins import *


# Set up logging
logger = logging.getLogger('subliminal')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)-24s %(levelname)-8s %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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
    query_tests = ['test_query_series', 'test_query_bad_series', 'test_query_wrong_languages',
                   'test_query_tvdbid', 'test_query_wrong_tvdbid', 'test_query_series_and_tvdbid']

    def setUp(self):
        self.config = PluginConfig(multi=True, cache_dir=cache_dir)
        self.languages = ['en', 'nl']
        self.wrong_languages = ['zz', 'es']
        self.fake_file = u'/tmp/fake_file'
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6
        self.tvdbid = 80379
        self.wrong_tvdbid = 9999999999

    def test_query_series(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.query(self.season, self.episode, self.languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) > 0)

    def test_query_bad_series(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.query(self.season, self.episode, self.languages, self.fake_file, series=self.wrong_series)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.query(self.season, self.episode, self.wrong_languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) == 0)

    def test_query_tvdbid(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_series_and_tvdbid(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.query(self.season, self.episode, self.languages, self.fake_file, series=self.series, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_tvdbid(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.wrong_tvdbid)
        self.assertTrue(len(results) == 0)

    def test_list_episode(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.list(test_file, ['en', 'nl'])
        self.assertTrue(len(results) > 0)

    def test_list_episode(self):
        with BierDopje(self.config) as bierdopje:
            results = bierdopje.list(test_file, ['en', 'nl'])
        self.assertTrue(len(results) > 0)

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

def query_suite():
    suite = unittest.TestSuite()
    suite.addTests(map(BierDopjeTestCase, BierDopjeTestCase.query_tests))
    #suite.addTest(BierDopjeTestCase('test_list'))
    #suite.addTest(BierDopjeTestCase('test_download'))
    #suite.addTest(GlobalTestCase('test_list_folder'))
    #suite.addTest(GlobalTestCase('test_download_file'))
    #suite.addTest(GlobalTestCase('test_download_folder'))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(query_suite())

