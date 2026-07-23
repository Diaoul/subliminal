"""Video class and subclasses Episode and Movie."""

from __future__ import annotations

# Do not put timedelta and Sequence in TYPE_CHECKING for avoid error with docs
import logging
import os
import sys
from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence, Set
from datetime import timedelta  # noqa: TC003
from importlib.metadata import version as get_version
from typing import Any, TypedDict

if sys.version_info >= (3, 12):
    from typing import override
else:  # pragma: no cover
    from typing_extensions import override

# Do not put babelfish.Language and Subtitle in TYPE_CHECKING so cattrs.unstructure works
import cattrs
from attrs import define, field
from babelfish import Country, Language  # type: ignore[import-untyped]
from packaging.version import Version

from subliminal.exceptions import GuessingError
from subliminal.subtitle import Subtitle
from subliminal.utils import ensure_list, ensure_str, get_age, matches_extended_title, safely_guessit

logger = logging.getLogger(__name__)


class VideoExternalIds(TypedDict, total=False):
    """External Ids of a video."""

    imdb_id: str
    tmdb_id: str
    tvdb_id: str
    series_imdb_id: str
    series_tmdb_id: str
    series_tvdb_id: str


# fmt: off
#: Video extensions
VIDEO_EXTENSIONS = (
    '.3g2', '.3gp', '.3gp2', '.3gpp', '.60d', '.ajp', '.asf', '.asx', '.avchd', '.avi', '.bik', '.bix', '.box', '.cam',
    '.dat', '.divx', '.dmf', '.dv', '.dvr-ms', '.evo', '.flc', '.fli', '.flic', '.flv', '.flx', '.gvi', '.gvp', '.h264',
    '.m1v', '.m2p', '.m2ts', '.m2v', '.m4e', '.m4v', '.mjp', '.mjpeg', '.mjpg', '.mk3d', '.mkv', '.moov', '.mov',
    '.movhd', '.movie', '.movx', '.mp4', '.mpe', '.mpeg', '.mpg', '.mpv', '.mpv2', '.mxf', '.nsv', '.nut', '.ogg',
    '.ogm', '.ogv', '.omf', '.ps', '.qt', '.ram', '.rm', '.rmvb', '.swf', '.ts', '.vfw', '.vid', '.video', '.viv',
    '.vivo', '.vob', '.vro', '.webm', '.wm', '.wmv', '.wmx', '.wrap', '.wvx', '.wx', '.x264', '.xvid',
)
# fmt: on


