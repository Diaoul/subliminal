"""Core functions."""

from __future__ import annotations

import itertools
import logging
import operator
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from babelfish import Language, LanguageReverseError  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]

from .archives import ARCHIVE_ERRORS, ARCHIVE_EXTENSIONS, is_supported_archive, scan_archive
from .exceptions import ArchiveError
from .extensions import (
    discarded_episode_refiners,
    discarded_movie_refiners,
    get_default_providers,
    get_default_refiners,
    provider_manager,
    refiner_manager,
)
from .score import compute_score as default_compute_score
from .subtitle import SUBTITLE_EXTENSIONS, LanguageType, Subtitle
from .utils import get_age, handle_exception
from .video import VIDEO_EXTENSIONS, Episode, Movie, Video

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence, Set
    from datetime import timedelta
    from types import TracebackType

    from subliminal.providers import Provider
    from subliminal.score import ComputeScore

logger = logging.getLogger(__name__)


class ProviderPool:
    """A pool of providers with the same API as a single :class:`~subliminal.providers.Provider`.

    It has a few extra features:

        * Lazy loads providers when needed and supports the `with` statement to :meth:`terminate`
          the providers on exit.
        * Automatically discard providers on failure.

    :param list providers: name of providers to use, if not all.
    :param dict provider_configs: provider configuration as keyword arguments per provider name to pass when
        instantiating the :class:`~subliminal.providers.Provider`.

    """

    #: Name of providers to use
    providers: Sequence[str]

    #: Provider configuration
    provider_configs: Mapping[str, Any]

    #: Initialized providers
    initialized_providers: dict[str, Provider]

    #: Discarded providers
    discarded_providers: set[str]

    def __init__(
        self,
        providers: Sequence[str] | None = None,
        provider_configs: Mapping[str, Any] | None = None,
    ) -> None:
        self.providers = providers if providers is not None else get_default_providers()
        self.provider_configs = provider_configs or {}
        self.initialized_providers = {}
        self.discarded_providers = set()

    def __enter__(self) -> ProviderPool:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.terminate()

    def __getitem__(self, name: str) -> Provider:
        if name not in self.providers:
            raise KeyError

        if name not in self.initialized_providers:
            logger.info('Initializing provider %s', name)
            provider = provider_manager[name].plugin(**self.provider_configs.get(name, {}))
            provider.initialize()
            self.initialized_providers[name] = provider

        return self.initialized_providers[name]

    def __delitem__(self, name: str) -> None:
        if name not in self.initialized_providers:
            raise KeyError(name)

        try:
            logger.info('Terminating provider %s', name)
            self.initialized_providers[name].terminate()
        except Exception as e:  # noqa: BLE001  # pragma: no cover
            handle_exception(e, f'Provider {name} improperly terminated')

        del self.initialized_providers[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self.initialized_providers)

    def list_subtitles_provider(self, provider: str, video: Video, languages: Set[Language]) -> list[Subtitle]:
        """List subtitles with a single provider.

        The video and languages are checked against the provider.

        :param str provider: name of the provider.
        :param video: video to list subtitles for.
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to search for.
        :type languages: set of :class:`~babelfish.language.Language`
        :return: found subtitles.
        :rtype: list of :class:`~subliminal.subtitle.Subtitle` or None

        """
        # check video validity
        if not provider_manager[provider].plugin.check(video):
            logger.info('Skipping provider %r: not a valid video', provider)
            return []

        # check supported languages
        provider_languages = provider_manager[provider].plugin.check_languages(languages)
        if not provider_languages:
            logger.info('Skipping provider %r: no language to search for', provider)
            return []

        # list subtitles
        logger.info('Listing subtitles with provider %r and languages %r', provider, provider_languages)
        try:
            return self[provider].list_subtitles(video, provider_languages)
        except Exception as e:  # noqa: BLE001
            handle_exception(e, f'Provider {provider}')

        return []

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[Subtitle]:
        """List subtitles.

        :param video: video to list subtitles for.
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to search for.
        :type languages: set of :class:`~babelfish.language.Language`
        :return: found subtitles.
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`

        """
        subtitles = []

        for name in self.providers:
            # check discarded providers
            if name in self.discarded_providers:
                logger.debug('Skipping discarded provider %r', name)
                continue

            # list subtitles
            provider_subtitles = self.list_subtitles_provider(name, video, languages)
            if provider_subtitles is None:
                logger.info('Discarding provider %s', name)
                self.discarded_providers.add(name)
                continue

            # add the subtitles
            subtitles.extend(provider_subtitles)

        return subtitles

    def download_subtitle(self, subtitle: Subtitle) -> bool:
        """Download `subtitle`'s :attr:`~subliminal.subtitle.Subtitle.content`.

        :param subtitle: subtitle to download.
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :return: `True` if the subtitle has been successfully downloaded, `False` otherwise.
        :rtype: bool

        """
        # check discarded providers
        if subtitle.provider_name in self.discarded_providers:
            logger.warning('Provider %r is discarded', subtitle.provider_name)
            return False

        logger.info('Downloading subtitle %r', subtitle)
        try:
            self[subtitle.provider_name].download_subtitle(subtitle)
        except ARCHIVE_ERRORS:  # type: ignore[misc]  # pragma: no cover
            logger.exception('Bad archive for subtitle %r', subtitle)
        except Exception as e:  # noqa: BLE001
            handle_exception(e, f'Discarding provider {subtitle.provider_name}')
            self.discarded_providers.add(subtitle.provider_name)

        # check subtitle validity
        if not subtitle.is_valid():
            logger.error('Invalid subtitle')
            return False

        return True

    def download_best_subtitles(
        self,
        subtitles: Sequence[Subtitle],
        video: Video,
        languages: Set[Language],
        *,
        min_score: int = 0,
        hearing_impaired: bool | None = None,
        foreign_only: bool | None = None,
        only_one: bool = False,
        compute_score: ComputeScore | None = None,
        ignore_subtitles: Sequence[str] | None = None,
    ) -> list[Subtitle]:
        """Download the best matching subtitles.

        :param subtitles: the subtitles to use.
        :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`
        :param video: video to download subtitles for.
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to download.
        :type languages: set of :class:`~babelfish.language.Language`
        :param int min_score: minimum score for a subtitle to be downloaded.
        :param (bool | None) hearing_impaired: hearing impaired preference (yes/no/indifferent).
        :param (bool | None) foreign_only: foreign only preference (yes/no/indifferent).
        :param bool only_one: download only one subtitle, not one per language.
        :param compute_score: function that takes `subtitle` and `video` as positional arguments,
            and returns the score.
        :param ignore_subtitles: list of subtitle ids to ignore (None defaults to an empty list).
        :return: downloaded subtitles.
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`

        """
        compute_score = compute_score or default_compute_score
        ignore_subtitles = ignore_subtitles or []

        # ignore subtitles
        subtitles = [s for s in subtitles if s.id not in ignore_subtitles]

        # sort by hearing impaired and foreign only
        language_type = LanguageType.from_flags(hearing_impaired=hearing_impaired, foreign_only=foreign_only)
        if language_type != LanguageType.UNKNOWN:
            logger.info('Sort subtitles by %s types first', language_type.value)
            subtitles = sorted(
                subtitles,
                key=lambda s: s.language_type == language_type,
                reverse=True,
            )

        # sort subtitles by score
        scored_subtitles = sorted(
            [(s, compute_score(s, video)) for s in subtitles],
            key=operator.itemgetter(1),
            reverse=True,
        )

        # download best subtitles, falling back on the next on error
        downloaded_subtitles: list[Subtitle] = []
        for subtitle, score in scored_subtitles:
            # check score
            if score < min_score:
                logger.info('Score %d is below min_score (%d)', score, min_score)
                break

            # check downloaded languages
            if subtitle.language in {s.language for s in downloaded_subtitles}:
                logger.debug('Skipping subtitle: %r already downloaded', subtitle.language)
                continue

            # download
            if self.download_subtitle(subtitle):
                downloaded_subtitles.append(subtitle)

            # stop when all languages are downloaded
            if {s.language for s in downloaded_subtitles} == languages:
                logger.debug('All languages downloaded')
                break

            # stop if only one subtitle is requested
            if only_one and len(downloaded_subtitles) > 0:
                logger.debug('Only one subtitle downloaded')
                break

        return downloaded_subtitles

    def terminate(self) -> None:
        """Terminate all the :attr:`initialized_providers`."""
        logger.debug('Terminating initialized providers')
        for name in list(self.initialized_providers):
            del self[name]


