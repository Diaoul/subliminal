"""Video class and subclasses Episode and Movie."""

from __future__ import annotations

import logging
import os
import warnings
from typing import TYPE_CHECKING, Any

from attrs import define, field
from babelfish import Country, Language  # noqa: TC002  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]

from subliminal.exceptions import GuessingError
from subliminal.subtitle import Subtitle  # noqa: TC001
from subliminal.utils import ensure_list, get_age, matches_extended_title

if TYPE_CHECKING:
    # Do not put babelfish.Language and Subtitle in TYPE_CHECKING so cattrs.unstructure works
    from collections.abc import Mapping, Sequence
    from datetime import timedelta


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


@define
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
    :param hashes: hashes of the video file by provider names.
    :type hashes: dict[str, str]
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
    _name: str

    #: Source of the video (HDTV, Web, Blu-ray, ...)
    source: str | None = field(kw_only=True, default=None)

    #: Release group of the video
    release_group: str | None = field(kw_only=True, default=None)

    #: Streaming service of the video
    streaming_service: str | None = field(kw_only=True, default=None)

    #: Resolution of the video stream (480p, 720p, 1080p or 1080i)
    resolution: str | None = field(kw_only=True, default=None)

    #: Codec of the video stream
    video_codec: str | None = field(kw_only=True, default=None)

    #: Codec of the main audio stream
    audio_codec: str | None = field(kw_only=True, default=None)

    #: Frame rate in frame per seconds
    frame_rate: float | None = field(kw_only=True, default=None)

    #: Duration of the video in seconds
    duration: float | None = field(kw_only=True, default=None)

    #: Hashes of the video file by provider names
    hashes: dict[str, str] = field(kw_only=True, factory=dict)

    #: Size of the video file in bytes
    size: int | None = field(kw_only=True, default=None)

    #: Title of the video
    title: str | None = field(kw_only=True, default=None)

    #: Year of the video
    year: int | None = field(kw_only=True, default=None)

    #: Country of the video
    country: Country | None = field(kw_only=True, default=None)

    #: IMDb id of the video
    imdb_id: str | None = field(kw_only=True, default=None)

    #: TMDB id of the video
    tmdb_id: int | None = field(kw_only=True, default=None)

    #: Existing subtitle languages
    subtitles: set[Subtitle] = field(kw_only=True, factory=set)

    @property
    def name(self) -> str:
        """Video name, read-only."""
        return self._name

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
        raise GuessingError(msg)

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


def ensure_list_int(value: int | Sequence[int] | None) -> list[int]:
    """Return None if the value is non-positive."""
    return ensure_list(value)


@define
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
    episodes: list[int] = field(converter=ensure_list_int)

    #: Title of the episode
    title: str | None = field(kw_only=True, default=None)

    #: Year of series
    year: int | None = field(kw_only=True, default=None)

    #: The series is the first with this name
    original_series: bool = field(kw_only=True, default=True)

    #: IMDb id of the episode
    imdb_id: str | None = field(kw_only=True, default=None)

    #: IMDb id of the series
    series_imdb_id: str | None = field(kw_only=True, default=None)

    #: TMDB id of the episode
    tmdb_id: int | None = field(kw_only=True, default=None)

    #: TMDB id of the series
    series_tmdb_id: int | None = field(kw_only=True, default=None)

    #: TVDB id of the episode
    tvdb_id: int | None = field(kw_only=True, default=None)

    #: TVDB id of the series
    series_tvdb_id: int | None = field(kw_only=True, default=None)

    #: Alternative names of the series
    alternative_series: list[str] = field(kw_only=True, factory=list)

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
            msg = f'Insufficient data to process the guess for {name!r}'
            raise GuessingError(msg)

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

    def __hash__(self) -> int:
        return hash(self.name)


@define
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
    year: int | None = field(kw_only=True, default=None)

    #: Country of the movie
    country: Country | None = field(kw_only=True, default=None)

    #: IMDb id of the episode
    imdb_id: str | None = field(kw_only=True, default=None)

    #: TMDB id of the episode
    tmdb_id: int | None = field(kw_only=True, default=None)

    #: Alternative titles of the movie
    alternative_titles: list[str] = field(kw_only=True, factory=list)

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
            msg = f'Insufficient data to process the guess for {name!r}'
            raise GuessingError(msg)

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
        return '<{cn} [{title}{country}{year}]>'.format(
            cn=self.__class__.__name__,
            title=self.title,
            country=f' ({self.country})' if self.country else '',
            year=f' ({self.year})' if self.year else '',
        )

    def __hash__(self) -> int:
        return hash(self.name)
