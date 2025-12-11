# mypy: disable-error-code="no-untyped-call"
"""Default implementation of the `compute_score` function.

It is the default for the `compute_score` parameter in :meth:`~subliminal.core.ProviderPool.download_best_subtitles`
and :func:`~subliminal.core.download_best_subtitles`.

.. note::

    To avoid unnecessary dependency on `sympy <https://www.sympy.org/>`_ and boost subliminal's import time, the
    resulting scores are hardcoded here and manually updated when the set of equations change.

Available matches:

  * hash
  * title
  * year
  * country
  * series
  * season
  * episode
  * release_group
  * streaming_service
  * source
  * audio_codec
  * resolution
  * fps
  * video_codec
  * series_imdb_id
  * imdb_id
  * tvdb_id

"""

from __future__ import annotations

import logging
from importlib.util import find_spec
from typing import TYPE_CHECKING, Any

from .utils import clip
from .video import Episode, Movie

if TYPE_CHECKING:
    from typing import Protocol

    from .subtitle import Subtitle
    from .video import Video

    class ComputeScore(Protocol):
        """Compute the score of a subtitle matching a video."""

        def __call__(self, subtitle: Subtitle, video: Video) -> int: ...  # noqa: D102


# Check if sympy is installed (for tests)
WITH_SYMPY = find_spec('sympy') is not None

logger = logging.getLogger(__name__)


#: Scores for episodes
episode_scores: dict[str, int] = {
    'hash': 971,
    'series': 486,
    'country': 162,
    'year': 162,
    'episode': 54,
    'season': 54,
    'release_group': 18,
    'streaming_service': 18,
    'fps': 9,
    'source': 4,
    'audio_codec': 2,
    'resolution': 1,
    'video_codec': 1,
}

#: Scores for movies
movie_scores: dict[str, int] = {
    'hash': 323,
    'title': 162,
    'country': 54,
    'year': 54,
    'release_group': 18,
    'streaming_service': 18,
    'fps': 9,
    'source': 4,
    'audio_codec': 2,
    'resolution': 1,
    'video_codec': 1,
}

#: All scores names
score_keys = set(list(episode_scores) + list(movie_scores))

#: Equivalent release groups
equivalent_release_groups = ({'LOL', 'DIMENSION'}, {'ASAP', 'IMMERSE', 'FLEET'}, {'AVS', 'SVA'})


def get_equivalent_release_groups(release_group: str) -> set[str]:
    """Get all the equivalents of the given release group.

    :param str release_group: the release group to get the equivalents of.
    :return: the equivalent release groups.
    :rtype: set

    """
    for equivalent_release_group in equivalent_release_groups:
        if release_group in equivalent_release_group:
            return equivalent_release_group

    return {release_group}


def get_scores(video: Video) -> dict[str, Any]:
    """Get the scores dict for the given `video`.

    This will return either :data:`episode_scores` or :data:`movie_scores` based on the type of the `video`.

    :param video: the video to compute the score against.
    :type video: :class:`~subliminal.video.Video`
    :return: the scores dict.
    :rtype: dict

    """
    if isinstance(video, Episode):
        return episode_scores
    if isinstance(video, Movie):
        return movie_scores

    msg = 'video must be an instance of Episode or Movie'  # pragma: no-cover
    raise ValueError(msg)  # pragma: no-cover


def compute_score(subtitle: Subtitle, video: Video, **kwargs: Any) -> int:
    """Compute the score of the `subtitle` against the `video`.

    :func:`compute_score` uses the :meth:`Subtitle.get_matches <subliminal.subtitle.Subtitle.get_matches>` method and
    applies the scores (either from :data:`episode_scores` or :data:`movie_scores`) after some processing.

    :param subtitle: the subtitle to compute the score of.
    :type subtitle: :class:`~subliminal.subtitle.Subtitle`
    :param video: the video to compute the score against.
    :type video: :class:`~subliminal.video.Video`
    :return: score of the subtitle.
    :rtype: int

    """
    logger.info('Computing score of %r for video %r', subtitle, video)

    # get the scores dict
    scores = get_scores(video)
    logger.debug('Using scores %r', scores)

    # get the matches
    matches = subtitle.get_matches(video)
    logger.debug('Found matches %r', matches)

    # on hash match, discard everything else
    if 'hash' in matches:
        logger.debug('Keeping only hash match')
        matches &= {'hash'}

    # handle equivalent matches
    if isinstance(video, Episode):
        if 'title' in matches:
            logger.debug('Adding title match equivalent')
            matches.add('episode')
        if 'series_imdb_id' in matches:
            logger.debug('Adding series_imdb_id match equivalent')
            matches |= {'series', 'year', 'country'}
        if 'imdb_id' in matches:
            logger.debug('Adding imdb_id match equivalents')
            matches |= {'series', 'year', 'country', 'season', 'episode'}
        if 'series_tmdb_id' in matches:
            logger.debug('Adding series_tmdb_id match equivalents')
            matches |= {'series', 'year', 'country'}
        if 'tmdb_id' in matches:
            logger.debug('Adding tmdb_id match equivalents')
            matches |= {'series', 'year', 'country', 'season', 'episode'}
        if 'series_tvdb_id' in matches:
            logger.debug('Adding series_tvdb_id match equivalents')
            matches |= {'series', 'year', 'country'}
        if 'tvdb_id' in matches:
            logger.debug('Adding tvdb_id match equivalents')
            matches |= {'series', 'year', 'country', 'season', 'episode'}
    elif isinstance(video, Movie):  # pragma: no branch
        if 'imdb_id' in matches:
            logger.debug('Adding imdb_id match equivalents')
            matches |= {'title', 'year', 'country'}
        if 'tmdb_id' in matches:
            logger.debug('Adding tmdb_id match equivalents')
            matches |= {'title', 'year', 'country'}

    # compute the score
    score = int(sum(scores.get(match, 0) for match in matches))
    logger.info('Computed score %r with final matches %r', score, matches)

    # ensure score is within valid bounds
    max_score = scores['hash']
    if not (0 <= score <= max_score):  # pragma: no cover
        logger.info('Clip score between 0 and %d: %d', max_score, score)
        score = int(clip(score, 0, max_score))

    return score


