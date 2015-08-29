# -*- coding: utf-8 -*-
import logging

from babelfish import Language
from requests import Session

from . import Provider, get_version
from .. import __version__
from ..subtitle import Subtitle, fix_line_ending


logger = logging.getLogger(__name__)


class TheSubDBSubtitle(Subtitle):
    provider_name = 'thesubdb'

    def __init__(self, language, hash):
        super(TheSubDBSubtitle, self).__init__(language)
        self.hash = hash

    @property
    def id(self):
        return self.hash

    def get_matches(self, video, hearing_impaired=False):
        matches = super(TheSubDBSubtitle, self).get_matches(video, hearing_impaired=hearing_impaired)

        # hash
        if 'thesubdb' in video.hashes and video.hashes['thesubdb'] == self.hash:
            matches.add('hash')

        return matches


class TheSubDBProvider(Provider):
    languages = {Language.fromalpha2(l) for l in ['en', 'es', 'fr', 'it', 'nl', 'pl', 'pt', 'ro', 'sv', 'tr']}
    required_hash = 'thesubdb'
    server_url = 'http://api.thesubdb.com/'

    def initialize(self):
        self.session = Session()
        self.session.headers = {'User-Agent': 'SubDB/1.0 (subliminal/%s; https://github.com/Diaoul/subliminal)' %
                                get_version(__version__)}

    def terminate(self):
        self.session.close()

    def query(self, hash):
        # make the query
        params = {'action': 'search', 'hash': hash}
        logger.info('Searching subtitles %r', params)
        r = self.session.get(self.server_url, params=params, timeout=10)

        # handle subtitles not found and errors
        if r.status_code == 404:
            logger.debug('No subtitles found')
            return []
        r.raise_for_status()

        # loop over languages
        subtitles = []
        for language_code in r.text.split(','):
            language = Language.fromalpha2(language_code)

            subtitle = TheSubDBSubtitle(language, hash)
            logger.debug('Found subtitle %r', subtitle)
            subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.hashes['thesubdb']) if s.language in languages]

    def download_subtitle(self, subtitle):
        logger.info('Downloading subtitle %r')
        params = {'action': 'download', 'hash': subtitle.hash, 'language': subtitle.language.alpha2}
        r = self.session.get(self.server_url, params=params, timeout=10)
        r.raise_for_status()

        subtitle.content = fix_line_ending(r.content)
