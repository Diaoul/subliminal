# -*- coding: utf-8 -*-
import logging
import os
from io import BytesIO
from zipfile import ZipFile

from babelfish import Language
from requests import Session

from . import Provider
from .. import __short_version__
from ..exceptions import AuthenticationError, ConfigurationError
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

    def __init__(self, username='subliminal', password='lanimilbus'):
        if any((username, password)) and not all((username, password)):
            raise ConfigurationError('Username and password must be specified')

        self.username = username
        self.password = password
        self.session = None

    def initialize(self):
        self.session = Session()
        self.session.headers['User-Agent'] = 'Subliminal/%s' % __short_version__
        self.session.headers['Content-Type'] = 'application/x-www-form-urlencoded'

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
            'n24pref': 1
        }

        response = self.session.post(self.server_url, data=params, timeout=10)
        response.raise_for_status()

        napisy24_status = response.content[:4]
        if napisy24_status[:2] != 'OK':
            if response.content[:11] == 'login error':
                raise AuthenticationError('Login failed')
            logger.error(response.content)
            return None

        if napisy24_status == 'OK-0':
            logger.debug('No subtitles found')
            return None

        response_content = response.content.split('||', 1)
        response_params = dict(p.split(':', 1) for p in response_content[0].split('|')[1:])

        logger.debug('Subtitle params: %s', response_params)

        if napisy24_status == 'OK-1':
            logger.debug('No subtitles found but got video info')
            return None
        elif napisy24_status == 'OK-2':
            logger.debug('Found subtitles')
        elif napisy24_status == 'OK-3':
            logger.debug('Found subtitles but not from n24 database')
            return None

        subtitle = Napisy24Subtitle(language, hash, 'tt%s' % response_params['imdb'].zfill(7))
        with ZipFile(BytesIO(response_content[1])) as zf:
            subtitle.content = fix_line_ending(zf.open(zf.namelist()[0]).read())

        return subtitle

    def list_subtitles(self, video, languages):
        return [s for s in [self.query(l, video.size, video.name, video.hashes['napisy24']) for l in languages] if s is not None]

    def download_subtitle(self, subtitle):
        # there is no download step, content is already filled from listing subtitles
        pass
        