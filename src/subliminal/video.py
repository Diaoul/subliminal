"""Video class and subclasses Episode and Movie."""

from __future__ import annotations

import logging
import os
import warnings
from typing import TYPE_CHECKING, Any

from guessit import guessit  # type: ignore[import-untyped]

from subliminal.utils import ensure_list, get_age, matches_extended_title

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Set
    from datetime import timedelta

    from babelfish import Country, Language  # type: ignore[import-untyped]

    from subliminal.subtitle import Subtitle

logger = logging.getLogger(__name__)

#: Video extensions
VIDEO_EXTENSIONS = (
    '.3g2',
    '.3gp',
    '.3gp2',
    '.3gpp',
    '.60d',
    '.ajp',
    '.asf',
    '.asx',
    '.avchd',
    '.avi',
    '.bik',
    '.bix',
    '.box',
    '.cam',
    '.dat',
    '.divx',
    '.dmf',
    '.dv',
    '.dvr-ms',
    '.evo',
    '.flc',
    '.fli',
    '.flic',
    '.flv',
    '.flx',
    '.gvi',
    '.gvp',
    '.h264',
    '.m1v',
    '.m2p',
    '.m2ts',
    '.m2v',
    '.m4e',
    '.m4v',
    '.mjp',
    '.mjpeg',
    '.mjpg',
    '.mk3d',
    '.mkv',
    '.moov',
    '.mov',
    '.movhd',
    '.movie',
    '.movx',
    '.mp4',
    '.mpe',
    '.mpeg',
    '.mpg',
    '.mpv',
    '.mpv2',
    '.mxf',
    '.nsv',
    '.nut',
    '.ogg',
    '.ogm',
    '.ogv',
    '.omf',
    '.ps',
    '.qt',
    '.ram',
    '.rm',
    '.rmvb',
    '.swf',
    '.ts',
    '.vfw',
    '.vid',
    '.video',
    '.viv',
    '.vivo',
    '.vob',
    '.vro',
    '.webm',
    '.wm',
    '.wmv',
    '.wmx',
    '.wrap',
    '.wvx',
    '.wx',
    '.x264',
    '.xvid',
)


