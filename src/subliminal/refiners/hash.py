"""Refine the :class:`~subliminal.video.Video` object with video hashes."""

from __future__ import annotations

import logging
import os
import struct
from typing import TYPE_CHECKING, Any, cast

from subliminal.extensions import get_default_providers, provider_manager

if TYPE_CHECKING:
    from collections.abc import Sequence, Set
    from typing import Callable, TypeAlias

    from babelfish import Language  # type: ignore[import-untyped]

    from subliminal.providers import Provider
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


hash_functions: dict[str, HashFunc] = {
    'opensubtitles': hash_opensubtitles,
    'opensubtitlesvip': hash_opensubtitles,
    'opensubtitlescom': hash_opensubtitles,
    'opensubtitlescomvip': hash_opensubtitles,
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

    :param Video video: the Video to refine.
    :param providers: list of providers for which the video hash should be computed.
    :param languages: set of languages that need to be compatible with the providers.

    """
    if video.size is None or video.size <= 10485760:
        logger.warning('Size is lower than 10MB: hashes not computed')
        return video

    providers = providers if providers is not None else get_default_providers()

    logger.debug('Computing hashes for %r', video.name)
    for name in providers:
        provider = cast('Provider', provider_manager[name].plugin)
        if not provider.check_types(video):
            continue

        if languages is not None and not provider.check_languages(languages):
            continue

        # Try provider static method
        h = provider.hash_video(video.name)

        # Try generic hashes
        if h is None and name in hash_functions:
            h = hash_functions[name](video.name)

        # Add hash
        if h is not None:
            video.hashes[name] = h

    logger.debug('Computed hashes %r', video.hashes)
    return video
