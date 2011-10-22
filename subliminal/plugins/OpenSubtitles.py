# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import PluginBase
import gzip
import os
import xmlrpclib
import guessit
import unicodedata
from subliminal.subtitles import Subtitle, get_subtitle_path
from subliminal.exceptions import DownloadFailedError
from subliminal.videos import *


class OpenSubtitles(PluginBase.PluginBase):
    site_url = 'http://www.opensubtitles.org'
    site_name = 'OpenSubtitles'
    server_url = 'http://api.opensubtitles.org/xml-rpc'
    user_agent = 'Subliminal v1.1'
    api_based = True
    languages = {'aa': 'aar', 'ab': 'abk', 'af': 'afr', 'ak': 'aka', 'sq': 'alb', 'am': 'amh', 'ar': 'ara',
                 'an': 'arg', 'hy': 'arm', 'as': 'asm', 'av': 'ava', 'ae': 'ave', 'ay': 'aym', 'az': 'aze',
                 'ba': 'bak', 'bm': 'bam', 'eu': 'baq', 'be': 'bel', 'bn': 'ben', 'bh': 'bih', 'bi': 'bis',
                 'bs': 'bos', 'br': 'bre', 'bg': 'bul', 'my': 'bur', 'ca': 'cat', 'ch': 'cha', 'ce': 'che',
                 'zh': 'chi', 'cu': 'chu', 'cv': 'chv', 'kw': 'cor', 'co': 'cos', 'cr': 'cre', 'cs': 'cze',
                 'da': 'dan', 'dv': 'div', 'nl': 'dut', 'dz': 'dzo', 'en': 'eng', 'eo': 'epo', 'et': 'est',
                 'ee': 'ewe', 'fo': 'fao', 'fj': 'fij', 'fi': 'fin', 'fr': 'fre', 'fy': 'fry', 'ff': 'ful',
                 'ka': 'geo', 'de': 'ger', 'gd': 'gla', 'ga': 'gle', 'gl': 'glg', 'gv': 'glv', 'el': 'ell',
                 'gn': 'grn', 'gu': 'guj', 'ht': 'hat', 'ha': 'hau', 'he': 'heb', 'hz': 'her', 'hi': 'hin',
                 'ho': 'hmo', 'hr': 'hrv', 'hu': 'hun', 'ig': 'ibo', 'is': 'ice', 'io': 'ido', 'ii': 'iii',
                 'iu': 'iku', 'ie': 'ile', 'ia': 'ina', 'id': 'ind', 'ik': 'ipk', 'it': 'ita', 'jv': 'jav',
                 'ja': 'jpn', 'kl': 'kal', 'kn': 'kan', 'ks': 'kas', 'kr': 'kau', 'kk': 'kaz', 'km': 'khm',
                 'ki': 'kik', 'rw': 'kin', 'ky': 'kir', 'kv': 'kom', 'kg': 'kon', 'ko': 'kor', 'kj': 'kua',
                 'ku': 'kur', 'lo': 'lao', 'la': 'lat', 'lv': 'lav', 'li': 'lim', 'ln': 'lin', 'lt': 'lit',
                 'lb': 'ltz', 'lu': 'lub', 'lg': 'lug', 'mk': 'mac', 'mh': 'mah', 'ml': 'mal', 'mi': 'mao',
                 'mr': 'mar', 'ms': 'may', 'mg': 'mlg', 'mt': 'mlt', 'mo': 'mol', 'mn': 'mon', 'na': 'nau',
                 'nv': 'nav', 'nr': 'nbl', 'nd': 'nde', 'ng': 'ndo', 'ne': 'nep', 'nn': 'nno', 'nb': 'nob',
                 'no': 'nor', 'ny': 'nya', 'oc': 'oci', 'oj': 'oji', 'or': 'ori', 'om': 'orm', 'os': 'oss',
                 'pa': 'pan', 'fa': 'per', 'pi': 'pli', 'pl': 'pol', 'pt': 'por', 'ps': 'pus', 'qu': 'que',
                 'rm': 'roh', 'rn': 'run', 'ru': 'rus', 'sg': 'sag', 'sa': 'san', 'sr': 'scc', 'si': 'sin',
                 'sk': 'slo', 'sl': 'slv', 'se': 'sme', 'sm': 'smo', 'sn': 'sna', 'sd': 'snd', 'so': 'som',
                 'st': 'sot', 'es': 'spa', 'sc': 'srd', 'ss': 'ssw', 'su': 'sun', 'sw': 'swa', 'sv': 'swe',
                 'ty': 'tah', 'ta': 'tam', 'tt': 'tat', 'te': 'tel', 'tg': 'tgk', 'tl': 'tgl', 'th': 'tha',
                 'bo': 'tib', 'ti': 'tir', 'to': 'ton', 'tn': 'tsn', 'ts': 'tso', 'tk': 'tuk', 'tr': 'tur',
                 'tw': 'twi', 'ug': 'uig', 'uk': 'ukr', 'ur': 'urd', 'uz': 'uzb', 've': 'ven', 'vi': 'vie',
                 'vo': 'vol', 'cy': 'wel', 'wa': 'wln', 'wo': 'wol', 'xh': 'xho', 'yi': 'yid', 'yo': 'yor',
                 'za': 'zha', 'zu': 'zul', 'ro': 'rum', 'pb': 'pob', 'un': 'unk', 'ay': 'ass'}
    reverted_languages = False
    videos = [Episode, Movie]
    require_video = False
    confidence_order = ['moviehash', 'imdbid', 'fulltext']

    def __init__(self, config=None, shared=None):
        super(OpenSubtitles, self).__init__(config, shared)

    def connect(self):
        if self.shared and 'OpenSubtitles' in self.shared:
            self.server = self.shared['OpenSubtitles']['server']
            self.token = self.shared['OpenSubtitles']['token']
            return
        self.server = xmlrpclib.ServerProxy(self.server_url)
        result = self.server.LogIn('', '', 'eng', self.user_agent)
        if not result['status'] or result['status'] != '200 OK' or not result['token']:
            raise PluginError('Login failed')
        self.token = result['token']
        if self.shared:
            self.shared['OpenSubtitles'] = {}
            self.shared['OpenSubtitles']['server'] = self.server
            self.shared['OpenSubtitles']['token'] = self.token

    @staticmethod
    def disconnect(server, token):
        server.LogOut(token)

    def list(self, video, languages):
        languages = languages & self.availableLanguages()
        if not languages:
            self.logger.debug(u'No language available')
            return []
        if not self.isValidVideo(video):
            self.logger.debug(u'Not a valid video')
            return []
        self.connect()
        result = self.query(self.create_searches(video, languages), video.path or video.release)
        if not self.shared:
            self.disconnect(self.server, self.token)
        return result

    def download(self, subtitle):
        try:
            self.downloadFile(subtitle.link, subtitle.path + '.gz')
            with open(subtitle.path, 'wb') as dump:
                gz = gzip.open(subtitle.path + '.gz')
                dump.write(gz.read())
                gz.close()
                self.adjustPermissions(subtitle.path)
        except Exception as e:
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            raise DownloadFailedError(str(e))
        finally:
            if os.path.exists(subtitle.path + '.gz'):
                os.remove(subtitle.path + '.gz')
        return subtitle

    def create_searches(self, video, languages):
        """Create the search array, use fulltext search as last resort"""
        searches = []
        if video.exists:
            searches.append({'moviehash': video.hashes['OpenSubtitles'], 'moviebytesize': str(video.size)})
        if video.imdbid:
            searches.append({'imdbid': video.imdbid})
        if not searches and isinstance(video, Episode):
            searches.append({'query': video.series})
        if not searches and isinstance(video, Movie):
            searches.append({'query': video.title})
        for search in searches:
            search['sublanguageid'] = ','.join([self.getLanguage(l) for l in languages])
        return searches

    def query(self, searches, filepath):
        self.logger.debug(u'Query uses token %s and search parameters %r' % (self.token, searches))
        results = self.server.SearchSubtitles(self.token, searches)
        subtitles = []
        for result in results['data']:
            language = self.getRevertLanguage(result['SubLanguageID'])
            path = get_subtitle_path(filepath, language, self.config.multi)
            confidence = 1 - float(self.confidence_order.index(result['MatchedBy'])) / float(len(self.confidence_order))
            subtitle = Subtitle(path, self.__class__.__name__, language, result['SubDownloadLink'], result['SubFileName'], confidence)
            subtitles.append(subtitle)
        return subtitles


