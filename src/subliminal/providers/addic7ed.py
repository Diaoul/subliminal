"""Provider for Addic7ed."""

from __future__ import annotations

import contextlib
import difflib
import hashlib
import logging
import re
import unicodedata
from random import randint
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import unquote

from babelfish import Language, language_converters  # type: ignore[import-untyped]
from babelfish.exceptions import LanguageReverseError  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]
from requests import Response, Session
from requests.cookies import RequestsCookieJar

from subliminal.cache import SHOW_EXPIRATION_TIME, region
from subliminal.exceptions import ConfigurationError, DownloadLimitExceeded, NotInitializedProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.utils import sanitize
from subliminal.video import Episode, Video

from . import ParserBeautifulSoup, Provider

if TYPE_CHECKING:
    from collections.abc import Mapping, Set

logger = logging.getLogger(__name__)

with contextlib.suppress(ValueError):
    language_converters.register('addic7ed = subliminal.converters.addic7ed:Addic7edConverter')

#: Series cell matching regex
show_cells_re = re.compile(b'<td class="version">.*?</td>', re.DOTALL)

#: Series url parsing regex
series_url_re = re.compile(
    r'\/serie\/(?P<series>[^\/]+)\/(?P<season>\d+)\/(?P<episode>\d+)\/(?P<title>[^\/]*)'  # spellchecker: disable-line
)

#: Show_id href parsing regex
show_id_re = re.compile(r'\/season\/(?P<show_id>\d+)\/(?P<season>\d+)')

#: Series header parsing regex
series_year_re = re.compile(r'^(?P<series>[ \w\'.:(),*&!?-]+?)(?: \((?P<year>\d{4})\))?$')


def remove_accents(input_str: str) -> str:
    """Remove accents."""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def addic7ed_sanitize(text: str) -> str:
    """Sanitize the title for Addic7ed."""
    return sanitize(remove_accents(text).replace("'", ' ').replace('_', ' '))


def concat_all(*args: Any) -> str:
    """Concatenate all the terms that are not None as strings."""
    return ' '.join(f'{a}' for a in args if a)


AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',  # noqa: E501
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',  # noqa: E501
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',  # noqa: E501
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:56.0) Gecko/20100101 Firefox/56.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Safari/604.1.38',  # noqa: E501
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Safari/604.1.38',  # noqa: E501
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:56.0) Gecko/20100101 Firefox/56.0',
]

addic7ed_languages: Set[Language] = {Language('por', 'BR')} | {
    Language(lang)
    for lang in [
        'ara',
        'aze',
        'ben',
        'bos',
        'bul',
        'cat',
        'ces',
        'dan',
        'deu',
        'ell',
        'eng',
        'eus',
        'fas',
        'fin',
        'fra',
        'glg',
        'heb',
        'hrv',
        'hun',
        'hye',
        'ind',
        'ita',
        'jpn',
        'kor',
        'mkd',
        'msa',
        'nld',
        'nor',
        'pol',
        'por',
        'ron',
        'rus',
        'slk',
        'slv',
        'spa',
        'sqi',
        'srp',
        'swe',
        'tha',
        'tur',
        'ukr',
        'vie',
        'zho',
    ]
}


