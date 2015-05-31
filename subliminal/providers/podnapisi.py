# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import logging
import re
import contextlib
import xml.etree.ElementTree
import zipfile
import babelfish
import bs4
import charade
import guessit
import requests
from . import Provider
from ..exceptions import InvalidSubtitle, ProviderNotAvailable, ProviderError
from ..subtitle import Subtitle, is_valid_subtitle, compute_guess_matches
from ..subtitle import sanitize_string, extract_title_year
from ..video import Episode, Movie
from urllib import quote

logger = logging.getLogger(__name__)
URL_RE = re.compile(
    '^((http[s]?|ftp):\/)?\/?([^:\/\s]+)(:([^\/]*))?((\/\w+)*\/)' + \
    '([\w\-\.]+[^#?\s]+)(\?([^#]*))?(#(.*))?$',
)

class PodnapisiSubtitle(Subtitle):
    provider_name = 'podnapisi'
    server = 'http://podnapisi.net'
    last_url = None

    def __init__(self, language, id, releases, hearing_impaired, link, series=None, season=None, episode=None,  # @ReservedAssignment
                 title=None, year=None):
        super(PodnapisiSubtitle, self).__init__(language, hearing_impaired)
        self.id = id
        self.releases = releases
        self.hearing_impaired = hearing_impaired
        self.link = link
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year

    def compute_matches(self, video):
        matches = set()
        # episode
        if isinstance(video, Episode):
            # series
            if video.series and \
                sanitize_string(self.series, strip_date=True) == \
                sanitize_string(video.series, strip_date=True):
                matches.add('series')
            # season
            if video.season and self.season == video.season:
                matches.add('season')
            # episode
            if video.episode and self.episode == video.episode:
                matches.add('episode')
            # guess
            for release in self.releases:
                matches |= compute_guess_matches(video, guessit.guess_episode_info(release + '.mkv'))

        # movie
        elif isinstance(video, Movie):
            # title
            if video.title and \
                sanitize_string(self.title) == \
                sanitize_string(video.title):
                matches.add('title')
            # year
            if video.year and self.year == video.year:
                matches.add('year')
            # guess
            for release in self.releases:
                matches |= compute_guess_matches(video, guessit.guess_movie_info(release + '.mkv'))
        return matches


