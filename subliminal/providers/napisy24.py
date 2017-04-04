# -*- coding: utf-8 -*-
import logging
import os
from io import BytesIO
from zipfile import ZipFile

from babelfish import Language
from requests import Session

from . import Provider
from .. import __short_version__
from ..exceptions import ConfigurationError
from ..subtitle import Subtitle, fix_line_ending

logger = logging.getLogger(__name__)


class Napisy24Subtitle(Subtitle):
    '''Napisy24 Subtitle.'''
    provider_name = 'napisy24'

    def __init__(self, language, hash, imdb_id):
        super(Napisy24Subtitle, self).__init__(language)
        self.hash = hash
        self.imdb_id = imdb_id

    @property
    def id(self):
        return self.hash

    def get_matches(self, video):
        matches = set()

        # hash
        if 'napisy24' in video.hashes and video.hashes['napisy24'] == self.hash:
            matches.add('hash')

        # imdb_id
        if video.imdb_id and self.imdb_id == video.imdb_id:
            matches.add('imdb_id')

        return matches


class Napisy24Provider(Provider):
    '''Napisy24 Provider.'''
    languages = {Language.fromalpha2(l) for l in ['pl']}
    required_hash = 'napisy24'
    server_url = 'http://napisy24.pl/run/CheckSubAgent.php'

    def __init__(self, username=None, password=None):        
        if username and not password or not username and password:
            raise ConfigurationError('Username and password must be specified')

        self.username = username or ''
        self.password = password or ''

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__

    def terminate(self):
        self.session.close()

    def query(self, language, size, name, hash):
        params = {
            'postAction': 'CheckSub', 
            'ua': self.username, 
            'ap': self.password, 
            'fs': size, 
            'fh': hash, 
            'fn': os.path.basename(name),
        }

        response = self.session.post(self.server_url, data=params, timeout=10)
        response.raise_for_status()

        if response.content[:4] != 'OK-2':
            logger.debug('No subtitles found')
            return None
        
        responseContent = response.content.split('||', 1)
        responseParams = dict(p.split(':', 1) for p in responseContent[0].split('|')[1:])

        logger.debug('Subtitle params: %s' % responseParams)

        subtitle = Napisy24Subtitle(language, hash, responseParams['imdb'])

        with ZipFile(BytesIO(responseContent[1])) as zf:
            subtitle.content = fix_line_ending(zf.open(zf.namelist()[0]).read())

        return subtitle

    def list_subtitles(self, video, languages):
        return [s for s in [self.query(l, video.size, video.name, video.hashes['napisy24']) for l in languages] if s is not None]

    def download_subtitle(self, subtitle):
        # there is no download step, content is already filled from listing subtitles
        pass