class Video:
    """Base class for videos.

    Represent a video, existing or not.

    :param str name: name or path of the video.
    :param str source: source of the video (HDTV, Web, Blu-ray, ...).
    :param str release_group: release group of the video.
    :param str streaming_service: streaming_service of the video.
    :param str resolution: resolution of the video stream (480p, 720p, 1080p or 1080i).
    :param str video_codec: codec of the video stream.
    :param str audio_codec: codec of the main audio stream.
    :param float frame_rate: frame rate in frames per seconds.
    :param float duration: duration of the video in seconds.
    :param dict hashes: hashes of the video file by provider names.
    :param int size: size of the video file in bytes.
    :param subtitles: existing subtitles.
    :type subtitles: set[:class:`~subliminal.subtitle.Subtitle`]
    :param int year: year of the video.
    :param country: Country of the video.
    :type country: :class:`~babelfish.country.Country`
    :param str imdb_id: IMDb id of the video.
    :param str tmdb_id: TMDB id of the video.

    """

    #: Name or path of the video
    name: str

    #: Source of the video (HDTV, Web, Blu-ray, ...)
    source: str | None

    #: Release group of the video
    release_group: str | None

    #: Streaming service of the video
    streaming_service: str | None

    #: Resolution of the video stream (480p, 720p, 1080p or 1080i)
    resolution: str | None

    #: Codec of the video stream
    video_codec: str | None

    #: Codec of the main audio stream
    audio_codec: str | None

    #: Frame rate in frame per seconds
    frame_rate: float | None

    #: Duration of the video in seconds
    duration: float | None

    #: Hashes of the video file by provider names
    hashes: dict[str, str]

    #: Size of the video file in bytes
    size: int | None

    #: Title of the video
    title: str | None

    #: Year of the video
    year: int | None

    #: Country of the video
    country: Country | None

    #: IMDb id of the video
    imdb_id: str | None

    #: TMDB id of the video
    tmdb_id: int | None

    #: Existing subtitle languages
    subtitles: set[Subtitle]

    def __init__(
        self,
        name: str,
        *,
        source: str | None = None,
        release_group: str | None = None,
        resolution: str | None = None,
        streaming_service: str | None = None,
        video_codec: str | None = None,
        audio_codec: str | None = None,
        frame_rate: float | None = None,
        duration: float | None = None,
        hashes: Mapping[str, str] | None = None,
        size: int | None = None,
        subtitles: Set[Subtitle] | None = None,
        title: str | None = None,
        year: int | None = None,
        country: Country | None = None,
        imdb_id: str | None = None,
        tmdb_id: int | None = None,
    ) -> None:
        self.name = name
        self.source = source
        self.release_group = release_group
        self.streaming_service = streaming_service
        self.resolution = resolution
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.frame_rate = frame_rate
        self.duration = duration
        self.hashes = dict(hashes) if hashes is not None else {}
        self.size = size
        self.subtitles = set(subtitles) if subtitles is not None else set()
        self.title = title
        self.year = year
        self.country = country
        self.imdb_id = imdb_id
        self.tmdb_id = tmdb_id

    @property
    def exists(self) -> bool:
        """Test whether the video exists."""
        return os.path.exists(self.name)

    @property
    def age(self) -> timedelta:
        """Age of the video."""
        warnings.warn(
            'Use `get_age(use_ctime)` instead, to specify if modification time is used or also creation time.',
            DeprecationWarning,
            stacklevel=1,
        )
        return self.get_age(use_ctime=False)

    @property
    def subtitle_languages(self) -> set[Language]:
        """Set of languages from the subtitles already found for the video."""
        return {s.language for s in self.subtitles}

    @classmethod
    def fromguess(cls, name: str, guess: dict[str, Any]) -> Video:
        """Create an :class:`Episode` or a :class:`Movie` with the given `name` based on the `guess`.

        :param str name: name of the video.
        :param dict guess: guessed data.
        :raise: :class:`ValueError` if the `type` of the `guess` is invalid

        """
        if guess['type'] == 'episode':
            return Episode.fromguess(name, guess)

        if guess['type'] == 'movie':
            return Movie.fromguess(name, guess)

        msg = 'The guess must be an episode or a movie guess'  # pragma: no-cover
        raise ValueError(msg)

    @classmethod
    def fromname(cls, name: str) -> Video:
        """Shortcut for :meth:`fromguess` with a `guess` guessed from the `name`.

        :param str name: name of the video.

        """
        return cls.fromguess(name, guessit(name))

    def get_age(self, *, use_ctime: bool = False) -> timedelta:
        """Age of the video, with an option to take into account creation time."""
        return get_age(self.name, use_ctime=use_ctime)

    def __repr__(self) -> str:  # pragma: no cover
        return f'<{self.__class__.__name__} [{self.name!r}]>'

    def __hash__(self) -> int:
        return hash(self.name)


