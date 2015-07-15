# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from subliminal.score import solve_episode_equations, solve_movie_equations
from subliminal.video import Episode, Movie


def test_episode_equations():
    expected_scores = {}
    for symbol, score in solve_episode_equations().items():
        expected_scores[str(symbol)] = score

    assert Episode.scores == expected_scores


def test_movie_equations():
    expected_scores = {}
    for symbol, score in solve_movie_equations().items():
        expected_scores[str(symbol)] = score

    assert Movie.scores == expected_scores
