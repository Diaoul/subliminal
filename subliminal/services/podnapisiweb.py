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
from ..exceptions import DownloadFailedError
from ..language import Language, language_set
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..videos import Episode, Movie
from bs4 import BeautifulSoup
import logging
import os.path
import re


logger = logging.getLogger(__name__)


class PodnapisiWeb(ServiceBase):
    server_url = 'http://simple.podnapisi.net'
    search_path = 'http://simple.podnapisi.net/ppodnapisi/search?'
    api_based = False
    videos = [Episode, Movie]
    require_video = False
    required_features = ['xml']
    language_map = {
        Language('Albanian'): '29',
        Language('Arabic'): '12',
        Language('spanish-Argentina'): '14',
        Language('Belarusian'): '50',
        Language('Bosnian'): '10',
        Language('portuguese-Brazil'): '48',
        Language('Bulgarian'): '33',
        Language('Catalan'): '53',
        Language('Chinese'): '17',
        Language('Croatian'): '38',
        Language('Czech'): '7',
        Language('Danish'): '24',
        Language('Dutch'): '23',
        Language('English'): '2',
        Language('Estonian'): '20',
        Language('Persian'): '52',
        Language('Finnish'): '31',
        Language('French'): '8',
        Language('German'): '5',
        Language('gre'): '16',
        Language('kal'): '57',
        Language('Hebrew'): '22',
        Language('Hindi'): '42',
        Language('Hungarian'): '15',
        Language('Icelandic'): '6',
        Language('Indonesian'): '54',
        Language('Irish'): '49',
        Language('Italian'): '9',
        Language('Japanese'): '11',
        Language('Kazakh'): '58',
        Language('Korean'): '4',
        Language('Latvian'): '21',
        Language('Lithuanian'): '19',
        Language('Macedonian'): '35',
        Language('Malay'): '55',
        Language('mdr'): '40',
        Language('Norwegian'): '3',
        Language('Polish'): '26',
        Language('Portuguese'): '32',
        Language('Romanian'): '13',
        Language('Russian'): '27',
        Language('srp'): '36',
        #Language('srp'): '47',
        Language('Sinhala'): '56',
        Language('Slovak'): '37',
        Language('Slovenian'): '1',
        Language('Spanish'): '28',
        Language('Swedish'): '25',
        Language('Thai'): '44',
        Language('Turkish'): '30',
        Language('Ukrainian'): '46',
        Language('Vietnamese'): '51',
        }

    def list_checked(self, video, languages):
        if isinstance(video, Movie):
            return self.query(video.path or video.release,
                              languages=languages,
                              title=video.title,
                              year=video.year)
        else:
            return self.query(video.path or video.release,
                              languages=languages,
                              title=video.series,
                              season=video.season,
                              episode=video.episode)

    def query(self, filepath, languages, title=None, season=None, episode=None, year=None):
        release, extension = os.path.splitext(os.path.basename(filepath))
        params = {'sXML': 1}
        if len(languages) == 1:
            params['sJ'] = self.get_code(list(languages)[0])
        else:
            params['sJ'] = 0
        if release is not None: params['sR'] = release
        if title is not None:   params['sK'] = title
        if season is not None:  params['sTS'] = season
        if episode is not None: params['sTE'] = episode
        if year is not None:    params['sY'] = year
        # Only request the first page (30 results). This might be a problem if
        # multiple language are requested (sJ=0 won't filter by language, so a
        # lot of results might be returned).
        r = self.session.get(self.search_path, params=params)
        if r.status_code != 200:
            logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return []

        results = []
        soup = BeautifulSoup(r.content, self.required_features)
        for subtitle in soup('subtitle'):
            lang_code = subtitle.languageId.text
            language = self.get_language(lang_code)
            if language not in languages:
                continue
            found_title = subtitle.title.text.strip()
            if not self.match_title(title, found_title):
                continue
            download_link = subtitle.url.text
            found_releases = subtitle.release.text
            for frelease in found_releases:
                results.append(ResultSubtitle(
                        path=get_subtitle_path(filepath, language, self.config.multi),
                        language=language,
                        service=self.__class__.__name__.lower(),
                        link=download_link,
                        release=frelease + extension))
        return results

    def download(self, subtitle):
        r = self.session.get(subtitle.link)
        if r.status_code != 200:
            raise DownloadFailedError()
        soup = BeautifulSoup(r.content)
        real_link = self.server_url + soup.find('img', title='Download').parent['href']
        self.download_zip_file(real_link, subtitle.path)
        return subtitle

    def match_title(self, a, b):
        def clean(x):
            return re.sub('[^a-zA-Z0-9]', '', x).lower()
        return clean(a) == clean(b)


PodnapisiWeb.languages = language_set(PodnapisiWeb.language_map.keys())
PodnapisiWeb.language_map.update(dict((v, k) for k, v in PodnapisiWeb.language_map.iteritems()))

Service = PodnapisiWeb
