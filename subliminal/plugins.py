# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
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

import abc
import logging
import os
import gzip
import urllib2
import xmlrpclib
import guessit
import threading
import unicodedata
import re
import zipfile
import requests
import urllib
from hashlib import md5, sha256
try:
    import cPickle as pickle
except ImportError:
    import pickle
from xml.dom import minidom
import BeautifulSoup
from utils import PluginConfig
from subtitles import Subtitle, get_subtitle_path, EXTENSIONS as SUBTITLE_EXTENSIONS
from videos import *
from exceptions import DownloadFailedError, MissingLanguageError, PluginError


class PluginBase(object):
    __metaclass__ = abc.ABCMeta
    site_url = ''
    site_name = ''
    server_url = ''
    user_agent = 'Subliminal v1.0'
    api_based = False
    timeout = 5
    lock = threading.Lock()
    languages = {}
    reverted_languages = False
    videos = []
    require_video = False
    shared_support = False

    @abc.abstractmethod
    def __init__(self, config=None):
        self.config = config or PluginConfig()
        self.logger = logging.getLogger('subliminal.%s' % self.__class__.__name__)

    @abc.abstractmethod
    def init(self):
        """Initiate connexion"""

    @abc.abstractmethod
    def terminate(self):
        """Terminate connexion"""

    @abc.abstractmethod
    def query(self, *args):
        """Make the actual query"""

    @abc.abstractmethod
    def list(self, video, languages):
        """List subtitles"""

    @abc.abstractmethod
    def download(self, subtitle):
        """Download a subtitle"""

    @classmethod
    def availableLanguages(cls):
        if not cls.reverted_languages:
            return set(cls.languages.keys())
        if cls.reverted_languages:
            return set(cls.languages.values())

    @classmethod
    def isValidVideo(cls, video):
        if cls.require_video and not video.exists:
            return False
        if not isinstance(video, tuple(cls.videos)):
            return False
        return True

    @classmethod
    def isValidLanguage(cls, language):
        if language in cls.availableLanguages():
            return True
        return False

    @classmethod
    def getRevertLanguage(cls, language):
        """ISO-639-1 language code from plugin language code"""
        if not cls.reverted_languages and language in cls.languages.values():
            return [k for k, v in cls.languages.iteritems() if v == language][0]
        if cls.reverted_languages and language in cls.languages.keys():
            return cls.languages[language]
        raise MissingLanguageError(language)

    @classmethod
    def getLanguage(cls, language):
        """Plugin language code from ISO-639-1 language code"""
        if not cls.reverted_languages and language in cls.languages.keys():
            return cls.languages[language]
        if cls.reverted_languages and language in cls.languages.values():
            return [k for k, v in cls.languages.iteritems() if v == language][0]
        raise MissingLanguageError(language)

    def adjustPermissions(self, filepath):
        if self.config.filemode != None:
            os.chmod(filepath, self.config.filemode)

    def downloadFile(self, url, filepath, data=None):
        """Download a subtitle file"""
        self.logger.info(u'Downloading %s' % url)
        try:
            req = urllib2.Request(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(filepath, 'wb') as dump:
                f = urllib2.urlopen(req, data=data)
                dump.write(f.read())
                self.adjustPermissions(filepath)
                f.close()
        except Exception as e:
            self.logger.error(u'Download %s failed: %s' % (url, e))
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))
        self.logger.debug(u'Download finished for file %s. Size: %s' % (filepath, os.path.getsize(filepath)))


