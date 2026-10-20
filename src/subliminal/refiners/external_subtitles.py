"""Refine the :class:`~subliminal.video.Video` object with mkv metadata."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, ClassVar

from subliminal.subtitle import SUBTITLE_EXTENSIONS, ExternalSubtitle
from subliminal.video import Episode, Movie

from . import AsyncRefiner

if TYPE_CHECKING:
    from subliminal.video import Video

logger = logging.getLogger(__name__)


def parse_language_code(subtitle_filename: str, video_filename: str) -> str | None:
    """Parse the subtitle filename to extract the language.

    Return None if the subtitle filename root is not identical to the video filename.

    :param str subtitle_filename: path to the subtitle.
    :param str video_filename: path to the video.
    :return: the language code suffixed to the video name or None if the names are different.
    :rtype: str | None

    """
    fileroot, fileext = os.path.splitext(video_filename)

    # keep only valid subtitle filenames
    if not subtitle_filename.startswith(fileroot) or not subtitle_filename.lower().endswith(SUBTITLE_EXTENSIONS):
        return None

    # extract the potential language code
    language_code = subtitle_filename[len(fileroot) : -len(os.path.splitext(subtitle_filename)[1])]
    return language_code.replace(fileext, '').replace('_', '-')[1:]


class ExternalSubtitlesRefiner(AsyncRefiner):
    """Search for external subtitles."""

    #: Supported video types
    video_types: ClassVar[tuple[type[Video], ...]] = (Episode, Movie)

    #: Stage of the refiner, lower is called first
    stage: ClassVar[int] = 1

    #: Priority of the refiner (inside its stage), higher value takes precedence
    priority: int = 0

    async def initialize(self) -> None:
        """Initialize the refiner."""
        pass

    async def terminate(self) -> None:
        """Terminate the refiner."""
        pass

    async def refine(
        self,
        video: Video,
        *,
        directory: str | os.PathLike | None = None,
        external_subtitles: bool = True,
        **kwarg: Any,
    ) -> dict[str, Any]:
        """Search for external subtitles from a video `path` and their associated language.

        Unless `directory` is provided, search will be made in the same directory as the video file.

        :param str path: path to the video.
        :param str directory: directory to search for subtitles.
        :param bool external_subtitles: search for external subtitles.
        :return: found subtitles with their languages.
        :rtype: dict

        """
        if not external_subtitles:
            logger.debug('Ignoring external subtitles')
            return {}

        path = video.name
        # split path
        dirpath, filename = os.path.split(path)
        dirpath = dirpath or '.'

        # search for subtitles
        subtitles = []
        for p in os.listdir(directory or dirpath):
            language_code = parse_language_code(p, filename)
            if language_code is None:
                continue

            subtitle = ExternalSubtitle.from_language_code(language_code, subtitle_path=p)
            subtitles.append(subtitle)

        if subtitles:
            logger.debug('Found subtitles %r', subtitles)
        else:
            logger.debug('No subtitles found')

        return {'subtitles': subtitles}
