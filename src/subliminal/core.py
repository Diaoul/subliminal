"""Scan video file functions."""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from .archives import ARCHIVE_EXTENSIONS, is_supported_archive, scan_archive
from .exceptions import ArchiveError
from .provider_pool import AsyncProviderPool, AsyncRefinerPool, _check_no_running_loop, check_video
from .utils import get_age, safely_guessit
from .video import VIDEO_EXTENSIONS, Video

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Set
    from datetime import timedelta

    from babelfish import Language

    from subliminal.score import ComputeScore

    from .subtitle import Subtitle

logger = logging.getLogger(__name__)


def scan_name(path: str | os.PathLike, name: str | None = None) -> Video:
    """Scan a video from a `path`.

    :param str path: path to the video.
    :param str name: if defined, name to use with guessit instead of the path.
    :return: the scanned video.
    :rtype: :class:`~subliminal.video.Video`
    """
    path = os.fspath(path)
    repl = name if name else path
    if name:
        logger.info('Scanning video %r, with replacement name %r', path, repl)
    else:
        logger.info('Scanning video %r', path)

    return Video.fromguess(path, safely_guessit(repl))


def scan_video(path: str | os.PathLike, name: str | None = None) -> Video:
    """Scan a video from an existing `path`.

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

    # guess
    video = scan_name(path, name=name)

    # size
    video.size = os.path.getsize(path)
    logger.debug('Size is %d', video.size)

    return video


def scan_video_or_archive(path: str | os.PathLike, name: str | None = None) -> Video:
    """Scan a video or an archive from a `path`.

    :param str path: existing path to the video or archive.
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

    # scan
    filename = os.path.basename(path)
    if filename.lower().endswith(VIDEO_EXTENSIONS):
        # scan video
        return scan_video(path, name=name)

    if is_supported_archive(filename):
        # scan archive
        try:
            video = scan_archive(path, name=name)
        except ArchiveError as e:
            # Re-raise as a ValueError
            msg = 'Error scanning archive'
            raise ValueError(msg) from e
        return video

    msg = f'Unsupported file {filename!r}'  # pragma: no cover
    raise ValueError(msg)  # pragma: no cover


def scan_path(filepath: str | os.PathLike[str], *, name: str | None = None) -> Video:
    """Scan a video or an archive from a `path`, maybe non-existing.

    :param str path: path to the video or archive, may be an existing path or not.
    :param str name: if defined, name to use with guessit instead of the path.
    :return: the scanned video.
    :rtype: :class:`~subliminal.video.Video`
    :raises: :class:`ValueError`: video path is not well defined.
    """
    if not os.path.isfile(filepath):
        return scan_name(filepath, name=name)
    return scan_video_or_archive(filepath, name=name)


def collect_video_filepaths(
    path: str | os.PathLike,
    *,
    age: timedelta | None = None,
    use_ctime: bool = True,
    archives: bool = True,
    name: str | None = None,
) -> list[str]:
    """Collect video file paths in directory `path`.

    :param str path: existing directory path to scan.
    :param datetime.timedelta age: maximum age of the video or archive.
    :param bool use_ctime: use the latest of creation time and modification time to compute the age of the video,
        instead of just modification time.
    :param bool archives: scan videos in archives.
    :return: the collected video file names.
    :rtype: list of str
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
    video_filepaths = []
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

            video_filepaths.append(filepath)

    return video_filepaths


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
    filepaths = collect_video_filepaths(path, age=age, use_ctime=use_ctime, archives=archives)

    videos = []
    for filepath in filepaths:
        try:
            video = scan_video_or_archive(filepath, name=name)
        except ValueError:
            logger.exception('Error scanning video')
            continue
        videos.append(video)

    return videos


async def async_refine(
    videos: Video | Set[Video],
    *,
    refiners: Sequence[str] | None = None,
    refiner_configs: Mapping[str, Any] | None = None,
    check_kwargs: Mapping[str, Any] | None = None,
    pool_class: type[AsyncRefinerPool] = AsyncRefinerPool,
    **kwargs: Any,
) -> set[Video]:
    """Refine one or several videos using :ref:`refiners`.

    .. note::

        Exceptions raised in refiners are silently passed and logged.

    :param videos: the videos to refine.
    :type videos: set of :class:`~subliminal.video.Video`
    :param Sequence refiners: refiners to select. None defaults to all refiners.
    :param dict refiner_configs: refiner configuration as keyword arguments per refiner name to pass when
        calling the refine method
    :param dict check_kwargs: arguments to pass to the check_video function
    :param pool_class: class to use as refiner pool.
    :type pool_class: :class:`~subliminal.provider_pool.AsyncRefinerPool` or similar
    :param kwargs: additional parameters for the `refine` method.
    :return: the videos that are not ignored.
    :rtype: set of :class:`~subliminal.video.Video`
    """
    # make sure videos is a list
    if isinstance(videos, Video):
        videos = {videos}
    # return immediately if no videos
    if not videos:
        return set()

    # refine videos
    async with pool_class(refiners=refiners, refiner_configs=refiner_configs, check_kwargs=check_kwargs) as pool:
        return await pool.refine_videos(videos, **kwargs)


def refine(*args: Any, **kwargs: Any) -> set[Video]:
    """Refine videos using :ref:`refiners`."""
    _check_no_running_loop()
    return asyncio.run(async_refine(*args, **kwargs))


async def async_list_subtitles(
    videos: Set[Video],
    languages: Set[Language],
    *,
    pool_class: type[AsyncProviderPool] = AsyncProviderPool,
    **kwargs: Any,
) -> dict[Video, list[Subtitle]]:
    """List subtitles.

    The `videos` must pass the `languages` check of :func:`~subliminal.provider_pool.check_video`.

    :param videos: videos to list subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to search for.
    :type languages: set of :class:`~babelfish.language.Language`
    :param pool_class: class to use as provider pool.
    :type pool_class: :class:`~subliminal.provider_pool.AsyncProviderPool` or similar
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
    async with pool_class(**kwargs) as pool:
        return await pool.list_subtitles_videos(checked_videos, languages)


