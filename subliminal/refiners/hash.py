"""Refine the :class:`~subliminal.video.Video` object with video hashes."""

from __future__ import annotations

import hashlib
import logging
import os
import struct
from typing import TYPE_CHECKING, Any, cast

from subliminal.extensions import default_providers, provider_manager
from subliminal.providers import Provider

if TYPE_CHECKING:
    from collections.abc import Sequence, Set
    from typing import Callable, TypeAlias

    from babelfish import Language  # type: ignore[import-untyped]

    from subliminal.video import Video

    HashFunc: TypeAlias = Callable[[str | os.PathLike], str | None]

logger = logging.getLogger(__name__)


def hash_opensubtitles(video_path: str | os.PathLike) -> str | None:
    """Compute a hash using OpenSubtitles' algorithm.

    :param (str | os.PathLike) video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    video_path = os.fspath(video_path)
    bytesize = struct.calcsize(b'<q')
    with open(video_path, 'rb') as f:
        filesize = os.path.getsize(video_path)
        filehash = filesize
        if filesize < 65536 * 2:
            return None
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash &= 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash &= 0xFFFFFFFFFFFFFFFF
    return f'{filehash:016x}'


def hash_thesubdb(video_path: str | os.PathLike) -> str | None:
    """Compute a hash using TheSubDB's algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    readsize = 64 * 1024
    if os.path.getsize(video_path) < readsize:
        return None
    with open(video_path, 'rb') as f:
        data = f.read(readsize)
        f.seek(-readsize, os.SEEK_END)
        data += f.read(readsize)

    return hashlib.md5(data).hexdigest()  # noqa: S324


def hash_napiprojekt(video_path: str | os.PathLike) -> str | None:
    """Compute a hash using NapiProjekt's algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    readsize = 1024 * 1024 * 10
    with open(video_path, 'rb') as f:
        data = f.read(readsize)
    return hashlib.md5(data).hexdigest()  # noqa: S324


def hash_shooter(video_path: str | os.PathLike) -> str | None:
    """Compute a hash using Shooter's algorithm.

    :param string video_path: path of the video
    :return: the hash
    :rtype: string

    """
    filesize = os.path.getsize(video_path)
    readsize = 4096
    if os.path.getsize(video_path) < readsize * 2:
        return None
    offsets = (readsize, filesize // 3 * 2, filesize // 3, filesize - readsize * 2)
    filehash = []
    with open(video_path, 'rb') as f:
        for offset in offsets:
            f.seek(offset)
            filehash.append(hashlib.md5(f.read(readsize)).hexdigest())  # noqa: S324
    return ';'.join(filehash)


hash_functions: dict[str, HashFunc] = {
    'napiprojekt': hash_napiprojekt,
    'opensubtitles': hash_opensubtitles,
    'opensubtitlesvip': hash_opensubtitles,
    'opensubtitlescom': hash_opensubtitles,
    'opensubtitlescomvip': hash_opensubtitles,
    'shooter': hash_shooter,
    'thesubdb': hash_thesubdb,
}


def refine(
    video: Video,
    *,
    providers: Sequence[str] | None = None,
    languages: Set[Language] | None = None,
    **kwargs: Any,
) -> Video:
    """Refine a video computing required hashes for the given providers.

    The following :class:`~subliminal.video.Video` attribute can be found:

      * :attr:`~subliminal.video.Video.hashes`

    """
    if video.size is None or video.size <= 10485760:
        logger.warning('Size is lower than 10MB: hashes not computed')
        return video

    logger.debug('Computing hashes for %r', video.name)
    for name in providers or default_providers:
        provider = cast(Provider, provider_manager[name].plugin)
        if name not in hash_functions:
            continue

        if not provider.check_types(video):
            continue

        if languages is not None and not provider.check_languages(languages):
            continue

        h = hash_functions[name](video.name)
        if h is not None:
            video.hashes[name] = h

    logger.debug('Computed hashes %r', video.hashes)
    return video
