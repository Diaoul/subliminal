# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import with_statement
import os
import logging
import json
import babelfish
import requests
import json
import hashlib
from . import Provider
from .. import __version__
from ..exceptions import ProviderError
from ..subtitle import Subtitle, fix_line_endings
from ..video import Episode, Movie


logger = logging.getLogger(__name__)
babelfish.language_converters.register('shooter = subliminal.converters.shooter:ShooterConverter')


class ShooterSubtitle(Subtitle):
    provider_name = 'shooter'

    def __init__(self, language, page_link=None, hash=None):
        super(ShooterSubtitle, self).__init__(language, page_link=page_link)
        self.hash = hash

    def compute_matches(self, video):
        matches = set()
        # hash
        if 'shooter' in video.hashes and video.hashes['shooter'] == self.hash:
            matches.add('hash')
        return matches


class ShooterProvider(Provider):
    languages = {babelfish.Language.fromshooter(l) for l in babelfish.language_converters['shooter'].codes}
    required_hash = 'shooter'
    video_types = (Episode, Movie)
    server = 'https://www.shooter.cn/api/subapi.php'

    def initialize(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s (https://github.com/Diaoul/subliminal)' %
                                __version__.split('-')[0]}

    def terminate(self):
        self.session.close()

    def query(self, language, filename, hash):
        params = {
            'filehash': hash,
            'pathinfo': os.path.realpath(filename),
            'format': 'json',
            'lang': language.shooter,
        }
        logger.debug('Searching subtitles %r', params)
        r = self.session.post(self.server, verify=False, params=params, timeout=10)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        if r.content == b'\xff':
            logger.debug('No subtitle found')
            return []
        content = json.loads(r.content)
        subtitles = [ShooterSubtitle(language, page_link=t['Link'], hash=hash) for s in content for t in s['Files']]
        return subtitles

    def list_subtitles(self, video, languages):
        return [s for l in languages for s in self.query(l, video.name, video.hashes['shooter'])]

    def download_subtitle(self, subtitle):
        r = self.session.get(subtitle.page_link)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        subtitle.content = fix_line_endings(r.content)
