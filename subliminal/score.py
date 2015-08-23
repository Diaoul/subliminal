# -*- coding: utf-8 -*-
"""
This module is responsible for calculating the :attr:`~subliminal.video.Video.scores` dicts
(:attr:`Episode.scores <subliminal.video.Episode.scores>` and :attr:`Movie.scores <subliminal.video.Movie.scores>`)
by assigning a score to a match.

.. note::

    To avoid unnecessary dependency on `sympy <http://www.sympy.org/>`_ and boost subliminal's import time, the
    resulting scores are hardcoded in their respective classes and manually updated when the set of equations change.

Available matches:

  * hearing_impaired
  * format
  * release_group
  * resolution
  * video_codec
  * audio_codec
  * imdb_id
  * hash
  * title
  * year
  * series
  * season
  * episode
  * tvdb_id


The :meth:`Subtitle.get_matches <subliminal.subtitle.Subtitle.get_matches>` method get the matches between the
:class:`~subliminal.subtitle.Subtitle` and the :class:`~subliminal.video.Video` and
:func:`~subliminal.subtitle.compute_score` computes the score.

"""
from __future__ import print_function

from sympy import Eq, solve, symbols


# Symbols
hearing_impaired, format, release_group, resolution = symbols('hearing_impaired format release_group resolution')
video_codec, audio_codec, imdb_id, hash, title, year = symbols('video_codec audio_codec imdb_id hash title year')
series, season, episode, tvdb_id = symbols('series season episode tvdb_id')


def solve_episode_equations():
    """Solve the score equations for an :class:`~subliminal.video.Episode`.

    The equations are the following:

    1. hash = resolution + format + video_codec + audio_codec + series + season + episode + year + release_group
    2. series = resolution + video_codec + audio_codec + season + episode + release_group + 1
    3. year = series
    4. tvdb_id = series + year
    5. season = resolution + video_codec + audio_codec + 1
    6. imdb_id = series + season + episode + year
    7. format = video_codec + audio_codec
    8. resolution = video_codec
    9. video_codec = 2 * audio_codec
    10. title = season + episode
    11. season = episode
    12. release_group = season
    13. audio_codec = 2 * hearing_impaired
    14. hearing_impaired = 1

    :return: the result of the equations.
    :rtype: dict

    """
    equations = [
        Eq(hash, resolution + format + video_codec + audio_codec + series + season + episode + year + release_group),
        Eq(series, resolution + video_codec + audio_codec + season + episode + release_group + 1),
        Eq(year, series),
        Eq(tvdb_id, series + year),
        Eq(season, resolution + video_codec + audio_codec + 1),
        Eq(imdb_id, series + season + episode + year),
        Eq(format, video_codec + audio_codec),
        Eq(resolution, video_codec),
        Eq(video_codec, 2 * audio_codec),
        Eq(title, season + episode),
        Eq(season, episode),
        Eq(release_group, season),
        Eq(audio_codec, 2 * hearing_impaired),
        Eq(hearing_impaired, 1)
    ]

    return solve(equations, [hearing_impaired, format, release_group, resolution, video_codec, audio_codec, imdb_id,
                             hash, series, season, episode, title, year, tvdb_id])


def solve_movie_equations():
    """Solve the score equations for a :class:`~subliminal.video.Movie`.

    The equations are the following:

    1. hash = resolution + format + video_codec + audio_codec + title + year + release_group
    2. imdb_id = hash
    3. resolution = video_codec
    4. video_codec = 2 * audio_codec
    5. format = video_codec + audio_codec
    6. title = resolution + video_codec + audio_codec + year + 1
    7. release_group = resolution + video_codec + audio_codec + 1
    8. year = release_group + 1
    9. audio_codec = 2 * hearing_impaired
    10. hearing_impaired = 1

    :return: the result of the equations.
    :rtype: dict

    """
    equations = [
        Eq(hash, resolution + format + video_codec + audio_codec + title + year + release_group),
        Eq(imdb_id, hash),
        Eq(resolution, video_codec),
        Eq(video_codec, 2 * audio_codec),
        Eq(format, video_codec + audio_codec),
        Eq(title, resolution + video_codec + audio_codec + year + 1),
        Eq(release_group, resolution + video_codec + audio_codec + 1),
        Eq(year, release_group + 1),
        Eq(audio_codec, 2 * hearing_impaired),
        Eq(hearing_impaired, 1)
    ]

    return solve(equations, [hearing_impaired, format, release_group, resolution, video_codec, audio_codec, imdb_id,
                             hash, title, year])
