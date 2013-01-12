#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2012 Antoine Bertin <diaoulael@gmail.com>
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
from charade.universaldetector import UniversalDetector
from subliminal.cache import region
from subliminal.language import language_set
from subliminal.videos import Video
import codecs
import hashlib
import os.path
import pysrt
import unittest
import yaml


services = {}
config = yaml.load(open('config.yml').read())
fake_file = u'/tmp/fake_file'
region.configure('dogpile.cache.memory')

# Override the exists property
Video.exists = False


def is_valid_subtitle(path):
    u = UniversalDetector()
    for line in open(path, 'rb'):
        u.feed(line)
    u.close()
    encoding = u.result['encoding']
    source_file = codecs.open(path, 'rU', encoding=encoding, errors='replace')
    try:
        for _ in pysrt.SubRipFile.stream(source_file, error_handling=pysrt.SubRipFile.ERROR_RAISE):
            pass
    except pysrt.Error as e:
        if e.args[0] < 50:  # Error occurs within the 50 first lines
            return False
    except UnicodeEncodeError:  # Workaround for https://github.com/byroot/pysrt/issues/12
        pass
    return True


def get_service(service_name, multi=False):
    if service_name not in services:
        mod = __import__('subliminal.services.' + service_name, globals=globals(), locals=locals(), fromlist=['Service'], level=0)
        services[service_name] = mod.Service()
        services[service_name].init()
    services[service_name].multi = multi
    return services[service_name]


class ServiceTestCase(unittest.TestCase):
    service_name = ''

    def setUp(self):
        self.service = get_service(self.service_name)

    def list(self, kind):
        """Test listing subtitles"""
        # Skip if nothing to test
        if kind not in config['services'][self.service_name]:
            raise unittest.SkipTest('Nothing to test')

        with self.service as service:
            # Loop over videos to test
            for video in config['services'][self.service_name][kind]:
                # Create a Video object from the episode config
                v = Video.from_path(config[kind][video['id']]['path'])
                if 'exists' in config[kind][video['id']]:
                    v.exists = config[kind][video['id']]['exists']
                if 'size' in config[kind][video['id']]:
                    v.size = config[kind][video['id']]['size']
                if 'opensubtitles_hash' in config[kind][video['id']]:
                    v.hashes['OpenSubtitles'] = config[kind][video['id']]['opensubtitles_hash']
                if 'thesubdb_hash' in config[kind][video['id']]:
                    v.hashes['TheSubDb'] = config[kind][video['id']]['thesubdb_hash']
                # List subtitles with the appropriate languages
                results = service.list(v, language_set(video['languages']))
                # Checks
                self.assertTrue(len(results) >= video['results'], 'Found %d results while expecting at least %d' % (len(results), video['results']))

    def download(self, kind):
        """Test downloading subtitles"""
        # Skip if nothing to test
        if kind not in config['services'][self.service_name]:
            raise unittest.SkipTest('Nothing to test')

        with self.service as service:
            # Loop over videos to test
            for video in config['services'][self.service_name][kind]:
                # Skip videos for which we don't expect any result
                if video['results'] == 0:
                    continue
                # Create a Video object from the episode config
                v = Video.from_path(config[kind][video['id']]['path'])
                if 'exists' in config[kind][video['id']]:
                    v.exists = config[kind][video['id']]['exists']
                if 'size' in config[kind][video['id']]:
                    v.size = config[kind][video['id']]['size']
                if 'opensubtitles_hash' in config[kind][video['id']]:
                    v.hashes['OpenSubtitles'] = config[kind][video['id']]['opensubtitles_hash']
                if 'thesubdb_hash' in config[kind][video['id']]:
                    v.hashes['TheSubDb'] = config[kind][video['id']]['thesubdb_hash']
                # Download the first subtitle with the appropriate languages
                results = service.list(v, language_set(video['languages']))
                result = service.download(results[0])
                # Checks
                self.assertTrue(os.path.exists(result.path), 'Subtitle file is missing')
                self.assertTrue(is_valid_subtitle(result.path), 'Invalid subtitle file')
                if 'sha1' in video:
                    sha1 = hashlib.sha1(open(result.path).read()).hexdigest()
                    self.assertTrue(sha1 in video['sha1'], 'Found %s SHA1 while expecting %s' % (sha1, video['sha1']))
                os.remove(result.path)

    def test_list_episodes(self):
        """Test listing subtitles for episodes"""
        self.list('episodes')

    def test_list_movies(self):
        """Test listing subtitles for movies"""
        self.list('movies')

    def test_download_episodes(self):
        """Test downloading subtitles for episodes"""
        self.download('episodes')

    def test_download_movies(self):
        """Test downloading subtitles for movies"""
        self.download('movies')


