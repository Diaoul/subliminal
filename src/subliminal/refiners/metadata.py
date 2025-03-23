"""Refine the :class:`~subliminal.video.Video` object with mkv metadata."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from babelfish import Language  # type: ignore[import-untyped]
from knowit.api import available_providers, dependencies, know  # type: ignore[import-untyped]

from subliminal.subtitle import EmbeddedSubtitle

if TYPE_CHECKING:
    from collections.abc import Mapping

    from subliminal.video import Video

logger = logging.getLogger(__name__)


def loaded_providers(options: dict[str, Any] | None = None) -> dict[str, bool]:
    """Return a dict with knowit providers and if they are installed."""
    # clear knowit cached available providers
    available_providers.clear()
    # find knowit providers with options
    deps = dependencies(options)
    # mediainfo requires more work, because 'pymediainfo' is always installed
    # but it's not working alone.
    return {k: len({v for v in d if v != 'pymediainfo'}) > 0 for k, d in deps.items()}


def refine(
    video: Video,
    *,
    embedded_subtitles: bool = True,
    metadata_provider: str | None = None,
    metadata_options: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> Video:
    """Refine a video by searching its metadata.

    For better metadata discovery, at least one of the following external tool
    needs to be installed:

        - ``mediainfo``: best capabilities, works with any video file format.
            Automatically installed on Windows and MacOS (bundled with
            the ``pymediainfo`` python package).
            Needs to be installed on Linux.
        - ``ffmpeg``: similar capabilities, works with any video file format.
            Needs to be installed on Windows, MacOS and Linux.
        - ``mkvmerge``: only works with ``mkv`` files.
            Needs to be installed on Windows, MacOS and Linux.

    Several :class:`~subliminal.video.Video` attributes can be found:

      * :attr:`~subliminal.video.Video.resolution`
      * :attr:`~subliminal.video.Video.duration`
      * :attr:`~subliminal.video.Video.frame_rate`
      * :attr:`~subliminal.video.Video.video_codec`
      * :attr:`~subliminal.video.Video.audio_codec`
      * :attr:`~subliminal.video.Video.subtitles`

    :param Video video: the Video to refine.
    :param bool embedded_subtitles: search for embedded subtitles.
    :param (str | None) metadata_provider: provider used to retrieve information from video metadata.
        Should be one of ['mediainfo', 'ffmpeg', 'mkvmerge', 'enzyme']. None defaults to `mediainfo`.
    :param dict metadata_options: keyword arguments to pass to knowit, like executable paths:
        `metadata_options={'ffmpeg': '/opt/bin/ffmpeg'}`.

    """
    # skip non existing videos
    if not video.exists:  # pragma: no cover
        return video

    # metadata options
    options = dict(metadata_options) if metadata_options is not None else {}
    # a dict of providers installed on the system
    providers = loaded_providers(options)
    # check if the specified metadata provider is installed, otherwise use default
    if metadata_provider is not None:
        # not a valid provider name
        if metadata_provider not in providers:
            msg = (
                f'metadata_provider={metadata_provider!r} is not a valid argument to `refine`, '
                f'needs to be None or one of:\n{list(providers.keys())}'
            )
            logger.warning(msg)
        # provider library or executable not found
        elif not providers[metadata_provider]:
            msg = (
                'The metadata_provider library or executable was not found, '
                'you can specify the path with the argument to the refine function: '
                f'`metadata_options={{{metadata_provider!r}: <path/to/exec/or/lib>}}'
            )
            logger.warning(msg)
        # provider installed, force using it
        else:
            options['provider'] = metadata_provider

    # get video metadata
    logger.debug('Retrieving metadata from %r', video.name)
    media = know(video.name, options)

    provider_info = media['provider']
    logger.debug('Using provider %r', provider_info)

    # duration, in seconds
    # more reliable to take it from here than from the 'video' track
    if 'duration' in media:
        video.duration = get_float(media['duration'])
        logger.debug('Found duration %.2f', video.duration)

    # main video track
    if 'video' in media and len(media['video']) > 0:
        # pick the default track if defined, otherwise just pick the first track
        default_videos = [track for track in media['video'] if track.get('default', False) is True]
        video_track = default_videos[0] if len(default_videos) > 0 else media['video'][0]

        # resolution
        if 'resolution' in video_track:
            resolution = str(video_track['resolution'])
            if resolution in ('480p', '720p', '1080p'):
                video.resolution = resolution
                logger.debug('Found resolution %s', video.resolution)

        # frame rate
        if 'frame_rate' in video_track:
            video.frame_rate = get_float(video_track['frame_rate'])
            logger.debug('Found frame_rate %.2f', video.frame_rate)

        # video codec
        if 'codec' in video_track:
            video.video_codec = video_track['codec']
            logger.debug('Found video_codec %s', video.video_codec)
    else:  # pragma: no cover
        logger.warning('Video has no video track')

    # main audio track
    if 'audio' in media and len(media['audio']) > 0:
        # pick the default track if defined, otherwise just pick the first track
        default_audios = [track for track in media['audio'] if track.get('default', False) is True]
        audio_track = default_audios[0] if len(default_audios) > 0 else media['audio'][0]

        # audio codec
        if 'codec' in audio_track:
            video.audio_codec = audio_track['codec']
            logger.debug('Found audio_codec %s', video.audio_codec)
    else:  # pragma: no cover
        logger.warning('Video has no audio track')

    # subtitle tracks
    if embedded_subtitles:
        if 'subtitle' in media and len(media['subtitle']) > 0:
            embedded_subtitles_list: list[EmbeddedSubtitle] = []
            for st in media['subtitle']:
                # language
                lang = st.get('language', Language('und'))

                sub = EmbeddedSubtitle(
                    lang,
                    subtitle_id=video.name,
                    hearing_impaired=st.get('hearing_impaired', st.get('closed_caption')),
                    foreign_only=st.get('forced'),
                    subtitle_format=get_subtitle_format(st.get('format', 'srt')),
                )

                # add to set
                embedded_subtitles_list.append(sub)

            logger.debug('Found embedded subtitles %r', embedded_subtitles_list)
            video.subtitles.extend(embedded_subtitles_list)
        else:
            logger.debug('Video has no subtitle track')

    return video


def get_float(value: Any) -> float | None:
    """Get the float value from a quantity."""
    if value is None:
        return None
    # already a float
    if isinstance(value, (int, float, str)):
        return float(value)

    # timedelta
    if isinstance(value, timedelta):
        return float(value.total_seconds())

    # pint.Quantity
    try:
        return float(value.magnitude)
    except AttributeError:
        pass
    return float(value)


def get_subtitle_format(value: str | None) -> str | None:
    """Normalize the subtitle format name."""
    if value is None:
        return None

    # lower case
    value = value.lower()

    # knowit uses 'SubRip', subliminal uses 'srt'
    if value == 'subrip':
        return 'srt'

    return value