class Episode(Video):
    """Episode :class:`Video`.

    :param str series: series of the episode.
    :param int season: season number of the episode.
    :param int or list episodes: episode numbers of the episode.
    :param str title: title of the episode.
    :param bool original_series: whether the series is the first with this name.
    :param int tvdb_id: TVDB id of the episode.
    :param list alternative_series: alternative names of the series
    :param kwargs: additional parameters for the :class:`Video` constructor.

    """

    #: Series of the episode
    series: str

    #: Season number of the episode
    season: int

    #: Episode numbers of the episode
    episodes: list[int]

    #: Title of the episode
    title: str | None

    #: Year of series
    year: int | None

    #: The series is the first with this name
    original_series: bool

    #: IMDb id of the episode
    imdb_id: str | None

    #: IMDb id of the series
    series_imdb_id: str | None

    #: TMDB id of the episode
    tmdb_id: int | None

    #: TMDB id of the series
    series_tmdb_id: int | None

    #: TVDB id of the episode
    tvdb_id: int | None

    #: TVDB id of the series
    series_tvdb_id: int | None

    #: Alternative names of the series
    alternative_series: list[str]

    def __init__(
        self,
        name: str,
        series: str,
        season: int,
        episodes: int | Sequence[int] | None,
        *,
        original_series: bool = True,
        tvdb_id: int | None = None,
        series_tvdb_id: int | None = None,
        series_imdb_id: str | None = None,
        series_tmdb_id: int | None = None,
        alternative_series: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, **kwargs)

        self.series = series
        self.season = season
        self.episodes = ensure_list(episodes)
        self.original_series = original_series
        self.tvdb_id = tvdb_id
        self.series_tvdb_id = series_tvdb_id
        self.series_imdb_id = series_imdb_id
        self.series_tmdb_id = series_tmdb_id
        self.alternative_series = list(alternative_series) if alternative_series is not None else []

    @property
    def episode(self) -> int | None:
        """Episode number.

        With various episodes, return the minimum.
        """
        return min(self.episodes) if self.episodes else None

    def matches(self, series: str | None) -> bool:
        """Match the name to the series name, using alternative series names also.."""
        return matches_extended_title(series, self.series, self.alternative_series)

    @classmethod
    def fromguess(cls, name: str, guess: Mapping[str, Any]) -> Episode:
        """Return an :class:`Episode` from a dict guess."""
        if guess['type'] != 'episode':  # pragma: no-cover
            msg = 'The guess must be an episode guess'
            raise ValueError(msg)

        if 'title' not in guess or 'episode' not in guess:
            msg = 'Insufficient data to process the guess'
            raise ValueError(msg)

        return cls(
            name,
            guess['title'],
            guess.get('season', 1),
            guess.get('episode', []),
            title=guess.get('episode_title'),
            year=guess.get('year'),
            country=guess.get('country'),
            original_series='year' not in guess and 'country' not in guess,
            source=guess.get('source'),
            alternative_series=ensure_list(guess.get('alternative_title')),
            release_group=guess.get('release_group'),
            streaming_service=guess.get('streaming_service'),
            resolution=guess.get('screen_size'),
            video_codec=guess.get('video_codec'),
            audio_codec=guess.get('audio_codec'),
        )

    @classmethod
    def fromname(cls, name: str) -> Episode:
        """Return an :class:`Episode` from the file name."""
        return cls.fromguess(name, guessit(name, {'type': 'episode'}))

    def __repr__(self) -> str:
        return '<{cn} [{series}{country}{year} s{season:02d}e{episodes}]>'.format(
            cn=self.__class__.__name__,
            series=self.series,
            country=f' ({self.country})' if not self.original_series and self.country else '',
            year=f' ({self.year})' if not self.original_series and self.year else '',
            season=self.season,
            episodes='-'.join(f'{num:02d}' for num in self.episodes),
        )


class Movie(Video):
    """Movie :class:`Video`.

    :param str title: title of the movie.
    :param int year: year of the movie.
    :param country: Country of the movie.
    :type country: :class:`~babelfish.country.Country`
    :param list[str] alternative_titles: alternative titles of the movie
    :param kwargs: additional parameters for the :class:`Video` constructor.

    """

    #: Title of the movie
    title: str

    #: Year of the movie
    year: int | None

    #: Country of the movie
    country: Country | None

    #: IMDb id of the episode
    imdb_id: str | None

    #: TMDB id of the episode
    tmdb_id: int | None

    #: Alternative titles of the movie
    alternative_titles: list[str]

    def __init__(
        self,
        name: str,
        title: str,
        *,
        alternative_titles: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, title=title, **kwargs)
        self.alternative_titles = list(alternative_titles) if alternative_titles is not None else []

    def matches(self, title: str) -> bool:
        """Match the name to the movie title, using alternative titles also.."""
        return matches_extended_title(title, self.title, self.alternative_titles)

    @classmethod
    def fromguess(cls, name: str, guess: Mapping[str, Any]) -> Movie:
        """Return an :class:`Movie` from a dict guess."""
        if guess['type'] != 'movie':  # pragma: no-cover
            msg = 'The guess must be a movie guess'
            raise ValueError(msg)

        if 'title' not in guess:
            msg = 'Insufficient data to process the guess'
            raise ValueError(msg)

        return cls(
            name,
            title=guess['title'],
            source=guess.get('source'),
            release_group=guess.get('release_group'),
            streaming_service=guess.get('streaming_service'),
            resolution=guess.get('screen_size'),
            video_codec=guess.get('video_codec'),
            alternative_titles=ensure_list(guess.get('alternative_title')),
            audio_codec=guess.get('audio_codec'),
            year=guess.get('year'),
            country=guess.get('country'),
        )

    @classmethod
    def fromname(cls, name: str) -> Movie:
        """Return an :class:`Movie` from the file name."""
        return cls.fromguess(name, guessit(name, {'type': 'movie'}))

    def __repr__(self) -> str:
        return '<{cn} [{title}{open}{country}{sep}{year}{close}]>'.format(
            cn=self.__class__.__name__,
            title=self.title,
            year=self.year or '',
            country=self.country or '',
            open=' (' if self.year or self.country else '',
            sep=') (' if self.year and self.country else '',
            close=')' if self.year or self.country else '',
        )