class OpenSubtitles(PluginBase):
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
                 'za': 'zha', 'zu': 'zul', 'ro': 'rum', 'pt-br': 'pob', 'un': 'unk', 'ay': 'ass'}
    reverted_languages = False
    videos = [Episode, Movie]
    require_video = False
    confidence_order = ['moviehash', 'imdbid', 'fulltext']

    def __init__(self, config=None):
        super(OpenSubtitles, self).__init__(config)
        self.server = xmlrpclib.ServerProxy(self.server_url)

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *args):
        self.terminate()

    def init(self):
        self.logger.debug(u'Initializing')
        result = self.server.LogIn('', '', 'eng', self.user_agent)
        if result['status'] != '200 OK':
            raise PluginError('Login failed')
        self.token = result['token']

    def terminate(self):
        self.logger.debug(u'Terminating')
        self.server.LogOut(self.token)

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
        self.logger.debug(u'Getting subtitles %r with token %s' % (searches, self.token))
        results = self.server.SearchSubtitles(self.token, searches)
        if not results['data']:
            self.logger.debug(u'Could not find subtitles for %r with token %s' % (searches, self.token))
            return []
        subtitles = []
        for result in results['data']:
            language = self.getRevertLanguage(result['SubLanguageID'])
            path = get_subtitle_path(filepath, language, self.config.multi)
            confidence = 1 - float(self.confidence_order.index(result['MatchedBy'])) / float(len(self.confidence_order))
            subtitle = Subtitle(path, self.__class__.__name__, language, result['SubDownloadLink'], result['SubFileName'], confidence)
            subtitles.append(subtitle)
        return subtitles

    def list(self, video, languages):
        languages = languages & self.availableLanguages()
        if not languages:
            self.logger.debug(u'No language available')
            return []
        if not self.isValidVideo(video):
            self.logger.debug(u'Not a valid video')
            return []
        result = self.query(self.create_searches(video, languages), video.path or video.release)
        return result

    def download(self, subtitle):
        #TODO: Use OpenSubtitles DownloadSubtitles method
        #TODO: Accept list argument? Because OpenSubtitles allow multiple subtitles download
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


