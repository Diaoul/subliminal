# -*- coding: utf-8 -*-
# Copyright 2012 Nicolas Wack <wackou@gmail.com>
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
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode
from subliminal.utils import get_keywords, split_keyword
from ..bs4wrapper import BeautifulSoup
import logging
import re
import unicodedata
import urllib


logger = logging.getLogger(__name__)

def match(pattern, string):
    try:
        return re.search(pattern, string).group(1)
    except AttributeError:
        logger.debug("Could not match '%s' on '%s'" % (pattern, string))
        return None

class TvSubtitles(ServiceBase):
    server_url = 'http://www.tvsubtitles.net'
    api_based = False
    languages = {u'English (US)': 'en', u'English (UK)': 'en', u'English': 'en', u'French': 'fr', u'Brazilian': 'po',
                 u'Portuguese': 'pt', u'Español (Latinoamérica)': 'es', u'Español (España)': 'es', u'Español': 'es',
                 u'Italian': 'it', u'Català': 'ca'}
    reverted_languages = True
    videos = [Episode]
    require_video = False


    def get_likely_series_id(self, name):
        r = self.session.post('%s/search.php' % self.server_url, data = { 'q': name })
        soup = BeautifulSoup(r.content, 'lxml')
        maindiv = soup.find('div', 'left')
        results = []
        for elem in maindiv.find_all('li'):
            sid = int(match('tvshow-([0-9]+)\.html', elem.a['href']))
            show_name = match('(.*) \(', elem.a.text)
            results.append((show_name, sid))

        # TODO: pick up the best one in a smart way
        result = results[0]

        return result[1]

    def get_episode_and_sub_ids(self, series_id, season, number, languages):
        episode_id = None
        subtitle_ids = []
        r = self.session.get('%s/tvshow-%d-%d.html' % (self.server_url, series_id, season))
        soup = BeautifulSoup(r.content, 'lxml')
        table = soup.find('table', id = 'table5')
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if not cells:
                continue

            episode_number = match('x([0-9]+)', cells[0].text)
            if not episode_number:
                continue

            episode_number = int(episode_number)
            episode_id = int(match('episode-([0-9]+)', cells[1].a['href']))

            if episode_number != number:
                # only look for further information for the given episode,
                # we're not trying to scrape tvsubtitles in its entirety
                continue

            for language in cells[3].find_all('a'):
                # we can have either a link directly to the subtitle file,
                # or a link to an episode with multiple subtitles, in which case
                # we need to follow it
                link = language['href']
                lng_code = language.img['alt']
                if lng_code not in languages:
                    logger.debug(u'Language %r not in wanted languages %r' % (lng_code, languages))
                    continue

                if link.startswith('subtitle'):
                    subid = int(match('([0-9]+)', link))
                    logger.debug('Found single subtitle for language: %s - id = %d' % (lng_code, subid))
                    subtitle_ids.append((lng_code, subid))

                elif link.startswith('episode'):
                    subids = []
                    r = self.session.get('%s/episode-%d-%s.html' % (self.server_url, episode_id, lng_code))
                    epsoup = BeautifulSoup(r.content, 'lxml')
                    for subdiv in epsoup.find_all('div', 'subtitlen'):
                        subid = int(match('([0-9]+)', subdiv.find_parent('a')['href']))
                        subids.append((lng_code, subid))
                    logger.debug('Found multiple subtitles for language: %s - ids = %s' % (lng_code, subids))
                    subtitle_ids += subids

        return episode_id, subtitle_ids


    def list(self, video, languages):
        if not self.check_validity(video, languages):
            return []
        results = self.query(video.path or video.release, languages, get_keywords(video.guess), video.series, video.season, video.episode)
        return results

    def download(self, subtitle):
        """Download a subtitle"""
        self.download_zip_file(subtitle.link, subtitle.path)

    def query(self, filepath, languages, keywords, series, season, episode):
        logger.debug(u'Getting subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
        sid = self.get_likely_series_id(series)
        eid, subids = self.get_episode_and_sub_ids(sid, season, episode, languages)

        subtitles = []
        for language, subid in subids:
            # TODO: get sub keywords in /subtitle-$(subid).html (rip and release)
            path = get_subtitle_path(filepath, language, self.config.multi)
            subtitle = ResultSubtitle(path, language, self.__class__.__name__.lower(),
                                      '%s/download-%d.html' % (self.server_url, subid),
                                      keywords=[])
            subtitles.append(subtitle)

        return subtitles

Service = TvSubtitles
