"""Refine the :class:`~subliminal.video.Video` object with mkv metadata."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from babelfish import Error as BabelfishError  # type: ignore[import-untyped]
from babelfish import Language  # type: ignore[import-untyped]
from enzyme import MKV  # type: ignore[import-untyped]

from subliminal.subtitle import EmbeddedSubtitle

if TYPE_CHECKING:
    from subliminal.video import Video

logger = logging.getLogger(__name__)


def refine(video: Video, *, embedded_subtitles: bool = True, **kwargs: Any) -> Video:
    """Refine a video by searching its metadata.

    Several :class:`~subliminal.video.Video` attributes can be found:

      * :attr:`~subliminal.video.Video.resolution`
      * :attr:`~subliminal.video.Video.video_codec`
      * :attr:`~subliminal.video.Video.audio_codec`
      * :attr:`~subliminal.video.Video.subtitles`

    :param bool embedded_subtitles: search for embedded subtitles.

    """
    # skip non existing videos
    if not video.exists:
        return video

    # check extensions
    extension = os.path.splitext(video.name)[1]
    if extension != '.mkv':
        logger.debug('Unsupported video extension %s', extension)
        return video

    with open(video.name, 'rb') as f:
        mkv = MKV(f)

    # main video track
    if mkv.video_tracks:
        video_track = mkv.video_tracks[0]

        # resolution
        if video_track.height in (480, 720, 1080):
            if video_track.interlaced:
                video.resolution = '%di' % video_track.height
            else:
                video.resolution = '%dp' % video_track.height
            logger.debug('Found resolution %s', video.resolution)

        # video codec
        if video_track.codec_id == 'V_MPEG4/ISO/AVC':
            video.video_codec = 'H.264'
            logger.debug('Found video_codec %s', video.video_codec)
        elif video_track.codec_id == 'V_MPEG4/ISO/SP':
            video.video_codec = 'DivX'
            logger.debug('Found video_codec %s', video.video_codec)
        elif video_track.codec_id == 'V_MPEG4/ISO/ASP':
            video.video_codec = 'Xvid'
            logger.debug('Found video_codec %s', video.video_codec)
    else:
        logger.warning('MKV has no video track')

    # main audio track
    if mkv.audio_tracks:
        audio_track = mkv.audio_tracks[0]
        # audio codec
        if audio_track.codec_id == 'A_AC3':
            video.audio_codec = 'Dolby Digital'
            logger.debug('Found audio_codec %s', video.audio_codec)
        elif audio_track.codec_id == 'A_DTS':
            video.audio_codec = 'DTS'
            logger.debug('Found audio_codec %s', video.audio_codec)
        elif audio_track.codec_id == 'A_AAC':
            video.audio_codec = 'AAC'
            logger.debug('Found audio_codec %s', video.audio_codec)
    else:
        logger.warning('MKV has no audio track')

    # subtitle tracks
    if mkv.subtitle_tracks:
        if embedded_subtitles:
            embedded_subtitle_languages = set()
            for st in mkv.subtitle_tracks:
                if st.language:
                    try:
                        embedded_subtitle_languages.add(Language.fromalpha3b(st.language))
                    except BabelfishError:
                        logger.exception(
                            'Embedded subtitle track language %r is not a valid language',
                            st.language,
                        )
                        embedded_subtitle_languages.add(Language('und'))
                elif st.name:
                    try:
                        embedded_subtitle_languages.add(Language.fromname(st.name))
                    except BabelfishError:
                        logger.debug('Embedded subtitle track name %r is not a valid language', st.name)
                        embedded_subtitle_languages.add(Language('und'))
                else:
                    embedded_subtitle_languages.add(Language('und'))
            logger.debug('Found embedded subtitle %r', embedded_subtitle_languages)
            video.subtitles |= {EmbeddedSubtitle(lang) for lang in embedded_subtitle_languages}
    else:
        logger.debug('MKV has no subtitle track')

    return video