class AsyncProviderPool(ProviderPool):
    """Subclass of :class:`ProviderPool` with asynchronous support for :meth:`~ProviderPool.list_subtitles`.

    :param int max_workers: maximum number of threads to use. If `None`, :attr:`max_workers` will be set
        to the number of :attr:`~ProviderPool.providers`.

    """

    #: Maximum number of threads to use.
    max_workers: int

    def __init__(self, max_workers: int | None = None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        #: Maximum number of threads to use
        self.max_workers = max_workers or len(self.providers)

    def list_subtitles_provider_tuple(
        self,
        provider: str,
        video: Video,
        languages: Set[Language],
    ) -> tuple[str, list[Subtitle]]:
        """List subtitles with a single provider, multi-threaded."""
        return provider, super().list_subtitles_provider(provider, video, languages)

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[Subtitle]:
        """List subtitles, multi-threaded."""
        subtitles: list[Subtitle] = []

        # Avoid raising a ValueError with `ThreadPoolExecutor(self.max_workers)`
        if self.max_workers == 0:
            return subtitles

        with ThreadPoolExecutor(self.max_workers) as executor:
            executor_map = executor.map(
                self.list_subtitles_provider_tuple,
                self.providers,
                itertools.repeat(video, len(self.providers)),
                itertools.repeat(languages, len(self.providers)),
            )
            for provider, provider_subtitles in executor_map:
                # discard provider that failed
                if provider_subtitles is None:
                    logger.info('Discarding provider %s', provider)
                    self.discarded_providers.add(provider)
                    continue

                # add subtitles
                subtitles.extend(provider_subtitles)

        return subtitles


def check_video(
    video: Video,
    *,
    languages: Set[Language] | None = None,
    age: timedelta | None = None,
    use_ctime: bool = False,
    undefined: bool = False,
) -> bool:
    """Perform some checks on the `video`.

    All the checks are optional. Return `False` if any of this check fails:

        * `languages` already exist in `video`'s :attr:`~subliminal.video.Video.subtitle_languages`.
        * `video` is older than `age`.
        * `video` has an `undefined` language in :attr:`~subliminal.video.Video.subtitle_languages`.

    :param video: video to check.
    :type video: :class:`~subliminal.video.Video`
    :param languages: desired languages.
    :type languages: set of :class:`~babelfish.language.Language`
    :param datetime.timedelta age: maximum age of the video.
    :param bool use_ctime: use the latest of creation time and modification time to compute the age of the video,
        instead of just modification time.
    :param bool undefined: fail on existing undefined language.
    :return: `True` if the video passes the checks, `False` otherwise.
    :rtype: bool

    """
    # language test
    if languages and not (languages - video.subtitle_languages):
        logger.debug('All languages %r exist', languages)
        return False

    # age test
    file_age = video.get_age(use_ctime=use_ctime)
    if age and file_age > age:
        logger.debug('Video is older than %r', age)
        return False

    # undefined test
    if undefined and Language('und') in video.subtitle_languages:
        logger.debug('Undefined language found')
        return False

    return True


def parse_subtitle_filename(subtitle_filename: str, video_filename: str) -> Subtitle | None:
    """Parse the subtitle filename to extract the language."""
    fileroot, fileext = os.path.splitext(video_filename)

    # keep only valid subtitle filenames
    if not subtitle_filename.startswith(fileroot) or not subtitle_filename.lower().endswith(SUBTITLE_EXTENSIONS):
        return None

    # extract the potential language code
    language = Language('und')
    language_code = subtitle_filename[len(fileroot) : -len(os.path.splitext(subtitle_filename)[1])]
    language_code = language_code.replace(fileext, '').replace('_', '-')[1:]
    if language_code:
        try:
            language = Language.fromietf(language_code)
        except (ValueError, LanguageReverseError):
            logger.exception('Cannot parse language code %r', language_code)

    # TODO: extract the hearing_impaired or foreign_only attribute

    return Subtitle(language, subtitle_id=subtitle_filename)


def search_external_subtitles(
    path: str | os.PathLike,
    *,
    directory: str | os.PathLike | None = None,
) -> dict[str, Subtitle]:
    """Search for external subtitles from a video `path` and their associated language.

    Unless `directory` is provided, search will be made in the same directory as the video file.

    :param str path: path to the video.
    :param str directory: directory to search for subtitles.
    :return: found subtitles with their languages.
    :rtype: dict

    """
    # split path
    dirpath, filename = os.path.split(path)
    dirpath = dirpath or '.'

    # search for subtitles
    subtitles = {}
    for p in os.listdir(directory or dirpath):
        subtitle = parse_subtitle_filename(p, filename)
        if subtitle is None:
            continue

        subtitles[p] = subtitle

    logger.debug('Found subtitles %r', subtitles)

    return subtitles


def scan_name(path: str | os.PathLike, name: str | None = None) -> Video:
    """Scan a video from a `path` that does not exist.

    :param str path: non-existing path to the video.
    :param str name: if defined, name to use with guessit instead of the path.
    :return: the scanned video.
    :rtype: :class:`~subliminal.video.Video`
    """
    path = os.fspath(path)
    repl = name if name else path
    return Video.fromguess(path, guessit(repl))


def scan_video(path: str | os.PathLike, name: str | None = None) -> Video:
    """Scan a video from a `path`.

    :param str path: existing path to the video.
    :param str name: if defined, name to use with guessit instead of the path.
    :return: the scanned video.
    :rtype: :class:`~subliminal.video.Video`
    :raises: :class:`ValueError`: video path is not well defined.
    """
    path = os.fspath(path)
    # check for non-existing path
    if not os.path.exists(path):
        msg = 'Path does not exist'
        raise ValueError(msg)

    # check video extension
    if not path.lower().endswith(VIDEO_EXTENSIONS):
        msg = f'{os.path.splitext(path)[1]!r} is not a valid video extension'
        raise ValueError(msg)

    dirpath, filename = os.path.split(path)
    repl = name if name else path
    if name:
        logger.info('Scanning video %r in %r, with replacement name %r', filename, dirpath, repl)
    else:
        logger.info('Scanning video %r in %r', filename, dirpath)

    # guess
    video = Video.fromguess(path, guessit(repl))

    # size
    video.size = os.path.getsize(path)
    logger.debug('Size is %d', video.size)

    return video


def scan_videos(
    path: str | os.PathLike,
    *,
    age: timedelta | None = None,
    use_ctime: bool = False,
    archives: bool = True,
    name: str | None = None,
) -> list[Video]:
    """Scan `path` for videos and their subtitles.

    See :func:`refine` to find additional information for the video.

    :param str path: existing directory path to scan.
    :param datetime.timedelta age: maximum age of the video or archive.
    :param bool use_ctime: use the latest of creation time and modification time to compute the age of the video,
        instead of just modification time.
    :param bool archives: scan videos in archives.
    :param str name: name to use with guessit instead of the path.
    :return: the scanned videos.
    :rtype: list of :class:`~subliminal.video.Video`
    :raises: :class:`ValueError`: video path is not well defined.
    """
    path = os.fspath(path)
    # check for non-existing path
    if not os.path.exists(path):
        msg = 'Path does not exist'
        raise ValueError(msg)

    # check for non-directory path
    if not os.path.isdir(path):
        msg = 'Path is not a directory'
        raise ValueError(msg)

    # walk the path
    videos = []
    for dirpath, dirnames, filenames in os.walk(path):
        logger.debug('Walking directory %r', dirpath)

        # remove badly encoded and hidden dirnames
        for dirname in list(dirnames):
            if dirname.startswith('.'):
                logger.debug('Skipping hidden dirname %r in %r', dirname, dirpath)
                dirnames.remove(dirname)
            # Skip Sample folder
            if dirname.lower() == 'sample':
                logger.debug('Skipping sample dirname %r in %r', dirname, dirpath)
                dirnames.remove(dirname)

        # scan for videos
        for filename in sorted(filenames):
            # filter on videos and archives
            if not filename.lower().endswith(VIDEO_EXTENSIONS) and not (
                archives and filename.lower().endswith(ARCHIVE_EXTENSIONS)
            ):
                continue

            # skip hidden files
            if filename.startswith('.'):
                logger.debug('Skipping hidden filename %r in %r', filename, dirpath)
                continue
            # skip 'sample' media files
            if os.path.splitext(filename)[0].lower() == 'sample':
                logger.debug('Skipping sample filename %r in %r', filename, dirpath)
                continue

            # reconstruct the file path
            filepath = os.path.join(dirpath, filename)

            # skip links
            if os.path.islink(filepath):
                logger.debug('Skipping link %r in %r', filename, dirpath)
                continue

            # skip old files
            try:
                file_age = get_age(filepath, use_ctime=use_ctime)
            except ValueError:  # pragma: no cover
                logger.warning('Could not get age of file %r in %r', filename, dirpath)
                continue
            else:
                if age and file_age > age:
                    logger.debug('Skipping old file %r in %r', filename, dirpath)
                    continue

            # scan
            if filename.lower().endswith(VIDEO_EXTENSIONS):  # video
                try:
                    video = scan_video(filepath, name=name)
                except ValueError:  # pragma: no cover
                    logger.exception('Error scanning video')
                    continue
            elif archives and is_supported_archive(filename):  # archive
                try:
                    video = scan_archive(filepath, name=name)
                except (ArchiveError, ValueError):  # pragma: no cover
                    logger.exception('Error scanning archive')
                    continue
            else:  # pragma: no cover
                msg = f'Unsupported file {filename!r}'
                raise ValueError(msg)

            videos.append(video)

    return videos


def refine(
    video: Video,
    *,
    refiners: Sequence[str] | None = None,
    refiner_configs: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> Video:
    """Refine a video using :ref:`refiners`.

    .. note::

        Exceptions raised in refiners are silently passed and logged.

    :param video: the video to refine.
    :type video: :class:`~subliminal.video.Video`
    :param Sequence refiners: refiners to select. None defaults to all refiners.
    :param dict refiner_configs: refiner configuration as keyword arguments per refiner name to pass when
        calling the refine method
    :param kwargs: additional parameters for the :func:`~subliminal.refiners.refine` functions.

    """
    refiners = refiners if refiners is not None else get_default_refiners()
    if isinstance(video, Movie):
        refiners = [r for r in refiners if r not in discarded_movie_refiners]
    if isinstance(video, Episode):
        refiners = [r for r in refiners if r not in discarded_episode_refiners]

    for refiner in refiners:
        logger.info('Refining video with %s', refiner)
        try:
            refiner_manager[refiner].plugin(video, **dict((refiner_configs or {}).get(refiner, {}), **kwargs))
        except Exception as e:  # noqa: BLE001
            handle_exception(e, f'Failed to refine video {video.name!r}')
    return video


def list_subtitles(
    videos: Set[Video],
    languages: Set[Language],
    *,
    pool_class: type[ProviderPool] = ProviderPool,
    **kwargs: Any,
) -> dict[Video, list[Subtitle]]:
    """List subtitles.

    The `videos` must pass the `languages` check of :func:`check_video`.

    :param videos: videos to list subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to search for.
    :type languages: set of :class:`~babelfish.language.Language`
    :param pool_class: class to use as provider pool.
    :type pool_class: :class:`ProviderPool`, :class:`AsyncProviderPool` or similar
    :param kwargs: additional parameters for the provided `pool_class` constructor.
    :return: found subtitles per video.
    :rtype: dict of :class:`~subliminal.video.Video` to list of :class:`~subliminal.subtitle.Subtitle`

    """
    listed_subtitles: dict[Video, list[Subtitle]] = defaultdict(list)

    # check videos
    checked_videos = []
    for video in videos:
        if not check_video(video, languages=languages):
            logger.info('Skipping video %r', video)
            continue
        checked_videos.append(video)

    # return immediately if no video passed the checks
    if not checked_videos:
        return listed_subtitles

    # list subtitles
    with pool_class(**kwargs) as pool:
        for video in checked_videos:
            logger.info('Listing subtitles for %r', video)
            subtitles = pool.list_subtitles(video, languages - video.subtitle_languages)
            listed_subtitles[video].extend(subtitles)
            logger.info('Found %d subtitle(s)', len(subtitles))

    return listed_subtitles


def download_subtitles(
    subtitles: Sequence[Subtitle],
    *,
    pool_class: type[ProviderPool] = ProviderPool,
    **kwargs: Any,
) -> None:
    """Download :attr:`~subliminal.subtitle.Subtitle.content` of `subtitles`.

    :param subtitles: subtitles to download.
    :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`
    :param pool_class: class to use as provider pool.
    :type pool_class: :class:`ProviderPool`, :class:`AsyncProviderPool` or similar
    :param kwargs: additional parameters for the provided `pool_class` constructor.

    """
    with pool_class(**kwargs) as pool:
        for subtitle in subtitles:
            logger.info('Downloading subtitle %r', subtitle)
            pool.download_subtitle(subtitle)


def download_best_subtitles(
    videos: Set[Video],
    languages: Set[Language],
    *,
    min_score: int = 0,
    hearing_impaired: bool | None = None,
    foreign_only: bool | None = None,
    only_one: bool = False,
    compute_score: ComputeScore | None = None,
    pool_class: type[ProviderPool] = ProviderPool,
    **kwargs: Any,
) -> dict[Video, list[Subtitle]]:
    """List and download the best matching subtitles.

    The `videos` must pass the `languages` and `undefined` (`only_one`) checks of :func:`check_video`.

    :param videos: videos to download subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to download.
    :type languages: set of :class:`~babelfish.language.Language`
    :param int min_score: minimum score for a subtitle to be downloaded.
    :param (bool | None) hearing_impaired: hearing impaired preference (yes/no/indifferent).
    :param (bool | None) foreign_only: foreign only preference (yes/no/indifferent).
    :param bool only_one: download only one subtitle, not one per language.
    :param compute_score: function that takes `subtitle` and `video` as positional arguments,
        `hearing_impaired` as keyword argument and returns the score.
    :param pool_class: class to use as provider pool.
    :type pool_class: :class:`ProviderPool`, :class:`AsyncProviderPool` or similar
    :param kwargs: additional parameters for the provided `pool_class` constructor.
    :return: downloaded subtitles per video.
    :rtype: dict of :class:`~subliminal.video.Video` to list of :class:`~subliminal.subtitle.Subtitle`

    """
    downloaded_subtitles: dict[Video, list[Subtitle]] = defaultdict(list)

    # check videos
    checked_videos = []
    for video in videos:
        if not check_video(video, languages=languages, undefined=only_one):
            logger.info('Skipping video %r', video)
            continue
        checked_videos.append(video)

    # return immediately if no video passed the checks
    if not checked_videos:
        return downloaded_subtitles

    # download best subtitles
    with pool_class(**kwargs) as pool:
        for video in checked_videos:
            logger.info('Downloading best subtitles for %r', video)
            subtitles = pool.download_best_subtitles(
                pool.list_subtitles(video, languages - video.subtitle_languages),
                video,
                languages,
                min_score=min_score,
                hearing_impaired=hearing_impaired,
                foreign_only=foreign_only,
                only_one=only_one,
                compute_score=compute_score,
            )
            logger.info('Downloaded %d subtitle(s)', len(subtitles))
            downloaded_subtitles[video].extend(subtitles)

    return downloaded_subtitles


def save_subtitles(
    video: Video,
    subtitles: Sequence[Subtitle],
    *,
    single: bool = False,
    directory: str | os.PathLike | None = None,
    encoding: str | None = None,
    subtitle_format: str | None = None,
    extension: str | None = None,
    language_type_suffix: bool = False,
    language_format: str = 'alpha2',
) -> list[Subtitle]:
    """Save subtitles on filesystem.

    Subtitles are saved in the order of the list. If a subtitle with a language has already been saved, other subtitles
    with the same language are silently ignored.

    The extension used is `.lang.srt` by default or `.srt` is `single` is `True`, with `lang` being the IETF code for
    the :attr:`~subliminal.subtitle.Subtitle.language` of the subtitle.

    :param video: video of the subtitles.
    :type video: :class:`~subliminal.video.Video`
    :param subtitles: subtitles to save.
    :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`
    :param bool single: save a single subtitle, default is to save one subtitle per language.
    :param str directory: path to directory where to save the subtitles, default is next to the video.
    :param str encoding: encoding in which to save the subtitles, default is to keep original encoding.
    :param str subtitle_format: format in which to save the subtitles, default is to keep original format.
    :param (str | None) extension: the subtitle extension, default is to match to the subtitle format.
    :param bool language_type_suffix: add a suffix 'hi' or 'fo' if needed. Default to False.
    :param str language_format: format of the language suffix. Default to 'alpha2'.
    :return: the saved subtitles
    :rtype: list of :class:`~subliminal.subtitle.Subtitle`

    """
    saved_subtitles: list[Subtitle] = []
    for subtitle in subtitles:
        # check content
        if not subtitle.content:
            logger.error('Skipping subtitle %r: no content', subtitle)
            continue

        # check language
        if subtitle.language in {s.language for s in saved_subtitles}:
            logger.debug('Skipping subtitle %r: language already saved', subtitle)
            continue

        # convert subtitle to a new format
        if subtitle_format:
            # Use the video FPS if the FPS of the subtitle is not defined
            fps = video.frame_rate if subtitle.fps is None else None
            subtitle.convert(subtitle_format, output_encoding=encoding, fps=fps)

        # create subtitle path
        subtitle_path = subtitle.get_path(
            video,
            single=single,
            extension=extension,
            language_type_suffix=language_type_suffix,
            language_format=language_format,
        )
        if directory is not None:
            subtitle_path = os.path.join(directory, os.path.split(subtitle_path)[1])

        # save content as is or in the specified encoding
        logger.info('Saving %r to %r', subtitle, subtitle_path)
        if encoding is None:
            with open(subtitle_path, 'wb') as f:
                f.write(subtitle.content)
        else:
            with open(subtitle_path, 'w', encoding=encoding) as f:
                f.write(subtitle.text)
        saved_subtitles.append(subtitle)

        # check single
        if single:
            break

    return saved_subtitles
