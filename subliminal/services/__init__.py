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
from ..exceptions import MissingLanguageError, DownloadFailedError
from ..subtitles import EXTENSIONS
from .. import cache
import logging
import os
import requests
import threading
import zipfile


__all__ = ['ServiceBase', 'ServiceConfig']
logger = logging.getLogger(__name__)


class ServiceBase(object):
    """Service base class

    :param config: service configuration
    :type config: :class:`ServiceConfig`

    """
    #: URL to the service server
    server_url = ''

    #: User Agent for any HTTP-based requests
    user_agent = 'subliminal v0.5'

    #: Whether based on an API or not
    api_based = False

    #: Timeout for web requests
    timeout = 5

    #: Mapping to Service's language codes and subliminal's
    languages = {}

    #: Whether the mapping is reverted or not
    reverted_languages = False

    #: Accepted video classes (:class:`~subliminal.videos.Episode`, :class:`~subliminal.videos.Movie`, :class:`~subliminal.videos.UnknownVideo`)
    videos = []

    #: Whether the video has to exist or not
    require_video = False

    def __init__(self, config=None):
        self.config = config or ServiceConfig()

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *args):
        self.terminate()

    def init(self):
        """Initialize connection"""
        logger.debug(u'Initializing %s' % self.__class__.__name__)
        self.session = requests.session(timeout=10, headers={'User-Agent': self.user_agent})

    def init_cache(self):
        """Initialize cache, make sure it is loaded from disk"""
        if not self.config or not self.config.cache:
            raise ServiceError('Cache directory is required')

        service_name = self.__class__.__name__
        self.config.cache.load(service_name)

    def save_cache(self):
        service_name = self.__class__.__name__
        self.config.cache.save(service_name)

    def clear_cache(self):
        service_name = self.__class__.__name__
        self.config.cache.clear(service_name)

    def cache_for(self, func, args, result):
        service_name = self.__class__.__name__
        return self.config.cache.cache_for(service_name, func, args, result)

    def cached_value(self, func, args):
        service_name = self.__class__.__name__
        return self.config.cache.cached_value(service_name, func, args)

    def terminate(self):
        """Terminate connection"""
        logger.debug(u'Terminating %s' % self.__class__.__name__)

    def query(self, *args):
        """Make the actual query"""
        pass

    def list(self, video, languages):
        """List subtitles"""
        pass

    def download(self, subtitle):
        """Download a subtitle"""
        self.download_file(subtitle.link, subtitle.path)

    @classmethod
    def available_languages(cls):
        """Available languages in the Service

        :return: available languages
        :rtype: set

        """
        if not cls.reverted_languages:
            return set(cls.languages.keys())
        return set(cls.languages.values())

    @classmethod
    def check_validity(cls, video, languages):
        """Check for video and languages validity in the Service

        :param video: the video to check
        :type video: :class:`~subliminal.videos.video`
        :param set languages: languages to check
        :rtype: bool

        """
        languages &= cls.available_languages()
        if not languages:
            logger.debug(u'No language available for service %s' % cls.__class__.__name__.lower())
            return False
        if not cls.is_valid_video(video):
            logger.debug(u'%r is not valid for service %s' % (video, cls.__class__.__name__.lower()))
            return False
        return True

    @classmethod
    def is_valid_video(cls, video):
        """Check if video is valid in the Service

        :param video: the video to check
        :type video: :class:`~subliminal.videos.Video`
        :rtype: bool

        """
        if cls.require_video and not video.exists:
            return False
        if not isinstance(video, tuple(cls.videos)):
            return False
        return True

    @classmethod
    def is_valid_language(cls, language):
        """Check if language is valid in the Service

        :param string language: the language to check
        :rtype: bool

        """
        if language in cls.available_languages():
            return True
        return False

    @classmethod
    def get_revert_language(cls, language):
        """ISO-639-1 language code from service language code

        :param string language: service language code
        :return: ISO-639-1 language code
        :rtype: string

        """
        if not cls.reverted_languages and language in cls.languages.values():
            return [k for k, v in cls.languages.iteritems() if v == language][0]
        if cls.reverted_languages and language in cls.languages.keys():
            return cls.languages[language]
        raise MissingLanguageError(language)

    @classmethod
    def get_language(cls, language):
        """Service language code from ISO-639-1 language code

        :param string language: ISO-639-1 language code
        :return: service language code
        :rtype: string

        """
        if not cls.reverted_languages and language in cls.languages.keys():
            return cls.languages[language]
        if cls.reverted_languages and language in cls.languages.values():
            return [k for k, v in cls.languages.iteritems() if v == language][0]
        raise MissingLanguageError(language)

    def download_file(self, url, filepath):
        """Attempt to download a file and remove it in case of failure

        :param string url: URL to download
        :param string filepath: destination path

        """
        logger.info(u'Downloading %s' % url)
        try:
            r = self.session.get(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(filepath, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logger.error(u'Download %s failed: %s' % (url, e))
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))
        logger.debug(u'Download finished for file %s. Size: %s' % (filepath, os.path.getsize(filepath)))

    def download_zip_file(self, url, filepath):
        """Attempt to download a zip file and extract any subtitle file from it, if any.
        This cleans up after itself if anything fails.

        :param string url: URL of the zip file to download
        :param string filepath: destination path for the subtitle

        """
        logger.info(u'Downloading %s' % url)
        try:
            zippath = filepath + '.zip'
            r = self.session.get(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(zippath, 'wb') as f:
                f.write(r.content)

            if not zipfile.is_zipfile(zippath):
                # TODO: could check if maybe we already have a text file and
                # download it directly
                raise DownloadFailedError('Downloaded file is not a zip file')

            zipsub = zipfile.ZipFile(zippath)
            for subfile in zipsub.namelist():
                if os.path.splitext(subfile)[1] in EXTENSIONS:
                    open(filepath, 'w').write(zipsub.open(subfile).read())
                    break
            else:
                logger.debug('No subtitles found in zip file...')
                raise DownloadFailedError(str(e))

            os.remove(zippath)
            logger.debug(u'Download finished for file %s. Size: %s' % (filepath, os.path.getsize(filepath)))

            return

        except Exception as e:
            logger.error(u'Download %s failed: %s' % (url, e))
            if os.path.exists(zippath):
                os.remove(zippath)
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))


class ServiceConfig(object):
    """Configuration for any :class:`Service`

    :param bool multi: whether to download one subtitle per language or not
    :param string cache_dir: cache directory

    """
    def __init__(self, multi=False, cache_dir=None):
        self.multi = multi
        self.cache_dir = cache_dir
        self.cache = None
        if cache_dir is not None:
            self.cache = cache.Cache(cache_dir)

    def __repr__(self):
        return 'ServiceConfig(%r, %s)' % (self.multi, self.cache.cache_dir)
