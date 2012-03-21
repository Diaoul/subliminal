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
from ..exceptions import ServiceError
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode
from ..bs4wrapper import BeautifulSoup
from ..cache import cachedmethod
import logging
import os.path
import urllib
try:
    import cPickle as pickle
except ImportError:
    import pickle


logger = logging.getLogger(__name__)


class BierDopje(ServiceBase):
    server_url = 'http://api.bierdopje.com/A2B638AC5D804C2E/'
    api_based = True
    languages = {'en': 'en', 'nl': 'nl'}
    reverted_languages = False
    videos = [Episode]
    require_video = False

    @cachedmethod
    def get_show_id(self, series):
        r = self.session.get('%sGetShowByName/%s' % (self.server_url, urllib.quote(series.lower())))
        if r.status_code != 200:
            logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return None

        soup = BeautifulSoup(r.content, ['lxml', 'xml'])
        if soup.status.contents[0] == 'false':
            logger.debug(u'Could not find show %s' % series)
            return None

        return int(soup.showid.contents[0])


    def query(self, season, episode, languages, filepath, tvdbid=None, series=None):
        self.init_cache()
        if series:
            request_id = self.get_show_id(series.lower())
            if request_id is None:
                return []
            request_source = 'showid'
            request_is_tvdbid = 'false'
        elif tvdbid:
            request_id = tvdbid
            request_source = 'tvdbid'
            request_is_tvdbid = 'true'
        else:
            raise ServiceError('One or more parameter missing')

        subtitles = []
        for language in languages:
            logger.debug(u'Getting subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language))
            r = self.session.get('%sGetAllSubsFor/%s/%s/%s/%s/%s' % (self.server_url, request_id, season, episode, language, request_is_tvdbid))
            if r.status_code != 200:
                logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
                return []
            soup = BeautifulSoup(r.content, ['lxml', 'xml'])
            if soup.status.contents[0] == 'false':
                logger.debug(u'Could not find subtitles for %s %d season %d episode %d with language %s' % (request_source, request_id, season, episode, language))
                continue
            path = get_subtitle_path(filepath, language, self.config.multi)
            for result in soup.results('result'):
                subtitle = ResultSubtitle(path, language, self.__class__.__name__.lower(), result.downloadlink.contents[0], result.filename.contents[0])
                subtitles.append(subtitle)
        return subtitles

    def list(self, video, languages):
        if not self.check_validity(video, languages):
            return []
        results = self.query(video.season, video.episode, languages, video.path or video.release, video.tvdbid, video.series)
        return results


Service = BierDopje