if WITH_SYMPY:  # pragma: no cover
    from sympy import Eq, Symbol, solve, symbols  # type: ignore[import-untyped]

    def solve_episode_equations() -> dict[Symbol, int]:
        """Solve the score equation for Episodes.

        For testing purposes.
        """
        hash, series, year, country, season, episode = symbols('hash series year country season episode')  # noqa: A001
        release_group, streaming_service, fps, source = symbols('release_group streaming_service fps source')
        audio_codec, resolution, video_codec = symbols('audio_codec resolution video_codec')

        equations = [
            # hash is best
            Eq(
                hash,
                series
                + year
                + country
                + season
                + episode
                + release_group
                + streaming_service
                + fps
                + source
                + audio_codec
                + resolution
                + video_codec,
            ),
            # series counts for the most part in the total score
            Eq(
                series,
                year
                + country
                + season
                + episode
                + release_group
                + streaming_service
                + fps
                + source
                + audio_codec
                + resolution
                + video_codec
                + 1,
            ),
            # year is the second most important part
            Eq(
                year,
                season
                + episode
                + release_group
                + streaming_service
                + fps
                + source
                + audio_codec
                + resolution
                + video_codec
                + 1,
            ),
            # year counts as much as country
            Eq(year, country),
            # season is important too
            Eq(season, release_group + streaming_service + fps + source + audio_codec + resolution + video_codec + 1),
            # episode is equally important to season
            Eq(episode, season),
            # release group is the next most wanted match
            Eq(release_group, fps + source + audio_codec + resolution + video_codec + 1),
            # streaming service counts as much as release group
            Eq(release_group, streaming_service),
            # fps is the next most wanted match
            Eq(fps, source + audio_codec + resolution + video_codec + 1),
            # source counts as much as audio_codec, resolution and video_codec
            Eq(source, audio_codec + resolution + video_codec),
            # audio_codec is more valuable than video_codec
            Eq(audio_codec, video_codec + 1),
            # resolution counts as much as video_codec
            Eq(resolution, video_codec),
            # video_codec is the least valuable match, so put it to 1
            Eq(video_codec, 1),
        ]

        return solve(  # type: ignore[no-any-return]
            equations,
            [
                hash,
                series,
                year,
                country,
                season,
                episode,
                release_group,
                streaming_service,
                fps,
                source,
                audio_codec,
                resolution,
                video_codec,
            ],
        )

    def solve_movie_equations() -> dict[Symbol, int]:
        """Solve the score equation for Episodes.

        For testing purposes.
        """
        hash, title, year, country, release_group = symbols('hash title year country release_group')  # noqa: A001
        streaming_service, fps, source, audio_codec = symbols('streaming_service fps source audio_codec')
        resolution, video_codec = symbols('resolution video_codec')

        equations = [
            # hash is best
            Eq(
                hash,
                title
                + year
                + country
                + release_group
                + streaming_service
                + fps
                + source
                + audio_codec
                + resolution
                + video_codec,
            ),
            # title counts for the most part in the total score
            Eq(
                title,
                year
                + country
                + release_group
                + streaming_service
                + fps
                + source
                + audio_codec
                + resolution
                + video_codec
                + 1,
            ),
            # year is the second most important part
            Eq(year, release_group + streaming_service + fps + source + audio_codec + resolution + video_codec + 1),
            # year counts as much as country
            Eq(year, country),
            # release group is the next most wanted match
            Eq(release_group, fps + source + audio_codec + resolution + video_codec + 1),
            # streaming service counts as much as release group
            Eq(release_group, streaming_service),
            # fps is the next most wanted match
            Eq(fps, source + audio_codec + resolution + video_codec + 1),
            # source counts as much as audio_codec, resolution and video_codec
            Eq(source, audio_codec + resolution + video_codec),
            # audio_codec is more valuable than video_codec
            Eq(audio_codec, video_codec + 1),
            # resolution counts as much as video_codec
            Eq(resolution, video_codec),
            # video_codec is the least valuable match, so put it to 1
            Eq(video_codec, 1),
        ]

        return solve(  # type: ignore[no-any-return]
            equations,
            [
                hash,
                title,
                year,
                country,
                release_group,
                streaming_service,
                fps,
                source,
                audio_codec,
                resolution,
                video_codec,
            ],
        )
