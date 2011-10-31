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
from subliminal import videos
from subliminal.exceptions import *
from subliminal.subtitles import Subtitle


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


class BierDopjeTestCase(unittest.TestCase):
    query_tests = ['test_query_series', 'test_query_bad_series', 'test_query_wrong_languages',
                   'test_query_tvdbid', 'test_query_wrong_tvdbid', 'test_query_series_and_tvdbid']
    list_tests = ['test_list_episode', 'test_list_movie', 'test_list_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        self.config = PluginConfig(multi=True, cache_dir=cache_dir)
        self.episode_path = u'The Big Bang Theory/Season 05/S05E06 - The Rhinitis Revelation - HD TV.mkv'
        self.movie_path = u'Inception (2010)/Inception - 1080p.mkv'
        self.languages = set(['en', 'nl'])
        self.wrong_languages = set(['zz', 'es'])
        self.fake_file = u'/tmp/fake_file'
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6
        self.tvdbid = 80379
        self.wrong_tvdbid = 9999999999

    def test_query_series(self):
        with BierDopje(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) > 0)

    def test_query_bad_series(self):
        with BierDopje(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, series=self.wrong_series)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with BierDopje(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.wrong_languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) == 0)

    def test_query_tvdbid(self):
        with BierDopje(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_series_and_tvdbid(self):
        with BierDopje(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, series=self.series, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_tvdbid(self):
        with BierDopje(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.wrong_tvdbid)
        self.assertTrue(len(results) == 0)

    def test_list_episode(self):
        episode = videos.factory(self.episode_path)
        with BierDopje(self.config) as plugin:
            results = plugin.list(episode, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_movie(self):
        movie = videos.factory(self.movie_path)
        with BierDopje(self.config) as plugin:
            results = plugin.list(movie, self.languages)
        self.assertTrue(len(results) == 0)

    def test_list_wrong_languages(self):
        episode = videos.factory(self.episode_path)
        with BierDopje(self.config) as plugin:
            results = plugin.list(episode, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        episode = videos.factory(self.episode_path)
        with BierDopje(self.config) as plugin:
            subtitle = plugin.list(episode, self.languages)[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            result = plugin.download(subtitle)
        self.assertTrue(isinstance(result, Subtitle))
        self.assertTrue(os.path.exists(subtitle.path))


class OpenSubtitlesTestCase(unittest.TestCase):
    query_tests = ['test_query_series', 'test_query_bad_series', 'test_query_wrong_languages',
                   'test_query_tvdbid', 'test_query_wrong_tvdbid', 'test_query_series_and_tvdbid']
    list_tests = ['test_list_episode', 'test_list_movie', 'test_list_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        self.config = PluginConfig(multi=True, cache_dir=cache_dir)
        self.episode_path = u'The Big Bang Theory/Season 05/S05E06 - The Rhinitis Revelation - HD TV.mkv'
        self.movie_path = u'Inception (2010)/Inception - 1080p.mkv'
        self.existing_episode_path = u'The Big Bang Theory/Season 05/S05E06 - The Rhinitis Revelation - HD TV.mkv'
        self.existing_movie_path = u'Inception (2010)/Inception - 1080p.mkv'
        self.languages = set(['en', 'fr'])
        self.wrong_languages = set(['zz', 'yy'])
        self.fake_file = u'/tmp/fake_file'
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6
        self.tvdbid = 80379
        self.wrong_tvdbid = 9999999999

    def test_query_(self):
        with OpenSubtitles(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) > 0)

    def test_query_bad_series(self):
        with OpenSubtitles(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, series=self.wrong_series)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with OpenSubtitles(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.wrong_languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) == 0)

    def test_query_tvdbid(self):
        with OpenSubtitles(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_series_and_tvdbid(self):
        with OpenSubtitles(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, series=self.series, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_tvdbid(self):
        with OpenSubtitles(self.config) as plugin:
            results = plugin.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.wrong_tvdbid)
        self.assertTrue(len(results) == 0)

    def test_list_episode(self):
        episode = videos.factory(self.episode_path)
        with OpenSubtitles(self.config) as plugin:
            results = plugin.list(episode, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_movie(self):
        movie = videos.factory(self.movie_path)
        with OpenSubtitles(self.config) as plugin:
            results = plugin.list(movie, self.languages)
        self.assertTrue(len(results) == 0)

    def test_list_wrong_languages(self):
        episode = videos.factory(self.episode_path)
        with OpenSubtitles(self.config) as plugin:
            results = plugin.list(episode, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        with OpenSubtitles(self.config) as plugin:
            subtitle = plugin.list(self.episode_path, self.languages)[0]
            result = plugin.download(subtitle)
        self.assertTrue(len(results) == 1)


class TheSubDBTestCase(unittest.TestCase):
    query_tests = ['test_query', 'test_query_wrong_hash', 'test_query_wrong_languages']
    list_tests = ['test_list', 'test_list_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        TheSubDB.server_url = 'http://sandbox.thesubdb.com/'
        self.config = PluginConfig(multi=True, cache_dir=cache_dir)
        self.path = u'justified.mp4'
        self.hash = u'edc1981d6459c6111fe36205b4aff6c2'
        self.wrong_hash = u'ffffffffffffffffffffffffffffffff'
        self.languages = set(['en', 'nl'])
        self.wrong_languages = set(['zz', 'cs'])
        self.fake_file = u'/tmp/fake_file'

    def test_query(self):
        with TheSubDB(self.config) as plugin:
            results = plugin.query(self.fake_file, self.hash, self.languages)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_hash(self):
        with TheSubDB(self.config) as plugin:
            results = plugin.query(self.fake_file, self.wrong_hash, self.languages)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with TheSubDB(self.config) as plugin:
            results = plugin.query(self.fake_file, self.hash, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_list(self):
        video = videos.factory(self.path)
        with TheSubDB(self.config) as plugin:
            results = plugin.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_wrong_languages(self):
        video = videos.factory(self.path)
        with TheSubDB(self.config) as plugin:
            results = plugin.list(video, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        video = videos.factory(self.path)
        with TheSubDB(self.config) as plugin:
            subtitle = plugin.list(video, self.languages)[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            result = plugin.download(subtitle)
        self.assertTrue(isinstance(result, Subtitle))
        self.assertTrue(os.path.exists(subtitle.path))

def query_suite():
    suite = unittest.TestSuite()
    #suite.addTests(map(BierDopjeTestCase, BierDopjeTestCase.query_tests))
    #suite.addTests(map(OpenSubtitlesTestCase, OpenSubtitlesTestCase.query_tests))
    suite.addTests(map(TheSubDBTestCase, TheSubDBTestCase.query_tests))
    return suite

def list_suite():
    suite = unittest.TestSuite()
    #suite.addTests(map(BierDopjeTestCase, BierDopjeTestCase.list_tests))
    #suite.addTests(map(OpenSubtitlesTestCase, OpenSubtitlesTestCase.list_tests))
    suite.addTests(map(TheSubDBTestCase, TheSubDBTestCase.list_tests))
    return suite

def download_suite():
    suite = unittest.TestSuite()
    #suite.addTests(map(BierDopjeTestCase, BierDopjeTestCase.download_tests))
    #suite.addTests(map(OpenSubtitlesTestCase, OpenSubtitlesTestCase.download_tests))
    suite.addTests(map(TheSubDBTestCase, TheSubDBTestCase.download_tests))
    return suite

if __name__ == '__main__':
    #unittest.TextTestRunner(verbosity=2).run(query_suite())
    #unittest.TextTestRunner(verbosity=2).run(list_suite())
    unittest.TextTestRunner(verbosity=2).run(download_suite())