class OpenSubtitlesTestCase(ServiceTestCase):
    service_name = 'opensubtitles'

    def test_query_query(self):
        video = config['movies'][1]
        with self.service as service:
            results = service.query(fake_file, language_set(['en']), query=video['name'])
        self.assertTrue(len(results) > 0)

    def test_query_wrong_languages(self):
        video = config['episodes'][1]
        with self.service as service:
            results = service.query(fake_file, language_set(['zza']), query=video['series'])
        self.assertTrue(len(results) == 0)

    def test_query_imdbid(self):
        video = config['movies'][1]
        with self.service as service:
            results = service.query(fake_file, language_set(['en', 'fr']), imdbid=video['imdbid'])
        self.assertTrue(len(results) > 0)

    def test_query_hash(self):
        video = config['movies'][1]
        with self.service as service:
            results = service.query(fake_file, language_set(['en']), moviehash=video['opensubtitles_hash'], size=str(video['size']))
        self.assertTrue(len(results) > 0)


class BierDopjeTestCase(ServiceTestCase):
    service_name = 'bierdopje'

    def test_query_series(self):
        video = config['episodes'][1]
        with self.service as service:
            results = service.query(fake_file, video['season'], video['episode'], language_set(['en']), series=video['series'])
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        video = config['episodes'][2]
        with self.service as service:
            results = service.query(fake_file, video['season'], video['episode'], language_set(['en']), series=video['series'])
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        video = config['episodes'][1]
        with self.service as service:
            results = service.query(fake_file, video['season'], video['episode'], language_set(['fr']), series=video['series'])
        self.assertTrue(len(results) == 0)

    def test_query_tvdbid(self):
        video = config['episodes'][3]
        with self.service as service:
            results = service.query(fake_file, video['season'], video['episode'], language_set(['en']), tvdbid=video['tvdbid'])
        self.assertTrue(len(results) > 0)

    def test_query_series_and_tvdbid(self):
        video = config['episodes'][3]
        with self.service as service:
            results = service.query(fake_file, video['season'], video['episode'], language_set(['en']), series=video['series'], tvdbid=video['tvdbid'])
        self.assertTrue(len(results) > 0)

    def test_query_wrong_tvdbid(self):
        video = config['episodes'][1]
        with self.service as service:
            results = service.query(fake_file, video['season'], video['episode'], language_set(['en']), tvdbid=9999999999)
        self.assertTrue(len(results) == 0)


class Addic7edTestCase(ServiceTestCase):
    service_name = 'addic7ed'

    def test_query_series(self):
        video = config['episodes'][1]
        with self.service as service:
            results = service.query(fake_file, language_set(['en']), set(), video['series'], video['season'], video['episode'])
        self.assertTrue(len(results) > 0)

    def test_query_wrong_series(self):
        video = config['episodes'][2]
        with self.service as service:
            results = service.query(fake_file, language_set(['en']), set(), video['series'], video['season'], video['episode'])
        self.assertTrue(len(results) == 0)

    def test_query_wrong_languages(self):
        video = config['episodes'][1]
        with self.service as service:
            results = service.query(fake_file, language_set(['zza']), set(), video['series'], video['season'], video['episode'])
        self.assertTrue(len(results) == 0)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(OpenSubtitlesTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(BierDopjeTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(Addic7edTestCase))
    return suite


if __name__ == '__main__':
#    import logging
#    logging.getLogger().setLevel(logging.DEBUG)
#    logging.basicConfig()
    unittest.TextTestRunner(verbosity=2).run(suite())