class Addic7edSubtitle(Subtitle):
    """Addic7ed Subtitle."""

    provider_name: ClassVar[str] = 'addic7ed'

    series: str
    season: int | None
    episode: int | None
    title: str | None
    year: int | None
    release_group: str | None

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        hearing_impaired: bool = False,
        page_link: str | None = None,
        series: str = '',
        season: int | None = None,
        episode: int | None = None,
        title: str | None = None,
        year: int | None = None,
        release_group: str | None = None,
    ) -> None:
        super().__init__(language, subtitle_id, hearing_impaired=hearing_impaired, page_link=page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.release_group = release_group

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        # Series (with year)
        series_year = f'{self.series} ({self.year})' if self.year is not None else self.series

        # Title with release group
        parts = []
        if self.title:
            parts.append(self.title)
        if self.release_group:
            parts.append(self.release_group)
        title_part = ' - '.join(parts)

        return f'{series_year} s{self.season:02d}e{self.episode:02d}{title_part}'

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        # series name
        matches = guess_matches(
            video,
            {
                'title': self.series,
                'season': self.season,
                'episode': self.episode,
                'episode_title': self.title,
                'year': self.year,
                'release_group': self.release_group,
            },
        )

        # resolution
        if video.resolution and self.release_group and video.resolution in self.release_group.lower():
            matches.add('resolution')
        # other properties
        if self.release_group:  # pragma: no branch
            matches |= guess_matches(video, guessit(self.release_group, {'type': 'episode'}), partial=True)

        return matches


class Addic7edProvider(Provider):
    """Addic7ed Provider.

    :param (str | None) username: addic7ed username (not mandatory)
    :param (str | None) password: addic7ed password (not mandatory)
    :param int timeout: request timeout
    :param bool allow_searches: allow using Addic7ed search API, it's very slow and
        using it can result in blocking access to the website (default to False).

    """

    languages: ClassVar[Set[Language]] = addic7ed_languages
    video_types: ClassVar = (Episode,)
    server_url: ClassVar[str] = 'https://www.addic7ed.com'
    subtitle_class: ClassVar = Addic7edSubtitle

    username: str | None
    password: str | None
    apikey: str
    timeout: int
    logged_in: bool
    session: Session | None

    #: Allow using Addic7ed search API, it's very slow and using it can result in blocking access to the website
    allow_searches: bool

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        *,
        timeout: int = 20,
        allow_searches: bool = False,
    ) -> None:
        if any((username, password)) and not all((username, password)):
            msg = 'Username and password must be specified'
            raise ConfigurationError(msg)

        self.username = username
        self.password = hashlib.md5(password.encode('utf-8')).hexdigest() if password else None  # noqa: S324
        self.timeout = timeout
        self.allow_searches = allow_searches
        self.logged_in = False
        self.session = None

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.headers['Accept-Language'] = 'en-US,en;q=1.0'
        self.session.headers['Referer'] = self.server_url

        logger.debug('Addic7ed: using random user agents')
        self.session.headers['User-Agent'] = AGENT_LIST[randint(0, len(AGENT_LIST) - 1)]  # noqa: S311

        # login:
        if self.username and self.password:
            cookies = {'wikisubtitlesuser': self.username, 'wikisubtitlespass': self.password}
            self.session.cookies = RequestsCookieJar()
            for k, v in cookies.items():
                self.session.cookies.set(k, v)

            logger.debug('Logged in')
            self.logged_in = True

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.session:  # pragma: no cover
            raise NotInitializedProviderError

        logger.debug('Logged out')
        self.logged_in = False
        self.session.close()

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def _get_show_ids(self) -> dict[str, int]:
        """Get the ``dict`` of show ids per series by querying the `shows.php` page.

        Best option for searching show id.

        :return: show id per series, lower case and without quotes.
        :rtype: dict[str, int]
        """
        if not self.session:  # pragma: no cover
            raise NotInitializedProviderError

        # get the show page
        logger.info('Getting show ids')
        # r = self.session.get(self.server_url + 'ajax_getShows.php', timeout=10)
        r = self.session.get(self.server_url, timeout=self.timeout)
        r.raise_for_status()

        if not r.text or 'Log in' in r.text:  # pragma: no cover
            logger.warning('Failed to login, check your userid, password')
            return {}

        # Use r.content in bytes as it is correctly decoded (it fails for r.text in str)
        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        # populate the show ids
        show_ids = {}
        for show in soup.select('option', value=re.compile(r'\d+')):  # type: ignore[call-arg]
            # Not a show, the combobox selector
            if 'selected' in show.attrs or 'value' not in show.attrs:
                continue
            try:
                show_id = int(show['value'])  # type: ignore[arg-type]
            except ValueError:
                continue
            title = addic7ed_sanitize(show.text)
            show_ids[title] = show_id
        logger.debug('Found %d show ids', len(show_ids))
        return show_ids

    def _get_episode_pages(self, response: Response) -> list[Response]:  # pragma: no cover
        """Get all the response pages from a single response."""
        if not self.session:
            raise NotInitializedProviderError

        # not a search page
        if 'search.php?' not in response.url:
            return [response]

        # parse the page
        soup = ParserBeautifulSoup(response.content, ['lxml', 'html.parser'])

        # check if list of episodes
        table = soup.find('table', class_='tabel')  # spellchecker: disable-line

        if table is None:
            logger.info('Cannot find the table with matching episodes in %s', response.url)
            return []

        pages = []
        episode_matches = table.select('tr > td > a')  # type: ignore[union-attr]
        for match in episode_matches:
            path = match['href']
            link = f'{self.server_url}/{path}'
            r = self.session.get(link, timeout=self.timeout)
            r.raise_for_status()
            # TODO: catch exception

            pages.append(r)

        return pages

    def _get_show_id_from_page(self, response: Response) -> int | None:  # pragma: no cover
        """Parse the show id from a page."""
        soup = ParserBeautifulSoup(response.content, ['lxml', 'html.parser'])

        # Find the show_id
        tag = soup.find('a', href=re.compile(r'\/season\/'))
        if tag is None:
            logger.warning('Show id not found: cannot find season href')
            return None

        href = str(tag['href'])  # type: ignore[index]
        match = show_id_re.search(href)
        if not match:
            logger.warning('Show id not found: cannot match season %s', href)
            return None

        return int(match.groupdict()['show_id'])

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def _search_show_ids(
        self,
        series_year: str,
        season: int | None = None,
        episode: int | None = None,
    ) -> dict[str, int]:  # pragma: no cover
        """Search the show id from the `series_year` query.

        Very slow, better to avoid.

        :param str series_year: series of the episode, optionally with the year.
        :param int season: season of the series. If None, defaults to 1
        :param int episode: episode in the season. If None, defaults to 1
        :return: a list of potential show ids.
        :rtype: list[int]
        """
        if not self.session:
            raise NotInitializedProviderError

        season = season if season is not None else 1
        episode = episode if episode is not None else 1
        search_series = f'{series_year} {season}x{episode}'
        params = {'search': search_series, 'Submit': 'Search'}

        # make the search
        logger.info('Searching with %r', params)
        r = self.session.get(self.server_url + '/search.php', params=params, timeout=self.timeout)
        r.raise_for_status()
        # TODO: catch exception

        # get the episode pages
        responses = self._get_episode_pages(r)

        show_ids = {}
        for response in responses:
            match = series_url_re.search(response.url)
            if not match:
                logger.info('Could not parse series name from %r', response.url)
                continue

            found_series = unquote(match.groupdict()['series'])
            found_series = addic7ed_sanitize(found_series)

            show_id = self._get_show_id_from_page(response)
            if show_id is not None:
                show_ids[found_series] = show_id
        return show_ids

    def _search_show_id(self, series_year: str) -> int | None:  # pragma: no cover
        """Search the show id from the dict of shows."""
        show_ids = self._search_show_ids(series_year)
        if len(show_ids) == 0:
            logger.info('Could not find show_id for %r', series_year)
            return None

        series_sanitized = addic7ed_sanitize(series_year)
        best_matches = difflib.get_close_matches(series_sanitized, show_ids.keys(), n=1, cutoff=0)
        if len(best_matches) == 0:
            logger.info('Could not find show_id for %r', series_year)
            return None
        return show_ids.get(best_matches[0])  # type: ignore[no-any-return]

    def _try_get_show_id(
        self,
        show_ids: Mapping[str, int],
        series: str,
        year: int | None = None,
        country_code: str | None = None,
    ) -> int | None:
        if not show_ids:  # pragma: no cover
            return None

        show_id = None
        # attempt with country
        if country_code:
            logger.debug('Getting show id with country')
            show_id = show_ids.get(f'{series} {country_code.lower()}')
            if show_id is not None:  # pragma: no branch
                return show_id

        # attempt with year
        if year:
            logger.debug('Getting show id with year')
            series_year = concat_all(series, year)
            show_id = show_ids.get(series_year)
            if show_id is not None:
                return show_id

        # attempt clean
        logger.debug('Getting show id')
        return show_ids.get(series)

    def get_show_id(self, series: str, year: int | None = None, country_code: str | None = None) -> int | None:
        """Get the show id.

        :param str series: the series title.
        :param (int | None) year: the series year.
        :param (str | None) country_code: the series country code.
        :return: the show id.
        :rtype: int | None

        """
        # addic7ed doesn't support search with quotes
        series_sanitized = addic7ed_sanitize(series)

        show_ids = self._get_show_ids()
        if not show_ids:  # pragma: no cover
            self._get_show_ids.invalidate()  # type: ignore[attr-defined]
            show_ids = self._get_show_ids()

        show_id = self._try_get_show_id(show_ids, series_sanitized, year=year, country_code=country_code)
        if show_id is not None:
            return show_id

        logger.info('Series %s not found in show ids', series)
        if self.allow_searches:  # pragma: no cover
            # search as last resort
            logger.info('Use the search API with %s', series)
            show_ids = self._search_show_ids(series_sanitized)

            show_id = self._try_get_show_id(show_ids, series_sanitized, year=year, country_code=country_code)
            if show_id is not None:
                return show_id

            # best match as last of last resort
            logger.info('Series %s not found in show ids', series)
            extended_series = concat_all(series_sanitized, year, country_code)
            return self._search_show_id(extended_series)

        return None

    def _get_show_id_with_alternative_names(self, video: Episode) -> int | None:
        """Get the show id, using alternative series names also."""
        # lookup show_id
        show_id = self.get_show_id(video.series, year=video.year)

        # Try alternative names
        if show_id is None:
            for alt_series in video.alternative_series:
                show_id = self.get_show_id(alt_series)
                if show_id is not None:  # pragma: no branch
                    # show_id found, keep the title and show_id
                    break

        return show_id

    def query(
        self,
        show_id: int | None,
        series: str,
        season: int,
        *,
        year: int | None = None,
    ) -> list[Addic7edSubtitle]:
        """Query the provider for subtitles.

        :param (int | None) show_id: the show id.
        :param str series: the series title.
        :param int season: the season number.
        :param (int | None) year: the year of the show.
        :return: the list of found subtitles.
        :rtype: list[Addic7edSubtitle]

        """
        if not self.session:  # pragma: no cover
            raise NotInitializedProviderError

        if show_id is None:  # pragma: no cover
            return []

        # get the page of the season of the show
        logger.info('Getting the page of show id %d, season %d', show_id, season)
        params: dict[str, Any] = {'show': show_id, 'season': season, 'langs': '|'}
        r = self.session.get(
            self.server_url + '/ajax_loadShow.php',
            params=params,
            timeout=self.timeout,
            headers={'referer': f'{self.server_url}/show/{show_id}', 'X-Requested-With': 'XMLHttpRequest'},
        )
        r.raise_for_status()

        if not r.text:  # pragma: no cover
            # Provider wrongful return a status of 304 Not Modified with an empty content
            # raise_for_status won't raise exception for that status code
            logger.error('No data returned from provider')
            return []

        soup = ParserBeautifulSoup(r.text, ['lxml', 'html.parser'])

        # loop over subtitle rows
        subtitles = []
        for row in soup.select('tr.epeven'):
            cells = row('td')

            # ignore incomplete subtitles
            status = cells[5].text
            if '%' in status:  # pragma: no cover
                logger.debug('Ignoring subtitle with status %s', status)
                continue

            # read the item
            try:
                language = Language.fromaddic7ed(cells[3].text)
            except LanguageReverseError as error:
                logger.debug('Language error: %s, Ignoring subtitle', error)
                continue
            hearing_impaired = bool(cells[6].text)
            # season = int(cells[0].text)
            episode = int(cells[1].text)
            path = cells[2].a['href'][1:]
            page_link = f'{self.server_url}/{path}'
            title = cells[2].text
            release_group = cells[4].text
            subtitle_id = cells[9].a['href'][1:]

            subtitle = self.subtitle_class(
                language=language,
                subtitle_id=subtitle_id,
                hearing_impaired=hearing_impaired,
                page_link=page_link,
                series=series,
                season=season,
                episode=episode,
                title=title,
                year=year,
                release_group=release_group,
            )
            logger.debug('Found subtitle %r', subtitle)
            subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[Addic7edSubtitle]:
        """List all the subtitles for the video."""
        if not isinstance(video, Episode):  # pragma: no cover
            return []

        # lookup show_id
        show_id = self._get_show_id_with_alternative_names(video)

        # query for subtitles with the show_id
        if show_id is None:  # pragma: no cover
            logger.error('No show id found for %r (%r)', video.series, {'year': video.year})
            return []
        return [
            s
            for s in self.query(show_id, series=video.series, season=video.season, year=video.year)
            if s.language in languages and s.episode == video.episode
        ]

    def download_subtitle(self, subtitle: Addic7edSubtitle) -> None:
        """Download the content of the subtitle."""
        if not self.session:  # pragma: no cover
            raise NotInitializedProviderError
        # download the subtitle
        logger.info('Downloading subtitle %r', subtitle)
        r = self.session.get(
            f'{self.server_url}/{subtitle.subtitle_id}',
            headers={'Referer': subtitle.page_link},
            timeout=self.timeout,
        )
        r.raise_for_status()

        if not r.content:  # pragma: no cover
            # Provider returns a status of 304 Not Modified with an empty content
            # raise_for_status won't raise exception for that status code
            logger.debug('Unable to download subtitle. No data returned from provider')
            return

        # detect download limit exceeded
        if r.headers['Content-Type'] == 'text/html':  # pragma: no cover
            raise DownloadLimitExceeded

        subtitle.content = fix_line_ending(r.content)