def list_subtitles(*args: Any, **kwargs: Any) -> dict[Video, list[Subtitle]]:
    """Synchronous wrapper around :func:`async_list_subtitles`."""
    _check_no_running_loop()
    return asyncio.run(async_list_subtitles(*args, **kwargs))


async def async_download_subtitles(
    subtitles: Sequence[Subtitle],
    *,
    pool_class: type[AsyncProviderPool] = AsyncProviderPool,
    **kwargs: Any,
) -> None:
    """Download :attr:`~subliminal.subtitle.Subtitle.content` of `subtitles`.

    :param subtitles: subtitles to download.
    :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`
    :param pool_class: class to use as provider pool.
    :type pool_class: :class:`~subliminal.provider_pool.AsyncProviderPool` or similar
    :param kwargs: additional parameters for the provided `pool_class` constructor.

    """
    async with pool_class(**kwargs) as pool:
        for subtitle in subtitles:
            logger.info('Downloading subtitle %r', subtitle)
            await pool.download_subtitle(subtitle)


def download_subtitles(*args: Any, **kwargs: Any) -> None:
    """Synchronous wrapper around :func:`async_download_subtitles`."""
    _check_no_running_loop()
    return asyncio.run(async_download_subtitles(*args, **kwargs))


async def async_download_best_subtitles(
    videos: Set[Video],
    languages: Set[Language],
    *,
    pool_class: type[AsyncProviderPool] = AsyncProviderPool,
    min_score: int = 0,
    subtitle_categories: str = '',
    skip_wrong_fps: bool = False,
    only_one: bool = False,
    compute_score: ComputeScore | None = None,
    ignore_subtitles: Sequence[str] | None = None,
    **kwargs: Any,
) -> dict[Video, list[Subtitle]]:
    """List and download the best matching subtitles.

    The `videos` must pass the `languages` and `undefined` (`only_one`) checks of
    :func:`~subliminal.provider_pool.check_video`.

    :param videos: videos to download subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to download.
    :type languages: set of :class:`~babelfish.language.Language`
    :param pool_class: class to use as async provider pool.
    :type pool_class: :class:`~subliminal.provider_pool.AsyncProviderPool` or similar
    :param int min_score: minimum score for a subtitle to be downloaded.
    :param str subtitle_categories: ordered list of categories to download, omitted categories are filtered out.
        Empty string corresponds to no filtering or sorting.
    :param bool skip_wrong_fps: skip subtitles with an FPS that do not match the video (False).
    :param bool only_one: download only one subtitle, not one per language.
    :param compute_score: function that takes `subtitle` and `video` as positional arguments and returns the score.
    :param ignore_subtitles: list of subtitle ids to ignore, if any.
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
    async with pool_class(**kwargs) as pool:
        for video in checked_videos:
            logger.info('Downloading best subtitles for %r', video)
            subtitles = await pool.list_subtitles(video, languages - video.subtitle_languages)
            downloaded_subtitles[video] = await pool.download_best_subtitles(
                subtitles,
                video,
                languages,
                min_score=min_score,
                subtitle_categories=subtitle_categories,
                skip_wrong_fps=skip_wrong_fps,
                only_one=only_one,
                compute_score=compute_score,
                ignore_subtitles=ignore_subtitles,
            )
            logger.info('Downloaded %d subtitle(s)', len(downloaded_subtitles[video]))

    return downloaded_subtitles


def download_best_subtitles(*args: Any, **kwargs: Any) -> dict[Video, list[Subtitle]]:
    """Synchronous wrapper around :func:`async_download_best_subtitles`."""
    _check_no_running_loop()
    return asyncio.run(async_download_best_subtitles(*args, **kwargs))


def save_subtitles(
    video: Video,
    subtitles: Sequence[Subtitle],
    *,
    single: bool = False,
    directory: str | os.PathLike | None = None,
    encoding: str | None = None,
    subtitle_format: str | None = None,
    extension: str | None = None,
    category_suffix: bool = False,
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
    :param bool category_suffix: add a suffix with the subtitle category ('hi' or 'fo') if needed. Default to False.
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
            subtitle.convert(output_format=subtitle_format, output_encoding=encoding, fps=fps)

        # create subtitle path
        subtitle_path = subtitle.get_path(
            video,
            single=single,
            extension=extension,
            category_suffix=category_suffix,
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
