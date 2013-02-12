# -*- coding: utf-8 -*-
# Copyright 2012 Nicolas Wack <wackou@gmail.com>
# Copyright 2013 Antoine Bertin <diaoulael@gmail.com>
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
from ..cache import region
from ..language import language_set, Language
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import split_keyword
from ..videos import Episode
from bs4 import BeautifulSoup
import logging
import re


logger = logging.getLogger(__name__)


class TVsubtitles(ServiceBase):
    server_url = 'http://www.tvsubtitles.net'
    api_based = False
    languages = language_set(['ar', 'bg', 'cs', 'da', 'de', 'el', 'en', 'es', 'fi', 'fr', 'hu',
                              'it', 'ja', 'ko', 'nl', 'pl', 'pt', 'ro', 'ru', 'sv', 'tr', 'uk',
                              'zh', 'pt-br'])
    #TODO: Find more exceptions
    language_map = {'gr': Language('gre'), 'cz': Language('cze'), 'ua': Language('ukr'),
                    'cn': Language('chi')}
    videos = [Episode]
    require_video = False
    required_features = ['permissive']

    @region.cache_on_arguments()
    def get_show_id(self, name):
        """Search for a show and get it's id.

        :param string name: name of the show to search for
        :return: id of the first show found
        :rtype: int or None

        """
        r = self.session.post('%s/search.php' % self.server_url, data={'q': name}, timeout=self.timeout)
        soup = BeautifulSoup(r.content, self.required_features)
        links = soup.select('div.left li div a')
        if not links:
            return None
        match = re.match('^/tvshow-(\d+)\.html$', links[0]['href'])
        return int(match.group(1))

    @region.cache_on_arguments()
    def get_episode_ids(self, show_id, season):
        """Get episode ids using a given show id.

        :param int show_id: show id
        :param int season: season number
        :return: episode ids per episode number
        :rtype: dict

        """
        r = self.session.get('%s/tvshow-%d-%d.html' % (self.server_url, show_id, season), timeout=self.timeout)
        soup = BeautifulSoup(r.content, self.required_features)
        episode_ids = {}
        for row in soup.select('table#table5 tr'):
            cells = row.find_all('td')
            if not cells:
                continue
            match = re.match('^\d+x(\d+)$', cells[0].text)
            if not match:
                continue
            episode_ids[int(match.group(1))] = int(re.match('^episode-(\d+)\.html$', cells[1].a['href']).group(1))
        return episode_ids

    def list_checked(self, video, languages):
        return self.query(video.path or video.release, languages, video.series, video.season, video.episode)

    def query(self, filepath, languages, series, season, episode):
        logger.debug(u'Getting subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
        # find the show id
        show_id = self.get_show_id(series.lower())
        if not show_id:
            logger.debug(u'Could not find show id')
            return []
        # load episode ids
        episode_ids = self.get_episode_ids(show_id, season)
        if episode not in episode_ids:
            logger.debug(u'Could not find episode id')
            return []
        episode_id = episode_ids[episode]
        # query with the episode id
        r = self.session.get('%s/episode-%d.html' % (self.server_url, episode_id), timeout=self.timeout)
        soup = BeautifulSoup(r.content, self.required_features)
        # loop over subtitles
        subtitles = []
        #TODO: put this in a class attribute?
        prog = re.compile('^/subtitle-(\d+)\.html$')
        for a in soup.find_all('a', href=prog):
            # filter on languages
            sub_language = self.get_language(re.match('^images/flags/(\w+)\.gif$', a.h5.img['src']).group(1))
            if sub_language not in languages:
                logger.debug(u'Language %r not in wanted languages %r' % (sub_language, languages))
                continue
            # get keywords
            sub_keywords = set()
            for p in a.find_all('p'):
                if 'title' in p.attrs:
                    if p['title'] == 'release':
                        sub_keywords |= split_keyword(p.text.strip().lower())
                    elif p['title'] == 'rip':
                        sub_keywords |= set(p.text.lower().split())
            # compute confidence allowing 1 bad vote per 10 good votes
            match = re.match('^(\d+)/(\d+)$', a.span.text.strip())
            sub_bad = int(match.group(1))
            sub_good = int(match.group(2))
            sub_confidence = sub_good / float(sub_good + max(sub_bad - sub_good / 10, 0)) if sub_good + sub_bad > 0 else None
            # other stuff
            sub_id = int(prog.match(a['href']).group(1))
            sub_link = self.server_url + '/download-%d.html' % sub_id
            sub_path = get_subtitle_path(filepath, sub_language, self.multi)
            subtitle = ResultSubtitle(sub_path, sub_language, self.__class__.__name__.lower(), sub_link, confidence=sub_confidence, keywords=sub_keywords)
            subtitles.append(subtitle)
        return subtitles

    def download(self, subtitle):
        self.download_zip_file(subtitle.link, subtitle.path)
        return subtitle


Service = TVsubtitles