@define(kw_only=True)
class Video:
    """Base class for videos.

    Represent a video, existing or not.

    :param str name: name or path of the video, read-only.
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
    :type subtitles: list[:class:`~subliminal.subtitle.Subtitle`]
    :param int year: year of the video.
    :param country: country of the video.
    :type country: :class:`~babelfish.country.Country`
    :param external_ids: external ids of the video from different databases (IMDb, TMDB, ...)
    :type external_ids: dict[str, str]
    :param bool use_ctime: use the latest of creation time and modification time for the video age

    """

    #: Name or path of the video, read-only.
    _name: str = field(kw_only=False)

    #: Source of the video (HDTV, Web, Blu-ray, ...)
    source: str | None = None

    #: Release group of the video
    release_group: str | None = None

    #: Streaming service of the video
    streaming_service: str | None = None

    #: Resolution of the video stream (480p, 720p, 1080p or 1080i)
    resolution: str | None = None

    #: Codec of the video stream
    video_codec: str | None = None

    #: Codec of the main audio stream
    audio_codec: str | None = None

    #: Frame rate in frame per seconds
    frame_rate: float | None = None

    #: Duration of the video in seconds
    duration: float | None = None

    #: Hashes of the video file by provider names
    hashes: dict[str, str] = field(factory=dict, eq=False)

    #: Size of the video file in bytes
    size: int | None = None

    #: Title of the video
    title: str | None = None

    #: Year of the video
    year: int | None = None

    #: Country of the video
    country: Country | None = None

    #: Use the latest of creation time and modification time for the video age
    use_ctime: bool = True

    #: External ids of the video from different databases (IMDb, TMDB, ...)
    external_ids: VideoExternalIds = field(factory=VideoExternalIds, eq=False)

    #: Existing subtitles
    subtitles: list[Subtitle] = field(factory=list, eq=False)

    @property
    def name(self) -> str:
        """Name or path of the video, read-only."""
        # Because it is used in __hash__, it needs to be immutable.
        return self._name

    @property
    def exists(self) -> bool:
        """Test whether the video exists."""
        return os.path.exists(self.name)

    @property
    def age(self) -> timedelta:
        """Age of the video."""
        return get_age(self.name, use_ctime=self.use_ctime)

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
        return cls.fromguess(name, safely_guessit(name))

    def update(self, update: Mapping[str, Any]) -> None:
        """Update video attributes with the dict items."""
        for k, v in update.items():
            if not hasattr(self, k):
                msg = f'Attribute does not exist, skip setting {self.__class__.__name__}.{k} to {v}'
                logger.warning(msg)
                continue

            attribute = getattr(self, k)
            # Do not replace containers, but extend/update them
            # List attribute
            if isinstance(attribute, MutableSequence):
                if not isinstance(v, Sequence):
                    msg = f'List cannot be extended, skip setting {self.__class__.__name__}.{k} to {v}'
                    logger.warning(msg)
                    continue
                msg = f'Extend list attribute {self.__class__.__name__}.{k} with {v}'
                logger.debug(msg)
                attribute.extend(v)

            # Dict attribute
            elif isinstance(attribute, MutableMapping):
                if not isinstance(v, Mapping):
                    msg = f'Dict cannot be updated, skip setting {self.__class__.__name__}.{k} to {v}'
                    logger.warning(msg)
                    continue
                msg = f'Update dict attribute {self.__class__.__name__}.{k} with {v}'
                logger.debug(msg)
                attribute.update(v)

            # Set attribute (do not use MutableSet as it does not define the update method)
            elif isinstance(attribute, set):
                if not isinstance(v, Set):
                    msg = f'Set cannot be updated, skip setting {self.__class__.__name__}.{k} to {v}'
                    logger.warning(msg)
                    continue
                msg = f'Update set attribute {self.__class__.__name__}.{k} with {v}'
                logger.debug(msg)
                attribute.update(v)

            # Not a container, set the value
            else:
                setattr(self, k, v)

    def matches(self, title: str) -> bool:  # pragma: no cover
        """Match the name to the video title."""
        return matches_extended_title(title, self.title)

    @override
    def __hash__(self) -> int:  # pragma: no cover
        # This method needs to be overridden in subclasses, otherwise attrs overwrites it with a default method
        return hash(self.name)

    @override
    def __repr__(self) -> str:  # pragma: no cover
        return f'<{self.__class__.__name__} [{self.name!r}]>'


def ensure_list_int(value: int | Sequence[int] | None) -> list[int]:
    """Return None if the value is non-positive."""
    return ensure_list(value)


