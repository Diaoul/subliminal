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

    def test_list_episodes(self):
        """Test listing subtitles for episodes"""
        # Skip if no episodes to test
        if 'episodes' not in config['services'][self.service_name]:
            raise unittest.SkipTest('No episodes to test')

        with self.service as service:
            # Loop over episodes to test and service parameters to use
            for episode_id, service_params in config['services'][self.service_name]['episodes'].items():
                # Create a Video object from the config
                video = Video.from_path(config['episodes'][episode_id]['path'])
                if 'exists' in config['episodes'][episode_id]:
                    video.exists = config['episodes'][episode_id]['exists']
                if 'size' in config['episodes'][episode_id]:
                    video.size = config['episodes'][episode_id]['size']
                if 'opensubtitles_hash' in config['episodes'][episode_id]:
                    video.hashes['OpenSubtitles'] = config['episodes'][episode_id]['opensubtitles_hash']
                if 'thesubdb_hash' in config['episodes'][episode_id]:
                    video.hashes['TheSubDb'] = config['episodes'][episode_id]['thesubdb_hash']
                # List subtitles
                results = service.list_checked(video, language_set(service_params['languages']))
                # Compare to the service parameters
                self.assertTrue(len(results) == service_params['results'], 'Found %d results while expecting %d' % (len(results), service_params['results']))


class OpenSubtitlesTestCase(ServiceTestCase):
    service_name = 'opensubtitles'


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(OpenSubtitlesTestCase))
    return suite


if __name__ == '__main__':
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    logging.basicConfig()
    unittest.TextTestRunner().run(suite())
