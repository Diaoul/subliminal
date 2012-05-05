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
from . import ServiceBase
from ..exceptions import ServiceError, DownloadFailedError
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode, Movie
from ..utils import to_unicode
from guessit.language import lang_set
import guessit
import gzip
import logging
import os.path
import xmlrpclib


logger = logging.getLogger(__name__)


class OpenSubtitles(ServiceBase):
    server_url = 'http://api.opensubtitles.org/xml-rpc'
    api_based = True
    languages = lang_set(['aar', 'abk', 'afr', 'aka', 'alb', 'amh', 'ara',
                          'arg', 'arm', 'asm', 'ava', 'ave', 'aym', 'aze',
                          'bak', 'bam', 'baq', 'bel', 'ben', 'bih', 'bis',
                          'bos',        'bul', 'bur', 'cat', 'cha', 'che',
                          'chi', 'chu', 'chv', 'cor', 'cos', 'cre', 'cze',
                          'dan', 'div', 'dut', 'dzo', 'eng', 'epo', 'est',
                          'ewe', 'fao', 'fij', 'fin', 'fre', 'fry', 'ful',
                          'geo', 'ger', 'gla', 'gle', 'glg', 'glv', 'ell',
                          'grn', 'guj', 'hat', 'hau', 'heb', 'her', 'hin',
                          'hmo', 'hrv', 'hun', 'ibo', 'ice', 'ido', 'iii',
                          'iku', 'ile', 'ina', 'ind', 'ipk', 'ita', 'jav',
                          'jpn', 'kal', 'kan', 'kas', 'kau', 'kaz', 'khm',
                          'kik', 'kin', 'kir', 'kom', 'kon', 'kor', 'kua',
                          'kur', 'lao', 'lat', 'lav', 'lim', 'lin', 'lit',
                          'ltz', 'lub', 'lug', 'mac', 'mah', 'mal', 'mao',
                          'mar', 'may', 'mlg', 'mlt',        'mon', 'nau',
                          'nav', 'nbl', 'nde', 'ndo', 'nep', 'nno', 'nob',
                          'nor', 'nya', 'oci', 'oji', 'ori', 'orm', 'oss',
                          'pan', 'per', 'pli', 'pol', 'por', 'pus', 'que',
                          'roh', 'run', 'rus', 'sag', 'san',        'sin',
                          'slo', 'slv',        'smo', 'sna', 'snd', 'som',
                          'sot', 'spa', 'srd', 'ssw', 'sun', 'swa', 'swe',
                          'tah', 'tam', 'tat', 'tel', 'tgk', 'tgl', 'tha',
                          'tib', 'tir', 'ton', 'tsn', 'tso', 'tuk', 'tur',
                          'twi', 'uig', 'ukr', 'urd', 'uzb', 'ven', 'vie',
                          'vol', 'wel', 'wln', 'wol', 'xho', 'yid', 'yor',
                          'zha', 'zul', 'rum', 'pob', 'unk'], strict=True)
    REMOVED_FROM_ORIGINAL_LIST = {'mo': 'mol', 'sr': 'scc', 'se': 'sme', 'br': 'bre', 'ay': 'ass'}
    videos = [Episode, Movie]
    require_video = False
    confidence_order = ['moviehash', 'imdbid', 'fulltext']

    def __init__(self, config=None):
        super(OpenSubtitles, self).__init__(config)
        self.server = xmlrpclib.ServerProxy(self.server_url)
        self.token = None

    def init(self):
        super(OpenSubtitles, self).init()
        result = self.server.LogIn('', '', 'eng', self.user_agent)
        if result['status'] != '200 OK':
            raise ServiceError('Login failed')
        self.token = result['token']

    def terminate(self):
        super(OpenSubtitles, self).terminate()
        if self.token:
            self.server.LogOut(self.token)

    def query(self, filepath, languages, moviehash=None, size=None, imdbid=None, query=None):
        searches = []
        if moviehash and size:
            searches.append({'moviehash': moviehash, 'moviebytesize': size})
        if imdbid:
            searches.append({'imdbid': imdbid})
        if query:
            searches.append({'query': query})
        if not searches:
            raise ServiceError('One or more parameter missing')
        for search in searches:
            search['sublanguageid'] = ','.join(l.alpha3 for l in languages)
        logger.debug(u'Getting subtitles %r with token %s' % (searches, self.token))
        results = self.server.SearchSubtitles(self.token, searches)
        if not results['data']:
            logger.debug(u'Could not find subtitles for %r with token %s' % (searches, self.token))
            return []
        subtitles = []
        for result in results['data']:
            language = guessit.Language(result['SubLanguageID'])
            path = get_subtitle_path(filepath, language, self.config.multi)
            confidence = 1 - float(self.confidence_order.index(result['MatchedBy'])) / float(len(self.confidence_order))
            subtitle = ResultSubtitle(path, language, service=self.__class__.__name__.lower(), link=result['SubDownloadLink'],
                                      release=to_unicode(result['SubFileName']), confidence=confidence)
            subtitles.append(subtitle)
        return subtitles

    def list_checked(self, video, languages):
        results = []
        if video.exists:
            results = self.query(video.path or video.release, languages, moviehash=video.hashes['OpenSubtitles'], size=str(video.size))
        elif video.imdbid:
            results = self.query(video.path or video.release, languages, imdbid=video.imdbid)
        elif isinstance(video, Episode):
            results = self.query(video.path or video.release, languages, query=video.series)
        elif isinstance(video, Movie):
            results = self.query(video.path or video.release, languages, query=video.title)
        return results

    def download(self, subtitle):
        #TODO: Use OpenSubtitles DownloadSubtitles method
        try:
            self.download_file(subtitle.link, subtitle.path + '.gz')
            with open(subtitle.path, 'wb') as dump:
                gz = gzip.open(subtitle.path + '.gz')
                dump.write(gz.read())
                gz.close()
        except Exception as e:
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            raise DownloadFailedError(str(e))
        finally:
            if os.path.exists(subtitle.path + '.gz'):
                os.remove(subtitle.path + '.gz')
        return subtitle


Service = OpenSubtitles
