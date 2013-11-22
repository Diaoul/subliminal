#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from sympy import Eq, symbols, solve


# Symbols
release_group, resolution, video_codec, audio_codec = symbols('release_group resolution video_codec audio_codec')
imdb_id, hash, title, series, tvdb_id, season, episode = symbols('imdb_id hash title series tvdb_id season episode')  # @ReservedAssignment
year = symbols('year')


def get_episode_equations():
    """Get the score equations for a :class:`~subliminal.video.Episode`

    The equations are the following:

    1. hash = resolution + video_codec + audio_codec + series + season + episode + release_group
    2. series = resolution + video_codec + audio_codec + season + episode + 1
    3. tvdb_id = series
    4. season = resolution + video_codec + audio_codec + 1
    5. imdb_id = series + season + episode
    6. resolution = video_codec
    7. video_codec = 2 * audio_codec
    8. title = season + episode
    9. season = episode
    10. release_group = season
    11. audio_codec = 1

    :return: the score equations for an episode
    :rtype: list of :class:`sympy.Eq`

    """
    equations = []
    equations.append(Eq(hash, resolution + video_codec + audio_codec + series + season + episode + release_group))
    equations.append(Eq(series, resolution + video_codec + audio_codec + season + episode + release_group))
    equations.append(Eq(tvdb_id, series))
    equations.append(Eq(season, resolution + video_codec + audio_codec + 1))
    equations.append(Eq(imdb_id, series + season + episode))
    equations.append(Eq(resolution, video_codec))
    equations.append(Eq(video_codec, 2 * audio_codec))
    equations.append(Eq(title, season + episode))
    equations.append(Eq(season, episode))
    equations.append(Eq(release_group, season))
    equations.append(Eq(audio_codec, 1))
    return equations


def get_movie_equations():
    """Get the score equations for a :class:`~subliminal.video.Movie`

    The equations are the following:

    1. hash = resolution + video_codec + audio_codec + title + year + release_group
    2. imdb_id = hash
    3. resolution = video_codec
    4. video_codec = 2 * audio_codec
    5. title = resolution + video_codec + audio_codec + year + 1
    6. release_group = resolution + video_codec + audio_codec + 1
    7. year = release_group + 1
    8. audio_codec = 1

    :return: the score equations for a movie
    :rtype: list of :class:`sympy.Eq`

    """
    equations = []
    equations.append(Eq(hash, resolution + video_codec + audio_codec + title + year + release_group))
    equations.append(Eq(imdb_id, hash))
    equations.append(Eq(resolution, video_codec))
    equations.append(Eq(video_codec, 2 * audio_codec))
    equations.append(Eq(title, resolution + video_codec + audio_codec + year + 1))
    equations.append(Eq(video_codec, 2 * audio_codec))
    equations.append(Eq(release_group, resolution + video_codec + audio_codec + 1))
    equations.append(Eq(year, release_group + 1))
    equations.append(Eq(audio_codec, 1))
    return equations


if __name__ == '__main__':
    print(solve(get_episode_equations(), [release_group, resolution, video_codec, audio_codec, imdb_id,
                                          hash, series, tvdb_id, season, episode, title]))
    print(solve(get_movie_equations(), [release_group, resolution, video_codec, audio_codec, imdb_id,
                                        hash, title, year]))