class BierDopje(PluginBase):
    site_url = 'http://bierdopje.com'
    site_name = 'BierDopje'
    server_url = 'http://api.bierdopje.com/A2B638AC5D804C2E/'
    api_based = True
    languages = {'en': 'en', 'nl': 'nl'}
    reverted_languages = False
    videos = [Episode]
    require_video = False

    def __init__(self, config=None):
        super(BierDopje, self).__init__(config)
        self.showids = {}
        if self.config and self.config.cache_dir:
            self.initCache()

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *args):
        self.terminate()

    def init(self):
        self.logger.debug(u'Initializing')
        self.session = requests.session(timeout=10)

    def terminate(self):
        self.logger.debug(u'Terminating')

    def initCache(self):
        self.logger.debug(u'Initializing cache...')
        if not self.config or not self.config.cache_dir:
            raise PluginError('Cache directory is required')
        self.showids_cache = os.path.join(self.config.cache_dir, 'bierdopje_showids.cache')
        if not os.path.exists(self.showids_cache):
            self.saveToCache()

    def saveToCache(self):
        self.logger.debug(u'Saving showids to cache...')
        with self.lock:
            with open(self.showids_cache, 'w') as f:
                pickle.dump(self.showids, f)

    def loadFromCache(self):
        self.logger.debug(u'Loading showids from cache...')
        with self.lock:
            with open(self.showids_cache, 'r') as f:
                self.showids = pickle.load(f)

    def query(self, season, episode, languages, filepath, tvdbid=None, series=None):
        self.initCache()
        self.loadFromCache()
        if not tvdbid:
            if series.lower() in self.showids:  # from cache
                request_id = self.showids[series.lower()]
                self.logger.debug(u'Retreived showid %d for %s from cache' % (request_id, series))
            else:  # query to get showid
                self.logger.debug(u'Getting showid from show name %s...' % series)
                r = self.session.get('%sGetShowByName/%s' % (self.server_url, urllib.quote(series.lower())))
                if r.status_code != 200:
                    self.logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
                    return []
                soup = BeautifulSoup.BeautifulStoneSoup(r.content)
                if soup.status.contents[0] == 'false':
                    self.logger.debug(u'Could not find show %s' % series)
                    return []
                request_id = int(soup.showid.contents[0])
                showname = soup.showname.contents[0]
                self.showids[series.lower()] = request_id
                self.saveToCache()
            request_source = 'showid'
            request_is_tvdbid = 'false'
        else:
            request_id = tvdbid
            request_source = 'tvdbid'
            request_is_tvdbid = 'true'
        subtitles = []
        for language in languages:
            self.logger.debug(u'Getting subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language))
            r = self.session.get('%sGetAllSubsFor/%s/%s/%s/%s/%s' % (self.server_url, request_id, season, episode, language, request_is_tvdbid))
            if r.status_code != 200:
                self.logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
                return []
            soup = BeautifulSoup.BeautifulStoneSoup(r.content)
            if soup.status.contents[0] == 'false':
                self.logger.debug(u'Could not find subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language))
                continue
            path = get_subtitle_path(filepath, language, self.config.multi)
            for result in soup.results('result'):
                subtitle = Subtitle(path, self.__class__.__name__, language, result.downloadlink.contents[0], result.filename.contents[0])
                subtitles.append(subtitle)
        return subtitles

    def list(self, video, languages):
        languages = languages & self.availableLanguages()
        if not languages:
            self.logger.debug(u'No language available')
            return []
        if not self.isValidVideo(video):
            self.logger.debug(u'Not a valid video')
            return []
        results = self.query(video.season, video.episode, languages, video.path or video.release, video.tvdbid, video.series)
        return results

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle

class TheSubDB(PluginBase):
    site_url = 'http://thesubdb.com'
    site_name = 'SubDB'
    server_url = 'http://api.thesubdb.com/'  # for testing purpose, use http://sandbox.thesubdb.com/ instead
    api_based = True
    user_agent = 'SubDB/1.0 (Subliminal/1.1; https://github.com/Diaoul/subliminal)'  # defined by the API
    languages = {'af': 'af', 'cs': 'cs', 'da': 'da', 'de': 'de', 'en': 'en', 'es': 'es', 'fi': 'fi',
                 'fr': 'fr', 'hu': 'hu', 'id': 'id', 'it': 'it', 'la': 'la', 'nl': 'nl', 'no': 'no',
                 'oc': 'oc', 'pl': 'pl', 'pt': 'pt', 'ro': 'ro', 'ru': 'ru', 'sl': 'sl', 'sr': 'sr',
                 'sv': 'sv', 'tr': 'tr'} # list available with the API at http://sandbox.thesubdb.com/?action=languages
    videos = [Movie, Episode, UnknownVideo]
    require_video = True

    def __init__(self, config=None):
        super(TheSubDB, self).__init__(config)

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *args):
        self.terminate()

    def init(self):
        self.logger.debug(u'Initializing')
        self.session = requests.session(timeout=10, headers={'user-agent': self.user_agent})

    def terminate(self):
        self.logger.debug(u'Terminating')

    def list(self, video, languages):
        languages = languages & self.availableLanguages()
        if not languages:
            self.logger.debug(u'No language available')
            return []
        if not self.isValidVideo(video):
            self.logger.debug(u'Not a valid video')
            return []
        results = self.query(video.path, video.hashes['TheSubDB'], languages)
        return results

    def query(self, filepath, moviehash, languages):
        r = self.session.get(self.server_url, params={'action': 'search', 'hash': moviehash})
        if r.status_code == 404:
            self.logger.debug(u'Could not find subtitles for hash %s' % moviehash)
            return []
        if r.status_code != 200:
            self.logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return []
        available_languages = set([self.getRevertLanguage(l) for l in r.content.split(',')])
        filtered_languages = languages & available_languages
        if not filtered_languages:
            self.logger.debug(u'Could not find subtitles for hash %s with languages %r (only %r available)' % (moviehash, languages, available_languages))
            return []
        subtitles = []
        for language in filtered_languages:
            path = get_subtitle_path(filepath, language, self.config.multi)
            subtitle = Subtitle(path, self.__class__.__name__, language, '%s?action=download&hash=%s&language=%s' % (self.server_url, moviehash, self.getLanguage(language)))
            subtitles.append(subtitle)
        return subtitles

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle


class GetSubtitle(PluginBase):
    site_url = 'http://www.subtitles.com.br/'
    site_name = 'GetSubtitle'
    server_url = 'http://api.getsubtitle.com/server.php?wsdl'
    api_based = True
    languages = {'sq': 'ALB', 'ar': 'ARA', 'hy': 'ARM', 'bs': 'BOS', 'bg': 'BUL', 'ca': 'CAT', 'zh': 'CHI', 'hr': 'HRV',
                 'cs': 'CZE', 'da': 'DAN', 'nl': 'NLD', 'en': 'ENG', 'eo': 'ESP', 'et': 'EST', 'fi': 'FIN', 'fr': 'FRA',
                 'gl': 'GLG', 'ka': 'GEO', 'de': 'DEU', 'el': 'GRC', 'he': 'ISR', 'hi': 'HIN', 'hu': 'HUN', 'is': 'ISL',
                 'id': 'IND', 'it': 'ITA', 'ja': 'JPN', 'kk': 'KAZ', 'ko': 'KOR', 'lv': 'LVA', 'lt': 'LIT', 'lb': 'LTZ',
                 'mk': 'MKD', 'ms': 'MAY', 'no': 'NOR', 'oc': 'OCC', 'pl': 'POL', 'pt': 'POR', 'ro': 'RUM', 'ru': 'RUS',
                 'sr': 'ZAF', 'sk': 'SLK', 'sl': 'SLV', 'es': 'SPA', 'sv': 'SWE', 'th': 'THA', 'tr': 'TUR', 'uk': 'UKR',
                 'ur': 'URD', 'vi': 'VTN'}
    reverted_languages = False
    videos = [Movie]
    require_video = False
    max_results = 100

    def __init__(self, config=None):
        super(GetSubtitle, self).__init__(config)

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *args):
        pass

    def init(self):
        self.logger.debug(u'Initializing')
        self.server = suds.client.Client(self.server_url)

    def terminate(self):
        self.logger.debug(u'Terminating')

    def query(self, *args):
        #TODO
        pass

    def list(self, video, languages):
        languages = languages & self.availableLanguages()
        if not languages:
            self.logger.debug(u'No language available')
            return []
        if not self.isValidVideo(video):
            self.logger.debug(u'Not a valid video')
            return []
        #TODO

    def download(self, subtitle):
        #TODO
        pass


