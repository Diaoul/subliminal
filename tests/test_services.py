#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from subliminal import videos
from subliminal.exceptions import MissingLanguageError, ServiceError
from subliminal.services import ServiceConfig
from subliminal.services.bierdopje import BierDopje
from subliminal.services.opensubtitles import OpenSubtitles
from subliminal.services.subswiki import SubsWiki
from subliminal.services.subtitulos import Subtitulos
from subliminal.services.thesubdb import TheSubDB
from subliminal.subtitles import Subtitle
import os
import unittest


cache_dir = u'/tmp/sublicache'
if not os.path.exists(cache_dir):
    os.mkdir(cache_dir)


class BierDopjeTestCase(unittest.TestCase):
    query_tests = ['test_query_series', 'test_query_wrong_series', 'test_query_wrong_languages',
                   'test_query_tvdbid', 'test_query_wrong_tvdbid', 'test_query_series_and_tvdbid']
    list_tests = ['test_list_episode', 'test_list_movie', 'test_list_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
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
        with BierDopje(self.config) as service:
            results = service.query(self.season, self.episode, self.languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with BierDopje(self.config) as service:
            results = service.query(self.season, self.episode, self.languages, self.fake_file, series=self.wrong_series)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with BierDopje(self.config) as service:
            results = service.query(self.season, self.episode, self.wrong_languages, self.fake_file, series=self.series)
        self.assertTrue(len(results) == 0)

    def test_query_tvdbid(self):
        with BierDopje(self.config) as service:
            results = service.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_series_and_tvdbid(self):
        with BierDopje(self.config) as service:
            results = service.query(self.season, self.episode, self.languages, self.fake_file, series=self.series, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_tvdbid(self):
        with BierDopje(self.config) as service:
            results = service.query(self.season, self.episode, self.languages, self.fake_file, tvdbid=self.wrong_tvdbid)
        self.assertTrue(len(results) == 0)

    def test_list_episode(self):
        episode = videos.Video.from_path(self.episode_path)
        with BierDopje(self.config) as service:
            results = service.list(episode, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_movie(self):
        movie = videos.Video.from_path(self.movie_path)
        with BierDopje(self.config) as service:
            results = service.list(movie, self.languages)
        self.assertTrue(len(results) == 0)

    def test_list_wrong_languages(self):
        episode = videos.Video.from_path(self.episode_path)
        with BierDopje(self.config) as service:
            results = service.list(episode, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        episode = videos.Video.from_path(self.episode_path)
        with BierDopje(self.config) as service:
            subtitle = service.list(episode, self.languages)[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            service.download(subtitle)
        self.assertTrue(os.path.exists(subtitle.path))


class OpenSubtitlesTestCase(unittest.TestCase):
    query_tests = ['test_query_query', 'test_query_imdbid', 'test_query_hash', 'test_query_wrong_languages']
    list_tests = ['test_list', 'test_list_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.languages = set(['en', 'fr'])
        self.wrong_languages = set(['zz', 'yy'])
        self.fake_file = u'/tmp/fake_file'
        self.path = u''  # replace with something existing here
        self.series = 'The Big Bang Theory'
        self.movie = 'Inception'
        self.wrong_series = 'No Existent Show Name'
        self.imdbid = 'tt1375666'
        self.wrong_imdbid = 'tt9999999'
        self.hash = '51e57c4e8fd77990'
        self.size = 882571264L

    def test_query_query(self):
        with OpenSubtitles(self.config) as service:
            results = service.query(self.fake_file, self.languages, query=self.movie)
        self.assertTrue(len(results) > 0)

    def test_query_imdbid(self):
        with OpenSubtitles(self.config) as service:
            results = service.query(self.fake_file, self.languages, imdbid=self.imdbid)
        self.assertTrue(len(results) > 0)

    def test_query_hash(self):
        with OpenSubtitles(self.config) as service:
            results = service.query(self.fake_file, self.languages, moviehash=self.hash, size=self.size)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_languages(self):
        with OpenSubtitles(self.config) as service:
            with self.assertRaises(MissingLanguageError):
                service.query(self.fake_file, self.wrong_languages, moviehash=self.hash, size=self.size)

    def test_list(self):
        video = videos.Video.from_path(self.path)
        with OpenSubtitles(self.config) as service:
            results = service.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_wrong_languages(self):
        video = videos.Video.from_path(self.path)
        with OpenSubtitles(self.config) as service:
            results = service.list(video, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        video = videos.Video.from_path(self.path)
        with OpenSubtitles(self.config) as service:
            subtitle = service.list(video, self.languages)[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            result = service.download(subtitle)
        self.assertTrue(isinstance(result, Subtitle))
        self.assertTrue(os.path.exists(subtitle.path))


class TheSubDBTestCase(unittest.TestCase):
    query_tests = ['test_query', 'test_query_wrong_hash', 'test_query_wrong_languages']
    list_tests = ['test_list', 'test_list_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.path = u'justified.mp4'  # replace with something existing here
        self.hash = u'edc1981d6459c6111fe36205b4aff6c2'
        self.wrong_hash = u'ffffffffffffffffffffffffffffffff'
        self.languages = set(['en', 'nl'])
        self.wrong_languages = set(['zz', 'cs'])
        self.fake_file = u'/tmp/fake_file'

    def test_query(self):
        with TheSubDB(self.config) as service:
            results = service.query(self.fake_file, self.hash, self.languages)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_hash(self):
        with TheSubDB(self.config) as service:
            results = service.query(self.fake_file, self.wrong_hash, self.languages)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with TheSubDB(self.config) as service:
            results = service.query(self.fake_file, self.hash, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_list(self):
        video = videos.Video.from_path(self.path)
        with TheSubDB(self.config) as service:
            results = service.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_wrong_languages(self):
        video = videos.Video.from_path(self.path)
        with TheSubDB(self.config) as service:
            results = service.list(video, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        video = videos.Video.from_path(self.path)
        with TheSubDB(self.config) as service:
            subtitle = service.list(video, self.languages)[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            result = service.download(subtitle)
        self.assertTrue(isinstance(result, Subtitle))
        self.assertTrue(os.path.exists(subtitle.path))


class SubsWikiTestCase(unittest.TestCase):
    query_tests = ['test_query_series', 'test_query_movie', 'test_query_wrong_parameters', 'test_query_wrong_series', 'test_query_wrong_languages']
    list_tests = ['test_list_series', 'test_list_movie', 'test_list_series_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.fake_file = u'/tmp/fake_file'
        self.languages = set(['en', 'es'])
        self.wrong_languages = set(['zz', 'ay'])
        self.movie_path = u'Soul Surfer (2011)/Soul.Surfer.(2011).DVDRip.XviD-TWiZTED.mkv'
        self.movie_keywords = set(['twizted'])
        self.movie = u'Soul Surfer'
        self.movie_year = 2011
        self.series_path = u'The Big Bang Theory/Season 05/The.Big.Bang.Theory.S05E06.HDTV.XviD-ASAP.mkv'
        self.series_keywords = set(['asap', 'hdtv'])
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.series_season = 5
        self.series_episode = 6

    def test_query_series(self):
        with SubsWiki(self.config) as service:
            results = service.query(self.fake_file, self.languages, keywords=self.series_keywords, series=self.series, season=self.series_season, episode=self.series_episode)
        self.assertTrue(len(results) > 0)

    def test_query_movie(self):
        with SubsWiki(self.config) as service:
            results = service.query(self.fake_file, self.languages, keywords=self.movie_keywords, movie=self.movie, year=self.movie_year)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_parameters(self):
        with SubsWiki(self.config) as service:
            with self.assertRaises(ServiceError):
                service.query(self.fake_file, self.languages, keywords=self.movie_keywords, movie=self.movie, series=self.series)

    def test_query_wrong_series(self):
        with SubsWiki(self.config) as service:
            results = service.query(self.fake_file, self.languages, keywords=self.series_keywords, series=self.wrong_series, season=self.series_season, episode=self.series_episode)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with SubsWiki(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, keywords=self.series_keywords, series=self.series, season=self.series_season, episode=self.series_episode)
        self.assertTrue(len(results) == 0)

    def test_list_series(self):
        video = videos.Video.from_path(self.series_path)
        with SubsWiki(self.config) as service:
            results = service.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_movie(self):
        video = videos.Video.from_path(self.movie_path)
        with SubsWiki(self.config) as service:
            results = service.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_series_wrong_languages(self):
        video = videos.Video.from_path(self.series_path)
        with SubsWiki(self.config) as service:
            results = service.list(video, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        video = videos.Video.from_path(self.series_path)
        with SubsWiki(self.config) as service:
            subtitle = service.list(video, self.languages)[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            service.download(subtitle)
        self.assertTrue(os.path.exists(subtitle.path))


class SubtitulosTestCase(unittest.TestCase):
    query_tests = ['test_query', 'test_query_wrong_series', 'test_query_wrong_languages']
    list_tests = ['test_list', 'test_list_wrong_languages']
    download_tests = ['test_download']

    def setUp(self):
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.fake_file = u'/tmp/fake_file'
        self.languages = set(['en', 'es'])
        self.wrong_languages = set(['zz', 'ay'])
        self.path = u'The Big Bang Theory/Season 05/The.Big.Bang.Theory.S05E06.HDTV.XviD-ASAP.mkv'
        self.keywords = set(['asap', 'hdtv'])
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6

    def test_query(self):
        with Subtitulos(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with Subtitulos(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.keywords, self.wrong_series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with Subtitulos(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, self.keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_list(self):
        video = videos.Video.from_path(self.path)
        with Subtitulos(self.config) as service:
            results = service.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_wrong_languages(self):
        video = videos.Video.from_path(self.path)
        with Subtitulos(self.config) as service:
            results = service.list(video, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download(self):
        video = videos.Video.from_path(self.path)
        with Subtitulos(self.config) as service:
            subtitle = service.list(video, self.languages)[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            result = service.download(subtitle)
        self.assertTrue(os.path.exists(subtitle.path))


def query_suite():
    suite = unittest.TestSuite()
    suite.addTests(map(BierDopjeTestCase, BierDopjeTestCase.query_tests))
    suite.addTests(map(OpenSubtitlesTestCase, OpenSubtitlesTestCase.query_tests))
    suite.addTests(map(TheSubDBTestCase, TheSubDBTestCase.query_tests))
    suite.addTests(map(SubsWikiTestCase, SubsWikiTestCase.query_tests))
    suite.addTests(map(SubtitulosTestCase, SubtitulosTestCase.query_tests))
    return suite


def list_suite():
    suite = unittest.TestSuite()
    suite.addTests(map(BierDopjeTestCase, BierDopjeTestCase.list_tests))
    suite.addTests(map(OpenSubtitlesTestCase, OpenSubtitlesTestCase.list_tests))
    suite.addTests(map(TheSubDBTestCase, TheSubDBTestCase.list_tests))
    suite.addTests(map(SubsWikiTestCase, SubsWikiTestCase.list_tests))
    suite.addTests(map(SubtitulosTestCase, SubtitulosTestCase.list_tests))
    return suite


def download_suite():
    suite = unittest.TestSuite()
    suite.addTests(map(BierDopjeTestCase, BierDopjeTestCase.download_tests))
    suite.addTests(map(OpenSubtitlesTestCase, OpenSubtitlesTestCase.download_tests))
    suite.addTests(map(TheSubDBTestCase, TheSubDBTestCase.download_tests))
    suite.addTests(map(SubsWikiTestCase, SubsWikiTestCase.download_tests))
    suite.addTests(map(SubtitulosTestCase, SubtitulosTestCase.download_tests))
    return suite


if __name__ == '__main__':
    suites = []
    suites.append(query_suite())
    suites.append(list_suite())
    suites.append(download_suite())
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
