"""Get matches between a :class:`~subliminal.video.Video` object and a dict of guesses.

.. py:function:: guess_matches(video, guess, *, partial = False)

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param guess: the guess.
    :type guess: dict[str, Any]
    :param bool partial: whether or not the guess is partial.
    :return: matches between the `video` and the `guess`.
    :rtype: set[str]

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .score import get_equivalent_release_groups, score_keys
from .utils import ensure_list, sanitize, sanitize_release_group
from .video import Episode, Movie, Video

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Protocol

    from babelfish import Country  # type: ignore[import-untyped]

    class MatchingFunc(Protocol):
        """Match a :class:`~subliminal.video.Video` to criteria."""

        def __call__(self, video: Video, **kwargs: Any) -> bool: ...  # noqa: D102


def series_matches(video: Video, *, title: str | None = None, **kwargs: Any) -> bool:
    """Whether the `video` matches the series title.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str title: the series name.
    :return: whether there's a match
    :rtype: bool

    """
    if not isinstance(video, Episode):
        return False
    sanitized_title = sanitize(title)
    return (
        video.series is not None
        and sanitized_title is not None
        and sanitized_title in (sanitize(name) for name in [video.series, *video.alternative_series])
    )


def title_matches(video: Video, *, title: str | None = None, episode_title: str | None = None, **kwargs: Any) -> bool:
    """Whether the movie matches the movie `title` or the series matches the `episode_title`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str title: the movie title.
    :param str episode_title: the series episode title.
    :return: whether there's a match
    :rtype: bool

    """
    if isinstance(video, Episode):
        return video.title is not None and sanitize(episode_title) == sanitize(video.title)
    if isinstance(video, Movie):
        return video.title is not None and sanitize(title) == sanitize(video.title)
    return False  # pragma: no cover


def season_matches(video: Video, *, season: int | None = None, **kwargs: Any) -> bool:
    """Whether the episode matches the `season`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param int season: the episode season.
    :return: whether there's a match
    :rtype: bool

    """
    if not isinstance(video, Episode):
        return False
    return video.season is not None and season == video.season


def episode_matches(video: Video, *, episode: int | None = None, **kwargs: Any) -> bool:
    """Whether the episode matches the `episode`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param episode: the episode season.
    :type: list of int or int
    :return: whether there's a match
    :rtype: bool

    """
    if not isinstance(video, Episode):
        return False
    return video.episodes is not None and ensure_list(episode) == video.episodes


def year_matches(video: Video, *, year: int | None = None, partial: bool = False, **kwargs: Any) -> bool:
    """Whether the video matches the `year`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param int year: the video year.
    :param bool partial: whether or not the guess is partial.
    :return: whether there's a match
    :rtype: bool

    """
    if video.year is not None and year == video.year:
        return True
    if isinstance(video, Episode):
        # count "no year" as an information
        return not partial and video.original_series and year is None
    return False


def country_matches(video: Video, *, country: Country | None = None, partial: bool = False, **kwargs: Any) -> bool:
    """Whether the video matches the `country`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param country: the video country.
    :type country: :class:`~babelfish.country.Country`
    :param bool partial: whether or not the guess is partial.
    :return: whether there's a match
    :rtype: bool

    """
    if video.country is not None and country == video.country:
        return True

    if isinstance(video, Episode):
        # count "no country" as an information
        return not partial and video.original_series and country is None

    if isinstance(video, Movie):
        # count "no country" as an information
        return video.country is None and country is None
    return False  # pragma: no cover


def fps_matches(video: Video, *, fps: float | None = None, strict: bool = True, **kwargs: Any) -> bool:
    """Whether the video matches the `fps`.

    Frame rates are considered equal if the relative difference is less than 0.1 percent.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str fps: the video frame rate.
    :param bool strict: if strict, an absence of information is a non-match.
    :return: whether there's a match
    :rtype: bool

    """
    # make the difference a bit more than 0.1% to be sure
    relative_diff = 0.0011
    # if video and subtitle fps are defined, return True if the match, otherwise False
    if video.frame_rate is not None and video.frame_rate > 0 and fps is not None and fps > 0:
        return bool(abs(video.frame_rate - fps) / video.frame_rate < relative_diff)

    # if information is missing, return True only if not strict
    return not strict


def release_group_matches(video: Video, *, release_group: str | None = None, **kwargs: Any) -> bool:
    """Whether the video matches the `release_group`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str release_group: the video release group.
    :return: whether there's a match
    :rtype: bool

    """
    return (
        video.release_group is not None
        and release_group is not None
        and any(
            r in sanitize_release_group(release_group)
            for r in get_equivalent_release_groups(sanitize_release_group(video.release_group))
        )
    )


def streaming_service_matches(video: Video, *, streaming_service: str | None = None, **kwargs: Any) -> bool:
    """Whether the video matches the `streaming_service`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str streaming_service: the video streaming service
    :return: whether there's a match
    :rtype: bool

    """
    return video.streaming_service is not None and streaming_service == video.streaming_service


def resolution_matches(video: Video, *, screen_size: str | None = None, **kwargs: Any) -> bool:
    """Whether the video matches the `resolution`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str screen_size: the video resolution
    :return: whether there's a match
    :rtype: bool

    """
    return video.resolution is not None and screen_size == video.resolution


def source_matches(video: Video, *, source: str | None = None, **kwargs: Any) -> bool:
    """Whether the video matches the `source`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str source: the video source
    :return: whether there's a match
    :rtype: bool

    """
    return video.source is not None and source == video.source


def video_codec_matches(video: Video, *, video_codec: str | None = None, **kwargs: Any) -> bool:
    """Whether the video matches the `video_codec`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str video_codec: the video codec
    :return: whether there's a match
    :rtype: bool

    """
    return video.video_codec is not None and video_codec == video.video_codec


def audio_codec_matches(video: Video, *, audio_codec: str | None = None, **kwargs: Any) -> bool:
    """Whether the video matches the `audio_codec`.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param str audio_codec: the video audio codec
    :return: whether there's a match
    :rtype: bool

    """
    return video.audio_codec is not None and audio_codec == video.audio_codec


#: Available matches functions
matches_manager: dict[str, MatchingFunc] = {
    'series': series_matches,
    'title': title_matches,
    'season': season_matches,
    'episode': episode_matches,
    'year': year_matches,
    'country': country_matches,
    'fps': fps_matches,
    'release_group': release_group_matches,
    'streaming_service': streaming_service_matches,
    'resolution': resolution_matches,
    'source': source_matches,
    'video_codec': video_codec_matches,
    'audio_codec': audio_codec_matches,
}


def guess_matches(video: Video, guess: Mapping[str, Any], *, partial: bool = False, strict: bool = True) -> set[str]:
    """Get matches between a `video` and a `guess`.

    If a guess is `partial`, the absence of information won't be counted as a match.
    If a match is `strict`, the absence of information will be counted as a non-match.

    :param video: the video.
    :type video: :class:`~subliminal.video.Video`
    :param guess: the guess.
    :type guess: dict
    :param bool partial: whether or not the guess is partial.
    :param bool strict: whether or not the match is strict.
    :return: matches between the `video` and the `guess`.
    :rtype: set

    """
    matches = set()
    for key in score_keys:
        if key in matches_manager and matches_manager[key](video, partial=partial, strict=strict, **guess):
            matches.add(key)

    return matches
