"""Provider for TVsubtitles.net."""

from __future__ import annotations

import contextlib
import io
import logging
import re
from typing import TYPE_CHECKING, ClassVar
from zipfile import ZipFile

from babelfish import Language, language_converters  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]
from requests import Session

from subliminal.cache import EPISODE_EXPIRATION_TIME, SHOW_EXPIRATION_TIME, region
from subliminal.exceptions import NotInitializedProviderError, ProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle, fix_line_ending
from subliminal.utils import sanitize
from subliminal.video import Episode, Video

from . import ParserBeautifulSoup, Provider

if TYPE_CHECKING:
    from collections.abc import Set

logger = logging.getLogger(__name__)

with contextlib.suppress(ValueError):
    language_converters.register('tvsubtitles = subliminal.converters.tvsubtitles:TVsubtitlesConverter')

link_re = re.compile(r'^(?P<series>.+?)(?: \(?\d{4}\)?| \((?:US|UK)\))? \((?P<first_year>\d{4})-\d{4}\)$')
episode_id_re = re.compile(r'^episode-\d+\.html$')
script_re = re.compile(r'var\s*s(?P<num>\d+)\s*=\s*\'(?P<string>[^\']+)\'')


class TVsubtitlesSubtitle(Subtitle):
    """TVsubtitles Subtitle."""

    provider_name: ClassVar[str] = 'tvsubtitles'

    series: str | None
    season: int | None
    episode: int | None
    year: int | None
    rip: str | None
    release: str | None

    def __init__(
        self,
        language: Language,
        subtitle_id: str,
        *,
        page_link: str | None = None,
        series: str | None = None,
        season: int | None = None,
        episode: int | None = None,
        year: int | None = None,
        rip: str | None = None,
        release: str | None = None,
    ) -> None:
        super().__init__(language, subtitle_id, page_link=page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.year = year
        self.rip = rip
        self.release = release

    @property
    def info(self) -> str:
        """Information about the subtitle."""
        return self.release or self.rip or ''

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        matches = guess_matches(
            video,
            {
                'title': self.series,
                'season': self.season,
                'episode': self.episode,
                'year': self.year,
                'release_group': self.release,
            },
        )

        # other properties
        if self.release is not None:
            matches |= guess_matches(video, guessit(self.release, {'type': 'episode'}), partial=True)
        if self.rip is not None:
            matches |= guess_matches(video, guessit(self.rip, {'type': 'episode'}), partial=True)

        return matches


class TVsubtitlesProvider(Provider):
    """TVsubtitles Provider."""

    languages: ClassVar[Set[Language]] = {Language('por', 'BR')} | {
        Language(lang)
        for lang in [
            'ara',
            'bul',
            'ces',
            'dan',
            'deu',
            'ell',
            'eng',
            'fin',
            'fra',
            'hun',
            'ita',
            'jpn',
            'kor',
            'nld',
            'pol',
            'por',
            'ron',
            'rus',
            'spa',
            'swe',
            'tur',
            'ukr',
            'zho',
        ]
    }
    video_types: ClassVar = (Episode,)
    server_url: ClassVar[str] = 'https://www.tvsubtitles.net'
    subtitle_class: ClassVar = TVsubtitlesSubtitle

    session: Session | None

    def __init__(self) -> None:
        self.session = None

    def initialize(self) -> None:
        """Initialize the provider."""
        self.session = Session()
        self.session.headers['User-Agent'] = self.user_agent
        self.session.headers['Referer'] = f'{self.server_url}/'
        self.session.headers['X-Requested-With'] = 'XMLHttpRequest'

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.session:
            raise NotInitializedProviderError
        self.session.close()

    @region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def search_show_id(self, series: str, year: int | None = None) -> int | None:
        """Search the show id from the `series` and `year`.

        :param str series: series of the episode.
        :param year: year of the series, if any.
        :type year: int
        :return: the show id, if any.
        :rtype: int

        """
        if not self.session:
            raise NotInitializedProviderError
        # make the search
        logger.info('Searching show id for %r', series)
        r = self.session.post(self.server_url + '/search.php', data={'qs': series}, timeout=10)
        r.raise_for_status()

        # get the series out of the suggestions
        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])
        sanitized = sanitize(series)
        show_id = None
        for suggestion in soup.select('div.left li div a', href=re.compile(r'\/tvshow-')):  # type: ignore[call-arg]
            match = link_re.match(suggestion.text)
            if not match:
                logger.error('Failed to match %s', suggestion.text)
                continue

            found_series = sanitize(match.group('series'))
            if found_series == sanitized:
                if year is not None and int(match.group('first_year')) != year:
                    logger.debug('Year does not match')
                    continue
                show_id = int(suggestion['href'][8:-5])  # type: ignore[arg-type]
                logger.debug('Found show id %d', show_id)
                break

        return show_id

    @region.cache_on_arguments(expiration_time=EPISODE_EXPIRATION_TIME)
    def get_episode_ids(self, show_id: int, season: int) -> dict[int, int]:
        """Get episode ids from the show id and the season.

        :param int show_id: show id.
        :param int season: season of the episode.
        :return: episode ids per episode number.
        :rtype: dict

        """
        if not self.session:
            raise NotInitializedProviderError
        # get the page of the season of the show
        logger.info('Getting the page of show id %d, season %d', show_id, season)
        r = self.session.get(self.server_url + f'/tvshow-{show_id:d}-{season:d}.html', timeout=10)
        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        # loop over episode rows
        episode_ids = {}
        for row in soup.select('table#table5 tr'):
            # skip rows that do not have a link to the episode page
            if not row('a', href=episode_id_re):
                continue

            # extract data from the cells
            cells = row('td')
            episode = int(cells[0].text.split('x')[1])
            episode_id = int(cells[1].a['href'][8:-5])
            episode_ids[episode] = episode_id

        if episode_ids:
            logger.debug('Found episode ids %r', episode_ids)
        else:
            logger.warning('No episode ids found')

        return episode_ids

    def query(
        self,
        show_id: int,
        series: str,
        season: int,
        episode: int | None,
        year: int | None = None,
    ) -> list[TVsubtitlesSubtitle]:
        """Query the episode with the show_id."""
        if not self.session:
            raise NotInitializedProviderError
        # get the episode ids
        episode_ids = self.get_episode_ids(show_id, season)

        if episode not in episode_ids:
            logger.error('Episode %d not found', episode)
            return []

        # get the episode page
        logger.info('Getting the page for episode %d', episode_ids[episode])
        r = self.session.get(self.server_url + f'/episode-{episode_ids[episode]:d}.html', timeout=10)
        soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])

        # loop over subtitles rows
        subtitles = []
        for row in soup.select('.subtitlen'):
            # read the item
            language = Language.fromtvsubtitles(row.h5.img['src'][13:-4])  # type: ignore[union-attr,index]
            subtitle_id = str(int(row.parent['href'][10:-5]))  # type: ignore[arg-type,index]
            page_link = self.server_url + f'/subtitle-{subtitle_id}.html'
            rip = row.find('p', title='rip').text.strip() or None  # type: ignore[union-attr]
            release = row.find('h5').text.strip() or None  # type: ignore[union-attr]

            subtitle = self.subtitle_class(
                language=language,
                subtitle_id=subtitle_id,
                page_link=page_link,
                series=series,
                season=season,
                episode=episode,
                year=year,
                rip=rip,
                release=release,
            )
            logger.debug('Found subtitle %s', subtitle)
            subtitles.append(subtitle)

        return subtitles

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[TVsubtitlesSubtitle]:
        """List all the subtitles for the video."""
        if not isinstance(video, Episode):
            return []

        # lookup show_id
        titles = [video.series, *video.alternative_series]
        title = None
        show_id = None
        for title in titles:
            show_id = self.search_show_id(title, video.year)
            if show_id is not None:
                break

        # query for subtitles with the show_id
        if show_id is not None and title is not None and video.episode is not None:
            return [
                s
                for s in self.query(show_id, title, video.season, video.episode, video.year)
                if s.language in languages and s.episode == video.episode
            ]

        logger.error('No show id found for %r (%r)', video.series, {'year': video.year})
        return []

    def download_subtitle(self, subtitle: TVsubtitlesSubtitle) -> None:
        """Download the content of the subtitle."""
        if not self.session:
            raise NotInitializedProviderError
        # download as a zip
        logger.info('Downloading subtitle %r', subtitle)
        url = self.server_url + f'/download-{subtitle.subtitle_id}.html'
        r = self.session.get(url, timeout=10)
        r.raise_for_status()

        # Not direct download
        if '</script>' in r.text:
            # Find the filename
            soup = ParserBeautifulSoup(r.content, ['lxml', 'html.parser'])
            parts = script_re.findall(soup.script.text)  # type: ignore[union-attr]
            filepath = ''.join(p[1] for p in parts)

            if not filepath:
                msg = f'Cannot find the subtitle name to download from {url}'
                raise ValueError(msg)

            direct_url = f'{self.server_url}/{filepath}'
            r = self.session.get(direct_url, timeout=10)
            r.raise_for_status()

        # open the zip
        with ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                msg = 'More than one file to unzip'
                raise ProviderError(msg)

            subtitle.content = fix_line_ending(zf.read(zf.namelist()[0]))
