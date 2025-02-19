"""Core functions."""

from __future__ import annotations

import logging
import operator
import os
import warnings
from pathlib import Path
from zipfile import BadZipfile

from guessit import guessit  # type: ignore[import-untyped]

from .exceptions import ArchiveError
from .video import VIDEO_EXTENSIONS, Video

logger = logging.getLogger(__name__)


try:
    from rarfile import (  # type: ignore[import-untyped]
        BadRarFile,
        Error,
        NotRarFile,
        RarCannotExec,
        RarFile,
        is_rarfile,
    )

    #: Supported archive extensions (.rar)
    ARCHIVE_EXTENSIONS: tuple[str] = ('.rar',)

    #: Supported archive errors
    ARCHIVE_ERRORS: tuple[Exception] = (ArchiveError, BadZipfile, BadRarFile)  # type: ignore[assignment]

except ImportError:
    #: Supported archive extensions
    ARCHIVE_EXTENSIONS: tuple[str] = ()  # type: ignore[no-redef]

    #: Supported archive errors
    ARCHIVE_ERRORS: tuple[Exception] = (ArchiveError, BadZipfile)  # type: ignore[no-redef]


def is_supported_archive(filename: str) -> bool:
    """Check if an archive format is supported and warn to install additional modules."""
    if filename.lower().endswith(ARCHIVE_EXTENSIONS):
        return True

    if filename.lower().endswith('.rar'):  # pragma: no cover
        msg = 'Install the rarfile module to be able to read rar archives.'
        warnings.warn(msg, UserWarning, stacklevel=2)

    return False  # pragma: no cover


def scan_archive(path: str | os.PathLike, name: str | None = None) -> Video:
    """Scan an archive from a `path`.

    :param str path: existing path to the archive.
    :param str name: if defined, name to use with guessit instead of the path.
    :return: the scanned video.
    :rtype: :class:`~subliminal.video.Video`
    :raises: :class:`ArchiveError`: error opening the archive.
    """
    path = Path(path)

    # rar
    if '.rar' in ARCHIVE_EXTENSIONS and path.suffix.lower() == '.rar':
        try:
            video = scan_archive_rar(path, name=name)
        except (Error, NotRarFile, RarCannotExec, ValueError) as e:
            args = (e.message,) if hasattr(e, 'message') else e.args
            raise ArchiveError(*args) from e

        return video

    msg = f'{path.suffix!r} is not a valid archive'
    raise ArchiveError(msg)


def scan_archive_rar(path: str | os.PathLike, name: str | None = None) -> Video:
    """Scan a rar archive from a `path`.

    :param str path: existing path to the archive.
    :param str name: if defined, name to use with guessit instead of the path.
    :return: the scanned video.
    :rtype: :class:`~subliminal.video.Video`
    :raises: :class:`ValueError`: video path is not well defined.
    """
    path = os.fspath(path)
    # check for non-existing path
    if not os.path.exists(path):  # pragma: no cover
        msg = f'Path does not exist: {path!r}'
        raise ValueError(msg)

    if not is_rarfile(path):
        msg = f'{os.path.splitext(path)[1]!r} is not a valid archive'
        raise ValueError(msg)

    dir_path, filename = os.path.split(path)

    logger.info('Scanning archive %r in %r', filename, dir_path)

    # Get filename and file size from RAR
    rar = RarFile(path)

    # check that the rar doesnt need a password
    if rar.needs_password():
        msg = 'Rar requires a password'
        raise ValueError(msg)

    # raise an exception if the rar file is broken
    # must be called to avoid a potential deadlock with some broken rars
    rar.testrar()

    file_infos = [f for f in rar.infolist() if not f.isdir() and f.filename.endswith(VIDEO_EXTENSIONS)]

    # sort by file size descending, the largest video in the archive is the one we want, there may be samples or intros
    file_infos.sort(key=operator.attrgetter('file_size'), reverse=True)

    # no video found
    if not file_infos:
        msg = 'No video in archive'
        raise ValueError(msg)

    # Free the information about irrelevant files before guessing
    file_info = file_infos[0]

    # guess
    video_filename = file_info.filename
    video_path = os.path.join(dir_path, video_filename)

    repl = name if name else video_path
    video = Video.fromguess(video_path, guessit(repl))

    # size
    video.size = file_info.file_size

    return video