class PodnapisiProvider(Provider):
    languages = set([babelfish.Language('por', 'BR')]) | set([babelfish.Language(l)
                 for l in ['ara', 'aze', 'ben', 'bos', 'bul', 'cat', 'ces', 'dan', 'deu', 'ell', 'eng', 'eus', 'fas',
                           'fin', 'fra', 'glg', 'heb', 'hrv', 'hun', 'hye', 'ind', 'ita', 'jpn', 'kor', 'mkd', 'msa',
                           'nld', 'nor', 'pol', 'por', 'ron', 'rus', 'slk', 'slv', 'spa', 'sqi', 'srp', 'swe', 'tha',
                           'tur', 'ukr', 'vie', 'zho']])
    video_types = (Episode, Movie)
    server = 'http://simple.podnapisi.net'
    pre_link_re = re.compile('^.*(?P<link>/ppodnapisi/predownload/i/\d+/k/.*$)')
    link_re = re.compile('^.*(?P<link>/[a-zA-Z]{2}/ppodnapisi/download/i/\d+/k/.*$)')

    headers = {}

    def initialize(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': self.random_user_agent,
            'Referer': '%s/subtitles/search/advanced' % self.server
        }

    def terminate(self):
        self.session.close()

    def get(self, url, params=None, headers=None, is_xml=False):
        """Make a GET request on `url` with the given parameters

        :param string url: part of the URL to reach with the leading slash
        :param dict params: params of the request
        :param dict headers: headers of the request
        :param bool xml: whether the response content is XML or not
        :return: the response
        :rtype: :class:`xml.etree.ElementTree.Element` or :class:`bs4.BeautifulSoup`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable`

        """

        prefix_url = ''
        url_result = URL_RE.search(url)
        if url_result and url_result.group(2) is None:
            prefix_url = self.server

        # Update url
        url = '%s%s' % (prefix_url, url)

        # Handle Headers
        self.session.headers = self.headers

        # Apply over-ride
        if headers:
            self.session.headers.update(headers)

        self.last_url = None
        try:
            r = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=10,
            )
            # store last url
            self.last_url = r.url

        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code != 200:
            raise ProviderNotAvailable('Request failed with status code %d' % r.status_code)

        if is_xml:
            return xml.etree.ElementTree.fromstring(r.content)
        else:
            return bs4.BeautifulSoup(r.content, ['permissive'])

    def query(self, language, series=None, season=None, episode=None, title=None, year=None):
        """
        Preforms a query for a show on Podnapisi.net
        """
        # Track page count (for multipage fetches
        page = 1
        # parameter listing
        params = {'language': language.alpha2, 'page': str(page)}
        if series and season and episode:
            params['keywords'] = sanitize_string(series, strip_date=True)
            params['seasons'] = season
            params['episodes'] = episode
            if not year:
                year = extract_title_year(series)
            if year:
                params['year'] = year
        elif title:
            params['keywords'] = sanitize_string(title)
            if year:
                params['year'] = year
        else:
            raise ValueError('Missing parameters series and season and episode or title')
        logger.debug('Searching series %r', params)
        subtitles = []

        # Initial Fetch
        preload = self.get(
            '/subtitles/search/advanced',
            params=params,
        )
        preload_url = self.last_url

        # Fetch tracking details
        verify = self.get(
            '/forum/app.php/track',
            params=dict([('path', quote('/subtitles/search/advanced', ''))] + \
                         params.items()),
            headers={
                'Referer': preload_url,
            },
        )

        # Reload page
        soup = self.get(
            '/subtitles/search/advanced',
            params=params,
            headers = {
                'Referer': preload_url,
            },
        )

        # Get page information
        pages = soup.find('div', class_='panel-body')
        pages = pages.find('ul', class_='pagination')
        if pages:
            bullets = pages('li')
            pages = int(bullets[-2][0].a.string)
        else:
            pages = 1

        logger.debug('Podnapisi page matches: %r' % pages)
        while page < 10:
            # Set a hard cap on page count to 10, there is really
            # no reason to turn up more content then that
            for row in soup('tr', class_='subtitle-entry'):
                cells = row('td')
                # common error checking on matched results
                if not cells:
                    continue
                if len(cells) < 1:
                    continue

                # Acquire flags
                flags = []
                flag_entries = cells[0].find_all('i')
                for entry in flag_entries:
                    try:
                        if entry['data-toggle'] != 'tooltip':
                            continue
                    except KeyError:
                        continue
                    try:
                        flags += [ e.lower() for e in entry['class'] if e != 'flag' ]
                    except KeyError:
                        continue
                # convert list
                flags = set(flags)

                # Get Hearing Impared Flag
                hearing_impaired = ('text-cc' in flags)

                # Get Link
                link = cells[0].find('a', rel='nofollow')['href']
                # Get ID
                id = link[11:-9]

                # Get releases (if defined)
                releases = cells[0].find('span', class_='release')
                if not releases:
                    # Fall back to general name
                    releases = [ str(cells[0].find('a', href=link[:-9]).string.strip()), ]

                # Store Title
                elif 'title' in releases:
                    releases = [ str(releases['title'].string.strip()), ]
                else:
                    # store name
                    releases = [ str(releases.string.strip()), ]

                # attempt to match against multi listings (if they exist)
                multi_release = cells[0].find_all('div', class_='release')
                if len(multi_release):
                    for r in multi_release:
                        releases.append(str(r.get_text()))
                if isinstance(releases, basestring):
                    releases = [ releases, ]

                # Simplify list by making it unique
                releases = list(set(releases))

                if series and season and episode:
                    try:
                        subtitles.append(
                            PodnapisiSubtitle(
                                language, id, releases,
                                hearing_impaired, link,
                                series=series, season=season, episode=episode,
                        ))
                    except AttributeError:
                        # there simply wasn't enough information in the TV Show
                        # gracefully handle this instead of crashing :)
                        continue
                elif title:
                    try:
                        subtitles.append(
                            PodnapisiSubtitle(
                                language, id, releases,
                                hearing_impaired, link,
                                title=title, year=year,
                        ))
                    except AttributeError:
                        # there simply wasn't enough information in the movie
                        # gracefully handle this instead of crashing :)
                        continue
                    pass

            # Handle multiple pages
            page += 1
            if page > pages:
                # We're done
                break
            # Store new page
            params['page'] = str(page)
            soup = self.get('/subtitles/search/advanced', params)

        return subtitles

    def list_subtitles(self, video, languages):
        if isinstance(video, Episode):
            return [s for l in languages \
                    for s in self.query(l, series=video.series,
                                        season=video.season,
                                        episode=video.episode)]
        elif isinstance(video, Movie):
            return [s for l in languages \
                    for s in self.query(l, title=video.title,
                                        year=video.year)]

    def download_subtitle(self, subtitle):
        try:
            r = self.session.get(self.server + subtitle.link, timeout=10)
        except requests.Timeout:
            raise ProviderNotAvailable('Timeout after 10 seconds')
        if r.status_code != 200:
            raise ProviderNotAvailable('Request failed with status code %d' % r.status_code)
        with contextlib.closing(zipfile.ZipFile(io.BytesIO(r.content))) as zf:
            if len(zf.namelist()) > 1:
                raise ProviderError('More than one file to unzip')
            subtitle_bytes = zf.read(zf.namelist()[0])
        subtitle_text = subtitle_bytes.decode(charade.detect(subtitle_bytes)['encoding'], 'replace')
        if not is_valid_subtitle(subtitle_text):
            raise InvalidSubtitle
        return subtitle_text
