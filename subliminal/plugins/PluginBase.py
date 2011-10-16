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
import urllib2
import threading
from subliminal.exceptions import DownloadFailedError, MissingLanguageError


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

    @abc.abstractmethod
    def __init__(self, config_dict=None):
        self.config_dict = config_dict
        self.logger = logging.getLogger('subliminal.%s' % self.__class__.__name__)

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

    @abc.abstractmethod
    def query(self, video, languages):
        """Make the actual query"""

    @abc.abstractmethod
    def list(self, video, languages):
        """List subtitles"""

    @abc.abstractmethod
    def download(self, subtitle):
        """Download a subtitle"""

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
        if self.config_dict and 'files_mode' in self.config_dict and self.config_dict['files_mode'] != -1:
            os.chmod(filepath, self.config_dict['files_mode'])
    
    def getSubtitlePath(self, video_path, language):
        if not os.path.exists(video_path):
            video_path = os.path.split(video_path)[1]
        path = video_path.rsplit('.', 1)[0]
        if self.config_dict and self.config_dict['multi']:
            return path + '.%s.srt' % language
        return path + '.srt'

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

    def _cmpReleaseGroup(self, x, y):
        """Sort based on keywords matching"""
        return -cmp(len(x.keywords.intersection(self.keywords)), len(y.keywords.intersection(self.keywords)))

