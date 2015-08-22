# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from babelfish import Language
from requests import Session

from . import Provider
from ..subtitle import Subtitle


logger = logging.getLogger(__name__)


class NapiProjektSubtitle(Subtitle):

    provider_name = 'napiprojekt'

    def __init__(self, language, file_hash):
        super(NapiProjektSubtitle, self).__init__(language)
        self.file_hash = file_hash

    @property
    def id(self):
        return self.file_hash

    def get_matches(self, video, hearing_impaired=False):
        matches = super(NapiProjektSubtitle, self).get_matches(
            video, hearing_impaired=hearing_impaired)
        if ('napiprojekt' in video.hashes and
                video.hashes['napiprojekt'] == self.file_hash):
            matches.add('hash')
        return matches


class NapiProjektProvider(Provider):

    languages = {Language.fromalpha2(l) for l in ['pl']}
    required_hash = 'napiprojekt'
    server_url = 'http://napiprojekt.pl/unit_napisy/dl.php?'

    def initialize(self):
        self.session = Session()

    def terminate(self):
        self.session.close()

    def get_hash(self, file_hash):
        idx = [0xe, 0x3, 0x6, 0x8, 0x2]
        mul = [2, 2, 5, 4, 3]
        add = [0, 0xd, 0x10, 0xb, 0x5]
        b = []
        for i in range(len(idx)):
            a = add[i]
            m = mul[i]
            i = idx[i]
            t = a + int(file_hash[i], 16)
            v = int(file_hash[t:t + 2], 16)
            b.append(("%x" % (v * m))[-1])
        return ''.join(b)

    def query(self, language, file_hash):
        params = {
            'v': 'dreambox',
            'kolejka': 'false',
            'nick': '',
            'pass': '',
            'napios': 'Linux',
            'l': language.alpha2.upper(),
            'f': file_hash,
            't': self.get_hash(file_hash)}
        logger.info('Searching subtitle %r', params)
        response = self.session.get(self.server_url, params=params, timeout=10)

        # handle subtitles not found and errors
        if str('NPc0') in str(response.content[:4]):
            logger.debug('No subtitles found')
            return None
        response.raise_for_status()

        subtitle = NapiProjektSubtitle(language, file_hash)
        subtitle.content = response.content
        logger.debug('Found subtitle %r', subtitle)
        return subtitle

    def list_subtitles(self, video, languages):
        return list(filter(None, [
            self.query(l, video.hashes['napiprojekt']) for l in languages]))

    def download_subtitle(self, subtitle):
        pass