'''
class Addic7ed(PluginBase.PluginBase):
    site_url = 'http://www.addic7ed.com'
    site_name = 'Addic7ed'
    server_url = 'http://www.addic7ed.com'
    api_based = False
    _plugin_languages = {u'English': 'en',
            u'English (US)': 'en',
            u'English (UK)': 'en',
            u'Italian': 'it',
            u'Portuguese': 'pt',
            u'Portuguese (Brazilian)': 'pt-br',
            u'Romanian': 'ro',
            u'Español (Latinoamérica)': 'es',
            u'Español (España)': 'es',
            u'Spanish (Latin America)': 'es',
            u'Español': 'es',
            u'Spanish': 'es',
            u'Spanish (Spain)': 'es',
            u'French': 'fr',
            u'Greek': 'el',
            u'Arabic': 'ar',
            u'German': 'de',
            u'Croatian': 'hr',
            u'Indonesian': 'id',
            u'Hebrew': 'he',
            u'Russian': 'ru',
            u'Turkish': 'tr',
            u'Swedish': 'se',
            u'Czech': 'cs',
            u'Dutch': 'nl',
            u'Hungarian': 'hu',
            u'Norwegian': 'no',
            u'Polish': 'pl',
            u'Persian': 'fa'}

    def __init__(self, config_dict=None):
        super(Addic7ed, self).__init__(self._plugin_languages, config_dict, isRevert=True)
        #http://www.addic7ed.com/serie/Smallville/9/11/Absolute_Justice
        self.release_pattern = re.compile(' \nVersion (.+), ([0-9]+).([0-9])+ MBs')

    def list(self, filepath, languages):
        if not self.checkLanguages(languages):
            return []
        guess = guessit.guess_file_info(filepath, 'autodetect')
        if guess['type'] != 'episode':
            self.logger.debug(u'Not an episode')
            return []
        # add multiple things to the release group set
        release_group = set()
        if 'releaseGroup' in guess:
            release_group.add(guess['releaseGroup'].lower())
        else:
            if 'title' in guess:
                release_group.add(guess['title'].lower())
            if 'screenSize' in guess:
                release_group.add(guess['screenSize'].lower())
        if 'series' not in guess or len(release_group) == 0:
            self.logger.debug(u'Not enough information to proceed')
            return []
        self.release_group = release_group  # used to sort results
        return self.query(guess['series'], guess['season'], guess['episodeNumber'], release_group, filepath, languages)

    def query(self, name, season, episode, release_group, filepath, languages=None):
        searchname = name.lower().replace(' ', '_')
        if isinstance(searchname, unicode):
            searchname = searchname.encode('utf-8')
        searchurl = '%s/serie/%s/%s/%s/%s' % (self.server_url, urllib2.quote(searchname), season, episode, urllib2.quote(searchname))
        self.logger.debug(u'Searching in %s' % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            self.logger.info(u'Error: %s - %s' % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.info(u'TimeOut: %s' % inst)
            return []
        soup = BeautifulSoup(page.read())
        sublinks = []
        for html_sub in soup('td', {'class': 'NewsTitle', 'colspan': '3'}):
            if not self.release_pattern.match(str(html_sub.contents[1])):  # On not needed soup td result
                continue
            sub_teams = self.listTeams([self.release_pattern.match(str(html_sub.contents[1])).groups()[0].lower()], ['.', '_', ' ', '/', '-'])
            if not release_group.intersection(sub_teams):  # On wrong team
                continue
            html_language = html_sub.findNext('td', {'class': 'language'})
            sub_language = self.getRevertLanguage(html_language.contents[0].strip().replace('&nbsp;', ''))
            if languages and not sub_language in languages:  # On wrong language
                continue
            html_status = html_language.findNextSibling('td')
            sub_status = html_status.find('b').string.strip()
            if not sub_status == 'Completed':  # On not completed subtitles
                continue
            sub_link = self.server_url + html_status.findNextSibling('td', {'colspan': '3'}).find('a')['href']
            self.logger.debug(u'Found a match with teams: %s' % sub_teams)
            result = Subtitle(filepath, self.getSubtitlePath(filepath, sub_language), self.__class__.__name__, sub_language, sub_link, keywords=sub_teams)
            sublinks.append(result)
        sublinks.sort(self._cmpReleaseGroup)
        return sublinks

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle


class Podnapisi(PluginBase.PluginBase):
    site_url = "http://www.podnapisi.net"
    site_name = "Podnapisi"
    server_url = 'http://ssp.podnapisi.net:8000'
    api_based = True
    _plugin_languages = {"sl": "1",
            "en": "2",
            "no": "3",
            "ko": "4",
            "de": "5",
            "is": "6",
            "cs": "7",
            "fr": "8",
            "it": "9",
            "bs": "10",
            "ja": "11",
            "ar": "12",
            "ro": "13",
            "es-ar": "14",
            "hu": "15",
            "el": "16",
            "zh": "17",
            "lt": "19",
            "et": "20",
            "lv": "21",
            "he": "22",
            "nl": "23",
            "da": "24",
            "se": "25",
            "pl": "26",
            "ru": "27",
            "es": "28",
            "sq": "29",
            "tr": "30",
            "fi": "31",
            "pt": "32",
            "bg": "33",
            "mk": "35",
            "sk": "37",
            "hr": "38",
            "zh": "40",
            "hi": "42",
            "th": "44",
            "uk": "46",
            "sr": "47",
            "pt-br": "48",
            "ga": "49",
            "be": "50",
            "vi": "51",
            "fa": "52",
            "ca": "53",
            "id": "54"}

    def __init__(self, config_dict=None):
        super(Podnapisi, self).__init__(self._plugin_languages, config_dict)
        # Podnapisi uses two reference for latin serbian and cyrillic serbian (36 and 47)
        # add the 36 manually as cyrillic seems to be more used
        self.revertPluginLanguages["36"] = "sr"

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""
        filepath = filenames[0]
        if not os.path.isfile(filepath):
            return []
        return self.query(self.hashFile(filepath), languages)

    def download(self, subtitle):
        return []

    def query(self, moviehash, languages=None):
        """Makes a query on podnapisi and returns info (link, lang) about found subtitles"""
        # login
        self.server = xmlrpclib.ServerProxy(self.server_url)
        try:
            log_result = self.server.initiate(self.user_agent)
            self.logger.debug(u"Result: %s" % log_result)
            token = log_result["session"]
            nonce = log_result["nonce"]
        except Exception:
            self.logger.error(u"Cannot login" % log_result)
            return []
        username = 'getmesubs'
        password = '99D31$$'
        hash = md5()
        hash.update(password)
        password = hash.hexdigest()
        hash = sha256()
        hash.update(password)
        hash.update(nonce)
        password = hash.hexdigest()
        self.server.authenticate(token, username, password)
        self.logger.debug(u'Authenticated')
        #if languages:
        #    self.logger.debug([self.getLanguage(l) for l in languages])
        #    self.server.setFilters(token, [self.getLanguage(l) for l in languages])
        #    self.logger.debug('Filers set for languages %s' % languages)
        self.logger.debug(u"Starting search with token %s and hashs %s" % (token, [moviehash]))
        results = self.server.search(token, [moviehash])
        return results
        subs = []
        for sub in results['results']:
            subs.append(sub)
        self.server.terminate(token)
        return subs


class SubScene(PluginBase.PluginBase):
    site_url = 'http://subscene.com'
    site_name = 'SubScene'
    server_url = 'http://subscene.com/s.aspx?subtitle='
    api_based = False
    _plugin_languages = {"en": "English",
            "se": "Swedish",
            "da": "Danish",
            "fi": "Finnish",
            "no": "Norwegian",
            "fr": "French",
            "es": "Spanish",
            "is": "Icelandic",
            "cs": "Czech",
            "bg": "Bulgarian",
            "de": "German",
            "ar": "Arabic",
            "el": "Greek",
            "fa": "Farsi/Persian",
            "nl": "Dutch",
            "he": "Hebrew",
            "id": "Indonesian",
            "ja": "Japanese",
            "vi": "Vietnamese",
            "pt": "Portuguese",
            "ro": "Romanian",
            "tr": "Turkish",
            "sr": "Serbian",
            "pt-br": "Brazillian Portuguese",
            "ru": "Russian",
            "hr": "Croatian",
            "sl": "Slovenian",
            "zh": "Chinese BG code",
            "it": "Italian",
            "pl": "Polish",
            "ko": "Korean",
            "hu": "Hungarian",
            "ku": "Kurdish",
            "et": "Estonian"}

    def __init__(self, config_dict=None):
        super(SubScene, self).__init__(self._plugin_languages, config_dict)
        #http://subscene.com/s.aspx?subtitle=Dexter.S04E01.HDTV.XviD-NoTV

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""
        filepath = filenames[0]
        fname = self.getFileName(filepath)
        subs = self.query(fname, filepath, languages)
        if not subs and fname.rfind(".[") > 0:
            # Try to remove the [VTV] or [EZTV] at the end of the file
            teamless_filename = fname[0:fname.rfind(".[")]
            subs = self.query(teamless_filename, filepath, languages)
            return subs
        else:
            return subs

    def download(self, subtitle):
        """Main method to call when you want to download a subtitle"""
        subpage = subtitle["page"]
        page = urllib2.urlopen(subpage)
        soup = BeautifulSoup(page)
        dlhref = soup.find("div", {"class": "download"}).find("a")["href"]
        subtitle["link"] = self.site_url + dlhref.split('"')[7]
        format = "zip"
        archivefilename = subtitle["filename"].rsplit(".", 1)[0] + '.' + format
        self.downloadFile(subtitle["link"], archivefilename)
        subtitlefilename = None
        if zipfile.is_zipfile(archivefilename):
            self.logger.debug(u"Unzipping file " + archivefilename)
            zf = zipfile.ZipFile(archivefilename, "r")
            for el in zf.infolist():
                extension = el.orig_filename.rsplit(".", 1)[1]
                if extension in ("srt", "sub", "txt"):
                    subtitlefilename = srtbasefilename + "." + extension
                    outfile = open(subtitlefilename, "wb")
                    outfile.write(zf.read(el.orig_filename))
                    outfile.flush()
                    self.adjustPermissions(subtitlefilename)
                    outfile.close()
                else:
                    self.logger.info(u"File %s does not seem to be valid " % el.orig_filename)
            # Deleting the zip file
            zf.close()
            os.remove(archivefilename)
            return subtitlefilename
        elif archivefilename.endswith('.rar'):
            self.logger.warn(u'Rar is not really supported yet. Trying to call unrar')
            import subprocess
            try:
                args = ['unrar', 'lb', archivefilename]
                output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
                for el in output.splitlines():
                    extension = el.rsplit(".", 1)[1]
                    if extension in ("srt", "sub"):
                        args = ['unrar', 'e', archivefilename, el, os.path.dirname(archivefilename)]
                        subprocess.Popen(args)
                        tmpsubtitlefilename = os.path.join(os.path.dirname(archivefilename), el)
                        subtitlefilename = os.path.join(os.path.dirname(archivefilename), srtbasefilename + "." + extension)
                        if os.path.exists(tmpsubtitlefilename):
                            # rename it to match the file
                            os.rename(tmpsubtitlefilename, subtitlefilename)
                            # exit
                        return subtitlefilename
            except OSError as e:
                self.logger.error(u"Execution failed: %s" % e)
                return None
        else:
            self.logger.info(u"Unexpected file type (not zip) for %s" % archivefilename)
            return None

    def downloadFile(self, url, filename):
        """Downloads the given url to the given filename"""
        #FIXME: Not working

    def query(self, token, filepath, langs=None):
        """Make a query on SubScene and returns info about found subtitles"""
        sublinks = []
        searchurl = "%s%s" % (self.server_url, urllib2.quote(token))
        self.logger.debug(u"Query: %s" % searchurl)
        page = urllib2.urlopen(searchurl)
        soup = BeautifulSoup(page.read())
        for subs in soup("a", {"class": "a1"}):
            lang_span = subs.find("span")
            lang = self.getRevertLanguage(lang_span.contents[0].strip())
            release_span = lang_span.findNext("span")
            release = release_span.contents[0].strip().split(" (")[0]
            sub_page = subs["href"]
            #http://subscene.com//s-dlpath-260016/78348/rar.zipx
            if release.lower().startswith(token.lower()) and (not langs or lang in langs):
                result = {}
                result["release"] = release
                result["lang"] = lang
                result["link"] = None
                result["page"] = self.site_url + sub_page
                result["filename"] = filepath
                result["plugin"] = self.__class__.__name__
                sublinks.append(result)
        return sublinks


class SubsWiki(PluginBase.PluginBase):
    site_url = 'http://www.subswiki.com'
    site_name = 'SubsWiki'
    server_url = 'http://www.subswiki.com'
    api_based = False
    _plugin_languages = {u'English (US)': 'en',
            u'English (UK)': 'en',
            u'English': 'en',
            u'French': 'fr',
            u'Brazilian': 'pt-br',
            u'Portuguese': 'pt',
            u'Español (Latinoamérica)': 'es',
            u'Español (España)': 'es',
            u'Español': 'es',
            u'Italian': 'it',
            u'Català': 'ca'}

    def __init__(self, config_dict=None):
        super(SubsWiki, self).__init__(self._plugin_languages, config_dict, True)
        self.release_pattern = re.compile('\nVersion (.+), ([0-9]+).([0-9])+ MBs')

    def list(self, video, languages):
        possible_languages = self.possible_languages(languages)
        if not isinstance(video, Episode):
            self.logger.debug(u'Not an episode')
            return []
        return self.query(video.series, video.season, video.episode, video.keywords, video.path, possible_languages)

    def query(self, name, season, episode, release_group, filepath, languages):
        sublinks = []
        searchname = name.lower().replace(' ', '_')
        if isinstance(searchname, unicode):
            searchname = searchname.encode('utf-8')
        searchurl = '%s/serie/%s/%s/%s/' % (self.server_url, urllib2.quote(searchname), season, episode)
        self.logger.debug(u'Searching in %s' % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            self.logger.info(u'Error: %s - %s' % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.info(u'TimeOut: %s' % inst)
            return []
        soup = BeautifulSoup(page.read())
        for subs in soup('td', {'class': 'NewsTitle'}):
            sub_teams = self.listTeams([self.release_pattern.search('%s' % subs.contents[1]).group(1).lower()], ['.', '_', ' ', '/', '-'])
            if not release_group.intersection(sub_teams):  # On wrong team
                continue
            self.logger.debug(u'Team from website: %s' % sub_teams)
            self.logger.debug(u'Team from file: %s' % release_group)
            for html_language in subs.parent.parent.findAll('td', {'class': 'language'}):
                sub_language = self.getRevertLanguage(html_language.string.strip())
                self.logger.debug(u'Subtitle reverted language: %s' % sub_language)
                if not sub_language in languages:  # On wrong language
                    continue
                html_status = html_language.findNextSibling('td')
                sub_status = html_status.find('strong').string.strip()
                if not sub_status == 'Completed':  # On not completed subtitles
                    continue
                sub_link = html_status.findNext('td').find('a')['href']
                result = Subtitle(filepath, self.getSubtitlePath(filepath, sub_language), self.__class__.__name__, sub_language, self.server_url + sub_link, keywords=sub_teams)
                sublinks.append(result)
        sublinks.sort(self._cmpReleaseGroup)
        return sublinks

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle

class TheSubDB(PluginBase.PluginBase):
    site_url = 'http://thesubdb.com'
    site_name = 'SubDB'
    server_url = 'http://api.thesubdb.com'  # for testing purpose, use http://sandbox.thesubdb.com instead
    api_based = True
    user_agent = 'SubDB/1.0 (Subliminal/1.0; https://github.com/Diaoul/subliminal)'  # defined by the API
    _plugin_languages = {'af': 'af', 'cs': 'cs', 'da': 'da', 'de': 'de', 'en': 'en', 'es': 'es', 'fi': 'fi', 'fr': 'fr', 'hu': 'hu', 'id': 'id',
             'it': 'it', 'la': 'la', 'nl': 'nl', 'no': 'no', 'oc': 'oc', 'pl': 'pl', 'pt': 'pt', 'ro': 'ro', 'ru': 'ru', 'sl': 'sl', 'sr': 'sr',
             'sv': 'sv', 'tr': 'tr'} # list available with the API at http://sandbox.thesubdb.com/?action=languages


    def __init__(self, config_dict=None):
        super(TheSubDB, self).__init__(self._plugin_languages, config_dict)

    def list(self, video, languages):
        possible_languages = self.possible_languages(languages)
        if not video.exists:
            return []
        return self.query(video.path, video.hashes['TheSubDB'], possible_languages)

    def query(self, filepath, moviehash, languages):
        searchurl = '%s/?action=%s&hash=%s' % (self.server_url, 'search', moviehash)
        self.logger.debug(u'Query URL: %s' % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            if inst.code == 404:  # no result found
                return []
            self.logger.error(u'Error: %s - %s' % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.error(u'TimeOut: %s' % inst)
            return []
        available_languages = page.readlines()[0].split(',')
        self.logger.debug(u'Available languages: %s' % available_languages)
        subs = []
        for l in available_languages:
            if l in languages:
                result = Subtitle(filepath, self.getSubtitlePath(filepath, l), self.__class__.__name__, l, '%s/?action=download&hash=%s&language=%s' % (self.server_url, moviehash, l))
                subs.append(result)
        return subs

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle
'''
