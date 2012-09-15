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
from subliminal.exceptions import ServiceError
from subliminal.language import language_set, LANGUAGES
from subliminal.services import ServiceConfig
from subliminal.services.addic7ed import Addic7ed
from subliminal.services.bierdopje import BierDopje
from subliminal.services.opensubtitles import OpenSubtitles
from subliminal.services.podnapisi import Podnapisi
from subliminal.services.subswiki import SubsWiki
from subliminal.services.subtitulos import Subtitulos
from subliminal.services.thesubdb import TheSubDB
from subliminal.services.tvsubtitles import TvSubtitles
import os
import unittest
try:
    import cPickle as pickle
except ImportError:
    import pickle


cache_dir = u'/tmp/sublicache'
if not os.path.exists(cache_dir):
    os.mkdir(cache_dir)
existing_video = u'/something/The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4'


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.wrong_languages = language_set(list(language_set(LANGUAGES) - self.service.languages)[:2])

    def tearDown(self):
        # Setting config to None allows to delete the object, which will in turn save the cache
        self.config = None

    def test_query_series(self):
        with self.service(self.config) as service:
            results = service.query(service, self.fake_file, self.languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with self.service(self.config) as service:
            results = service.query(service, self.fake_file, self.languages, self.episode_keywords, self.wrong_series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with self.service(self.config) as service:
            results = service.query(service, self.fake_file, self.wrong_languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_list_episode(self):
        video = videos.Video.from_path(self.episode_path)
        with self.service(self.config) as service:
            results = service.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_movie(self):
        video = videos.Video.from_path(self.movie_path)
        with self.service(self.config) as service:
            results = service.list(video, self.languages)
        self.assertTrue(len(results) > 0)

    def test_list_wrong_languages(self):
        video = videos.Video.from_path(self.episode_path)
        with self.service(self.config) as service:
            results = service.list(video, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    def test_download_episode(self):
        video = videos.Video.from_path(self.episode_path)
        with self.service(self.config) as service:
            subtitle = service.list(video, language_set([self.episode_sublanguage]))[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            service.download(subtitle)
        self.assertTrue(os.path.exists(subtitle.path))
        self.assertTrue(os.path.getsize(subtitle.path) in self.episode_subfilesizes, msg='Size %d not in %r' % (os.path.getsize(subtitle.path), self.episode_subfilesizes))
        os.remove(subtitle.path)

    def test_download_movie(self):
        video = videos.Video.from_path(self.movie_path)
        with self.service(self.config) as service:
            subtitle = service.list(video, language_set([self.movie_sublanguage]))[0]
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            service.download(subtitle)
        self.assertTrue(os.path.exists(subtitle.path))
        self.assertTrue(os.path.getsize(subtitle.path) in self.movie_subfilesizes, msg='Size %d not in %r' % (os.path.getsize(subtitle.path), self.movie_subfilesizes))
        os.remove(subtitle.path)

    def test_cached_series(self):
        with self.service(self.config) as service:
            service.clear_cache()
            service.query(self.fake_file, self.languages, self.episode_keywords, self.series, self.season, self.episode)
            service.save_cache()
        c = pickle.load(open(os.path.join(cache_dir, 'subliminal_%s.cache' % self.service.__name__)))
        found = False
        for _, cached_values in c.items():
            for args, __ in cached_values.items():
                if args == (self.series.lower(),):
                    found = True
        self.assertTrue(found)


class Addic7edTestCase(ServiceTestCase):
    query_tests = ['test_query_series', 'test_query_wrong_series', 'test_query_wrong_languages']
    list_tests = ['test_list_episode', 'test_list_wrong_languages']
    download_tests = ['test_download_episode']
    cache_tests = ['test_cached_series']
    service = Addic7ed

    def setUp(self):
        super(Addic7edTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.fake_file = u'/tmp/fake_file'
        self.languages = language_set(['en', 'fr'])
        self.episode_path = u'The Big Bang Theory/Season 05/The.Big.Bang.Theory.S05E06.HDTV.XviD-ASAP.mkv'
        self.episode_sublanguage = 'en'
        # FIXME: this is the size of the first subtitle that appears on the page
        # which is the original one, not the most updated one. We should make
        # sure the Addic7ed service picks up the most recent one instead
        self.episode_subfilesizes = [33469]
        self.episode_keywords = set(['asap', 'hdtv'])
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6

    def test_query_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.wrong_series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) == 0)


class BierDopjeTestCase(ServiceTestCase):
    query_tests = ['test_query_series', 'test_query_wrong_series', 'test_query_wrong_languages',
                   'test_query_tvdbid', 'test_query_wrong_tvdbid', 'test_query_series_and_tvdbid']
    list_tests = ['test_list_episode', 'test_list_wrong_languages']
    download_tests = ['test_download_episode']
    cache_tests = ['test_cached_series']
    service = BierDopje

    def setUp(self):
        super(BierDopjeTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.episode_path = u'The Big Bang Theory/Season 05/S05E06 - The Rhinitis Revelation - HD TV.mkv'
        self.episode_sublanguage = 'en'
        self.episode_subfilesizes = [28982]
        self.movie_path = u'Inception (2010)/Inception - 1080p.mkv'
        self.movie_sublanguage = 'en'
        self.movie_subfilesizes = []
        self.languages = language_set(['en', 'nl'])
        self.fake_file = u'/tmp/fake_file'
        self.series = 'The Big Bang Theory'
        self.episode_keywords = set()
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6
        self.tvdbid = 80379
        self.wrong_tvdbid = 9999999999

    def test_query_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.season, self.episode, self.languages, series=self.series)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.season, self.episode, self.languages, series=self.wrong_series)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.season, self.episode, self.wrong_languages, series=self.series)
        self.assertTrue(len(results) == 0)

    def test_query_tvdbid(self):
        with BierDopje(self.config) as service:
            results = service.query(self.fake_file, self.season, self.episode, self.languages, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_series_and_tvdbid(self):
        with BierDopje(self.config) as service:
            results = service.query(self.fake_file, self.season, self.episode, self.languages, series=self.series, tvdbid=self.tvdbid)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_tvdbid(self):
        with BierDopje(self.config) as service:
            results = service.query(self.fake_file, self.season, self.episode, self.languages, tvdbid=self.wrong_tvdbid)
        self.assertTrue(len(results) == 0)

    def test_cached_series(self):
        with self.service(self.config) as service:
            service.clear_cache()
            service.query(self.fake_file, self.season, self.episode, self.languages, series=self.series)
            service.save_cache()
        c = pickle.load(open(os.path.join(cache_dir, 'subliminal_%s.cache' % self.service.__name__)))
        found = False
        for _, cached_values in c.items():
            for args, __ in cached_values.items():
                if args == (self.series.lower(),):
                    found = True
        self.assertTrue(found)


class OpenSubtitlesTestCase(ServiceTestCase):
    query_tests = ['test_query_query', 'test_query_imdbid', 'test_query_hash', 'test_query_wrong_languages']
    list_tests = ['test_list_episode', 'test_list_wrong_languages']
    download_tests = ['test_download_episode']
    cache_tests = []
    service = OpenSubtitles

    def setUp(self):
        super(OpenSubtitlesTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.languages = language_set(['en', 'fr'])
        self.fake_file = u'/tmp/fake_file'
        self.episode_path = existing_video
        self.episode_sublanguage = 'en'
        self.episode_subfilesizes = [30374, 30358, 33585, 33547, 33563, 33601, 31413, 31429]
        self.movie = 'Inception'
        self.imdbid = '1375666'
        self.wrong_imdbid = '9999999'
        self.hash = '51e57c4e8fd77990'
        self.size = 882571264L

    def test_query_query(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, query=self.movie)
        self.assertTrue(len(results) > 0)

    def test_query_imdbid(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, imdbid=self.imdbid)
        self.assertTrue(len(results) > 0)

    def test_query_hash(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, moviehash=self.hash, size=self.size)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_languages(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, moviehash=self.hash, size=self.size)
        self.assertTrue(len(results) == 0)


class PodnapisiTestCase(ServiceTestCase):
    query_tests = ['test_query', 'test_query_wrong_languages']
    list_tests = [] #'test_list', 'test_list_wrong_languages'
    download_tests = [] #'test_download'
    cache_tests = []
    service = Podnapisi

    def setUp(self):
        super(PodnapisiTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.languages = language_set(['en', 'fr'])
        self.fake_file = u'/tmp/fake_file'
        self.path = existing_video
        self.hash = 'e1b45885346cfa0b'

    def test_query(self):
        with Podnapisi(self.config) as service:
            results = service.query(self.fake_file, self.languages, moviehash=self.hash)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_languages(self):
        with Podnapisi(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, moviehash=self.hash)
        self.assertTrue(len(results) == 0)


class SubsWikiTestCase(ServiceTestCase):
    query_tests = ['test_query_series', 'test_query_movie', 'test_query_wrong_parameters', 'test_query_wrong_series', 'test_query_wrong_languages']
    list_tests = ['test_list_episode', 'test_list_movie', 'test_list_wrong_languages']
    download_tests = ['test_download_episode', 'test_download_movie']
    cache_tests = []
    service = SubsWiki

    def setUp(self):
        super(SubsWikiTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.fake_file = u'/tmp/fake_file'
        self.languages = language_set(['en', 'es'])
        self.movie_path = u'Soul Surfer (2011)/Soul.Surfer.(2011).DVDRip.XviD-TWiZTED.mkv'
        self.movie_sublanguage = 'es'
        self.movie_subfilesizes = [87528]
        self.movie_keywords = set(['twizted'])
        self.movie = u'Soul Surfer'
        self.movie_year = 2011
        self.episode_path = u'The Big Bang Theory/Season 05/The.Big.Bang.Theory.S05E06.HDTV.XviD-ASAP.mkv'
        self.episode_sublanguage = 'es'
        self.episode_subfilesizes = [34040]
        self.episode_keywords = set(['asap', 'hdtv'])
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6

    def test_query_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.wrong_series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_query_movie(self):
        with SubsWiki(self.config) as service:
            results = service.query(self.fake_file, self.languages, keywords=self.movie_keywords, movie=self.movie, year=self.movie_year)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_parameters(self):
        with SubsWiki(self.config) as service:
            self.assertRaises(ServiceError, service.query,
                              self.fake_file, self.languages, keywords=self.movie_keywords, movie=self.movie, series=self.series)


class SubtitulosTestCase(ServiceTestCase):
    query_tests = ['test_query_series', 'test_query_wrong_series', 'test_query_wrong_languages']
    list_tests = ['test_list_episode', 'test_list_wrong_languages']
    download_tests = ['test_download_episode']
    cache_tests = []
    service = Subtitulos

    def setUp(self):
        super(SubtitulosTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.fake_file = u'/tmp/fake_file'
        self.languages = language_set(['en', 'es'])
        self.episode_path = u'The Big Bang Theory/Season 05/The.Big.Bang.Theory.S05E06.HDTV.XviD-ASAP.mkv'
        self.episode_sublanguage = 'en'
        self.episode_subfilesizes = [32986]
        self.episode_keywords = set(['asap', 'hdtv'])
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6

    def test_query_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.wrong_series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) == 0)


class TheSubDBTestCase(ServiceTestCase):
    query_tests = ['test_query', 'test_query_wrong_languages']
    list_tests = ['test_list_episode', 'test_list_wrong_languages']
    download_tests = ['test_download_episode']
    cache_tests = []
    service = TheSubDB

    def setUp(self):
        super(TheSubDBTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.episode_path = existing_video
        self.episode_sublanguage = 'en'
        self.episode_subfilesizes = [33536]
        self.hash = u'edc1981d6459c6111fe36205b4aff6c2'
        self.languages = language_set(['en', 'nl'])
        self.fake_file = u'/tmp/fake_file'

    def test_query(self):
        with TheSubDB(self.config) as service:
            results = service.query(self.fake_file, self.hash, self.languages)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_languages(self):
        with TheSubDB(self.config) as service:
            results = service.query(self.fake_file, self.hash, self.wrong_languages)
        self.assertTrue(len(results) == 0)

    @unittest.skipUnless(os.path.exists(existing_video), 'No existing video')
    def test_list_episode(self):
        super(TheSubDBTestCase, self).test_list_episode()

    @unittest.skipUnless(os.path.exists(existing_video), 'No existing video')
    def test_download_episode(self):
        super(TheSubDBTestCase, self).test_download_episode()


class TvSubtitlesTestCase(ServiceTestCase):
    query_tests = ['test_query_series', 'test_query_wrong_series', 'test_query_wrong_languages']
    list_tests = ['test_list_episode', 'test_list_wrong_languages']
    download_tests = ['test_download_episode']
    cache_tests = ['test_cached_series']
    service = TvSubtitles

    def setUp(self):
        super(TvSubtitlesTestCase, self).setUp()
        self.config = ServiceConfig(multi=True, cache_dir=cache_dir)
        self.fake_file = u'/tmp/fake_file'
        self.languages = language_set(['en', 'es'])
        self.episode_path = u'The Big Bang Theory/Season 05/The.Big.Bang.Theory.S05E06.HDTV.XviD-ASAP.mkv'
        self.episode_sublanguage = 'en'
        self.episode_subfilesizes = [33078]
        self.episode_keywords = set(['asap', 'hdtv'])
        self.series = 'The Big Bang Theory'
        self.wrong_series = 'No Existent Show Name'
        self.season = 5
        self.episode = 6

    def test_query_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.languages, self.episode_keywords, self.wrong_series, self.season, self.episode)
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        with self.service(self.config) as service:
            results = service.query(self.fake_file, self.wrong_languages, self.episode_keywords, self.series, self.season, self.episode)
        self.assertTrue(len(results) == 0)


TESTCASES = [Addic7edTestCase, BierDopjeTestCase, OpenSubtitlesTestCase, PodnapisiTestCase, SubsWikiTestCase,
             SubtitulosTestCase, TheSubDBTestCase, TvSubtitlesTestCase]


def query_suite():
    suite = unittest.TestSuite()
    for testcase in TESTCASES:
        suite.addTests(map(testcase, testcase.query_tests))
    return suite


def list_suite():
    suite = unittest.TestSuite()
    for testcase in TESTCASES:
        suite.addTests(map(testcase, testcase.list_tests))
    return suite


def download_suite():
    suite = unittest.TestSuite()
    for testcase in TESTCASES:
        suite.addTests(map(testcase, testcase.download_tests))
    return suite


def cache_suite():
    suite = unittest.TestSuite()
    for testcase in TESTCASES:
        suite.addTests(map(testcase, testcase.cache_tests))
    return suite


def suite():
    return unittest.TestSuite([query_suite(), list_suite(), download_suite(), cache_suite()])


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
