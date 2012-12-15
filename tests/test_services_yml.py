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
from subliminal.videos import Video
from subliminal.language import language_set
import unittest
import yaml


services = {}
config = yaml.load(open('config.yml').read())

# Override the exists property
Video.exists = False


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
            raise unittest.SkipTest('No %s to test' % kind)

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
                results = service.list_checked(v, language_set(video['languages']))
                # Compare to the service parameters
                self.assertTrue(len(results) == video['results'], 'Found %d results while expecting %d' % (len(results), video['results']))

    def test_list_episodes(self):
        """Test listing subtitles for episodes"""
        self.list('episodes')

    def test_list_movies(self):
        """Test listing subtitles for movies"""
        self.list('movies')


class OpenSubtitlesTestCase(ServiceTestCase):
    service_name = 'opensubtitles'


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(OpenSubtitlesTestCase))
    return suite


if __name__ == '__main__':
#    import logging
#    logging.getLogger().setLevel(logging.DEBUG)
#    logging.basicConfig()
    unittest.TextTestRunner().run(suite())
