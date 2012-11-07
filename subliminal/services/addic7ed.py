# -*- coding: utf-8 -*-
# Copyright 2012 Olivier Leveau <olifozzy@gmail.com>
# Copyright 2012 Antoine Bertin <diaoulael@gmail.com>
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
from ..cache import cachedmethod
from ..exceptions import DownloadFailedError
from ..language import Language, language_set
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import get_keywords, split_keyword
from ..videos import Episode
from guessit.date import search_year
from guessit.matchtree import MatchTree
from guessit.transfo import guess_properties, guess_release_group
from bs4 import BeautifulSoup
import guessit
import logging
import os
import re


logger = logging.getLogger(__name__)

# remove 720p too as it is a far too common keyword to be helpful
NON_KEYWORDS = frozenset(['720p', 'also', 'works', 'with', 'of', 'and'])


class Addic7ed(ServiceBase):
    server_url = 'http://www.addic7ed.com'
    api_based = False
    #TODO: Complete this
    languages = language_set(['ar', 'ca', 'de', 'el', 'en', 'es', 'eu', 'fr', 'ga', 'gl', 'he', 'hr', 'hu',
                              'it', 'pl', 'pt', 'ro', 'ru', 'se', 'pt-br'])
    language_map = {'Portuguese (Brazilian)': Language('por-BR'), 'Greek': Language('gre'),
                    'Spanish (Latin America)': Language('spa'), 'Galego': Language('glg'),
                    u'Català': Language('cat')}
    videos = [Episode]
    require_video = False
    required_features = ['permissive']

    @cachedmethod
    def get_series_id(self, name):
        """Get the show page and cache every show found in it"""
        r = self.session.get('%s/shows.php' % self.server_url)
        soup = BeautifulSoup(r.content, self.required_features)
        for html_series in soup.select('h3 > a'):
            # get series ID
            match = re.search('show/([0-9]+)', html_series['href'])
            if match is None:
                continue
            series_id = int(match.group(1))

            # get series name
            series_name = html_series.text.lower()
            self.cache_for(self.get_series_id, args=(series_name,), result=series_id)

            # if we have a the year in the series name, also cache the series
            # id for the name without the year in it
            if (series_name != name and
                series_name.startswith(name) and
                search_year(series_name[len(name):])[0] is not None):
                try:
                    # if we already have a cached value, don't overwrite
                    self.cached_value(self.get_series_id, args=(name,))
                except KeyError:
                    # if this is not cached yet, do it now
                    logger.debug('Accepting series "%s" (queried: "%s")' % (series_name, name))
                    self.cache_for(self.get_series_id, args=(name,), result=series_id)


        return self.cached_value(self.get_series_id, args=(name,))

    @cachedmethod
    def get_episode_url(self, series_id, season, episode):
        r = self.session.get('%s/show/%d&season=%d' % (self.server_url, series_id, season))
        soup = BeautifulSoup(r.content, self.required_features)

        for row in soup('tr', {'class': 'epeven completed'}):
            cells = row('td')
            s = int(cells[0].text.strip())
            ep = int(cells[1].text.strip())
            episode_url = '%s/%s' % (self.server_url, cells[2].a['href'])
            self.cache_for(self.get_episode_url,
                           args=(series_id, s, ep),
                           result=episode_url)
        return self.cached_value(self.get_episode_url, args=(series_id, season, episode))

    def list_checked(self, video, languages):
        return self.query(video.path or video.release, languages, get_keywords(video.guess), video.series, video.season, video.episode)

    def parse_subtitles(self, soup):
        subs = []
        for i, container in enumerate(soup.findAll(id='container95m')):
            table = container.table.table
            if not table:
                continue

            rows = table('tr')

            # row 0: version
            # row 1: "works with" metadata
            # row N: language - completion status - download links
            # row N+1: ? - hearing impaired - num downloads
            title = rows[0]('td')[0].text.strip()
            version = title.split(',')[0][7:].strip()
            notes = rows[1]('td', {'class': 'newsDate'})[0].text.strip()

            mtree = MatchTree(version.lower())
            guess_release_group.process(mtree)
            guess_properties.process(mtree)
            found = mtree.matched()

            keywords = get_keywords(found)
            keywords = (keywords | split_keyword(notes.lower())) - NON_KEYWORDS

            for row1, row2 in zip(rows[2:], rows[3:]):
                lang_cell = row1.find('td', {'class': 'language'})
                if not lang_cell:
                    continue

                cells1 = row1('td')
                cells2 = row2('td')

                lang = cells1[2].text.strip()
                status = cells1[3].text.strip()
                dlinks = row1('a', {'class': 'buttonDownload'})
                # if there are 2 download buttons, keep the 2nd one, which
                # corresponds to most updated subtitle (preferred to original)
                if len(dlinks) == 1:
                    url = dlinks[0]['href']
                elif len(dlinks) == 2:
                    url = dlinks[1]['href']
                else:
                    logger.debug('Invalid number of download links, skipping sub...')
                    continue

                hearing_impaired = cells2[0].img.next.get('title')

                subs.append(dict(version=version,
                                 language=lang,
                                 keywords=keywords,
                                 status=status,
                                 hearing_impaired=hearing_impaired,
                                 url=url))

        return subs


    def query(self, filepath, languages, keywords, series, season, episode):
        logger.debug(u'Getting subtitles for %s season %d episode %d with languages %r' % (series, season, episode, languages))
        self.init_cache()
        try:
            series_id = self.get_series_id(series.lower())
        except KeyError:
            logger.debug(u'Could not find series id for %s' % series)
            return []

        try:
            episode_url = self.get_episode_url(series_id, season, episode)
        except KeyError:
            logger.debug(u'Could not find episode id for season %d episode %s' % (season, episode))
            return []

        # first, get info for all the subtitles on the page...
        r = self.session.get(episode_url)
        soup = BeautifulSoup(r.content, self.required_features)
        subs = self.parse_subtitles(soup)

        # ...then filter them to keep only those that we want
        subtitles = []
        for sub in subs:
            #if sub['hearing_impaired']:
            #    logger.debug(u'Skipping hearing impaired')
            #    continue
            if sub['status'] != 'Completed':
                logger.debug(u'Wrong subtitle status %s' % sub['status'])
                continue
            sub_language = self.get_language(sub['language'])
            if sub_language not in languages:
                logger.debug(u'Language %r not in wanted languages %r' % (sub_language, languages))
                continue

            sub_keywords = sub['keywords']
            #TODO: Maybe allow empty keywords here? (same in Subtitulos)
            if keywords and not keywords & sub_keywords:
                logger.debug(u'None of subtitle keywords %r in %r' % (sub_keywords, keywords))
                continue

            logger.debug(u'Accepted sub in %s (HI=%s) with keywords asked: %s - parsed: %s'
                         % (sub_language, bool(sub['hearing_impaired']), keywords, sub_keywords))

            sub_link = '%s/%s' % (self.server_url, sub['url'])
            sub_path = get_subtitle_path(filepath, sub_language, self.config.multi)
            subtitle = ResultSubtitle(sub_path, sub_language, self.__class__.__name__.lower(), sub_link, keywords=sub_keywords)
            subtitles.append(subtitle)
        return subtitles

    def download(self, subtitle):
        logger.info(u'Downloading %s in %s' % (subtitle.link, subtitle.path))
        try:
            r = self.session.get(subtitle.link, headers={'Referer': subtitle.link, 'User-Agent': self.user_agent})
            soup = BeautifulSoup(r.content, self.required_features)
            if soup.title is not None and u'Addic7ed.com' in soup.title.text.strip():
                raise DownloadFailedError('Download limit exceeded')
            with open(subtitle.path, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            logger.error(u'Download failed: %s' % e)
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            raise DownloadFailedError(str(e))
        logger.debug(u'Download finished')
        return subtitle


Service = Addic7ed