@define(kw_only=True)
class Episode(Video):
    """Episode :class:`Video`.

    :param str series: series of the episode.
    :param int season: season number of the episode.
    :param int or list episodes: episode numbers of the episode.
    :param str title: title of the episode.
    :param int year: year of the series.
    :param bool original_series: whether the series is the first with this name.
    :param external_ids: external ids of the episode from different databases (IMDb, TMDB, Series IMDb, ...)
    :type external_ids: dict[str, str]
    :param list alternative_series: alternative names of the series
    :param kwargs: additional parameters for the :class:`Video` constructor.

    """

    #: Series of the episode
    series: str = field(kw_only=False)

    #: Season number of the episode
    season: int = field(kw_only=False)

    #: Episode numbers of the episode
    episodes: list[int] = field(kw_only=False, converter=ensure_list_int)

    #: Title of the episode
    title: str | None = None

    #: Year of series
    year: int | None = None

    #: The series is the first with this name
    original_series: bool = True

    #: External ids of the episode from different databases (IMDb, TMDB, Series IMDb, ...)
    external_ids: VideoExternalIds = field(factory=VideoExternalIds, eq=False)

    #: Alternative names of the series
    alternative_series: list[str] = field(factory=list)

    @property
    def episode(self) -> int | None:
        """Episode number.

        With various episodes, return the minimum.
        """
        return min(self.episodes) if self.episodes else None

    @override
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
            series=ensure_str(guess['title']),
            season=guess.get('season', 1),
            episodes=guess.get('episode', []),
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

    @override
    @classmethod
    def fromname(cls, name: str) -> Episode:
        """Return an :class:`Episode` from the file name."""
        return cls.fromguess(name, safely_guessit(name, {'type': 'episode'}))

    @override
    def matches(self, series: str | None) -> bool:
        """Match the name to the series name, using alternative series names also."""
        return matches_extended_title(series, self.series, self.alternative_series)

    @override
    def __hash__(self) -> int:
        return hash(self.name)

    @override
    def __repr__(self) -> str:
        return '<{cn} [{series}{country}{year} s{season:02d}e{episodes}]>'.format(
            cn=self.__class__.__name__,
            series=self.series,
            country=f' ({self.country})' if not self.original_series and self.country else '',
            year=f' ({self.year})' if not self.original_series and self.year else '',
            season=self.season,
            episodes='-'.join(f'{num:02d}' for num in self.episodes),
        )


@define(kw_only=True)
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
    title: str = field(kw_only=False)

    #: Year of the movie
    year: int | None = None

    #: Country of the movie
    country: Country | None = None

    #: External ids of the movie from different databases (IMDb, TMDB, ...)
    external_ids: VideoExternalIds = field(factory=VideoExternalIds, eq=False)

    #: Alternative titles of the movie
    alternative_titles: list[str] = field(factory=list)

    @override
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

    @override
    @classmethod
    def fromname(cls, name: str) -> Movie:
        """Return an :class:`Movie` from the file name."""
        return cls.fromguess(name, safely_guessit(name, {'type': 'movie'}))

    @override
    def matches(self, title: str) -> bool:
        """Match the name to the movie title, using alternative titles also."""
        return matches_extended_title(title, self.title, self.alternative_titles)

    @override
    def __hash__(self) -> int:
        return hash(self.name)

    @override
    def __repr__(self) -> str:
        return '<{cn} [{title}{country}{year}]>'.format(
            cn=self.__class__.__name__,
            title=self.title,
            country=f' ({self.country})' if self.country else '',
            year=f' ({self.year})' if self.year else '',
        )


converter = cattrs.Converter()


@converter.register_structure_hook
def subtitle_structure_hook(val: Any, _: Any) -> Subtitle:
    """This hook will be registered for structuring :class:`~subliminal.subtitle.Subtitle`s."""
    if not isinstance(val, dict):  # pragma: no cover
        msg = f'A dict was expected to structure a Subtitle: {val}'
        raise TypeError(msg)
    val = {k: v for k, v in val.items() if k not in ['provider_name']}
    return Subtitle(**val)


@converter.register_unstructure_hook
def subtitle_unstructure_hook(val: Subtitle) -> dict[str, Any]:
    """This hook will be registered for unstructuring :class:`~subliminal.subtitle.Subtitle`s."""
    return {
        'language': val.language,
        'subtitle_id': val.subtitle_id,
        'provider_name': val.provider_name,
        # 'category': val.category,
        'embedded': val.embedded,
    }


# Special un/structure hooks for languages
if Version(get_version('babelfish')) <= Version('0.6.1'):  # pragma: no cover

    @converter.register_structure_hook
    def language_structure_hook(val: str, _: Any) -> Language:
        """This hook will be registered for structuring :class:`~babelfish.language.Language`s."""
        return Language.fromietf(val)

    @converter.register_unstructure_hook
    def language_unstructure_hook(val: Language) -> str:
        """This hook will be registered for unstructuring :class:`~babelfish.language.Language`s."""
        return f'{val.alpha3}-{val.country.alpha2}-{val.script.code}'
