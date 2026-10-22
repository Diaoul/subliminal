"""Core functions."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from subliminal.utils import safely_guessit

from .archives import ARCHIVE_EXTENSIONS, is_supported_archive, scan_archive
from .exceptions import ArchiveError
from .utils import get_age
from .video import VIDEO_EXTENSIONS, Video

if TYPE_CHECKING:
    from datetime import timedelta

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
