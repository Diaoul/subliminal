from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from subliminal.score import compute_score, episode_scores, movie_scores, solve_episode_equations, solve_movie_equations

if TYPE_CHECKING:
    from subliminal.providers.mock import MockSubtitle
    from subliminal.video import Episode, Movie

# Core test
pytestmark = pytest.mark.core


def test_episode_equations() -> None:
    expected_scores = {}
    for symbol, score in solve_episode_equations().items():
        expected_scores[str(symbol)] = score

    assert episode_scores == expected_scores


def test_movie_equations() -> None:
    expected_scores = {}
    for symbol, score in solve_movie_equations().items():
        expected_scores[str(symbol)] = score

    assert movie_scores == expected_scores


def test_compute_score(episodes: dict[str, Episode], subtitles: dict[str, MockSubtitle]) -> None:
    video = episodes['bbt_s07e05']
    subtitle = subtitles['bbt_s07e05==series_year_country']
    expected_score = episode_scores['series'] + episode_scores['year'] + episode_scores['country']
    assert compute_score(subtitle, video) == expected_score


def test_get_score_cap(movies: dict[str, Movie], subtitles: dict[str, MockSubtitle]) -> None:
    video = movies['man_of_steel']
    subtitle = subtitles['man_of_steel==hash']

    expected_matches = {'hash', 'country'}
    assert subtitle.get_matches(video) == expected_matches

    expected = movie_scores['hash']
    assert compute_score(subtitle, video) == expected


def test_compute_score_movie_imdb_id(movies: dict[str, Movie], subtitles: dict[str, MockSubtitle]) -> None:
    video = movies['man_of_steel']
    subtitle = subtitles['man_of_steel==imdb_id']
    expected = sum(
        movie_scores.get(m, 0)
        for m in ('imdb_id', 'title', 'year', 'country', 'release_group', 'source', 'resolution', 'video_codec')
    )
    assert compute_score(subtitle, video) == expected


def test_compute_score_episode_title(episodes: dict[str, Episode], subtitles: dict[str, MockSubtitle]) -> None:
    video = episodes['bbt_s07e05']
    subtitle = subtitles['bbt_s07e05==episode_title']
    expected = sum(
        episode_scores.get(m, 0)
        for m in (
            'series',
            'year',
            'country',
            'season',
            'episode',
            'release_group',
            'source',
            'resolution',
            'video_codec',
            'title',
        )
    )
    assert compute_score(subtitle, video) == expected


@pytest.mark.parametrize('id_type', ['imdb_id', 'tmdb_id', 'tvdb_id'])
def test_compute_score_episode_imdb_id_only(
    episodes: dict[str, Episode],
    subtitles: dict[str, MockSubtitle],
    id_type: str,
) -> None:
    video = episodes['bbt_s07e05']
    subtitle = subtitles['bbt_s07e05==empty']
    subtitle.matches.clear()
    subtitle.matches.add(id_type)

    expected = sum(episode_scores.get(m, 0) for m in ('series', 'year', 'country', 'season', 'episode'))
    assert compute_score(subtitle, video) == expected


@pytest.mark.parametrize('id_type', ['series_imdb_id', 'series_tmdb_id', 'series_tvdb_id'])
def test_compute_score_episode_series_imdb_id_only(
    episodes: dict[str, Episode],
    subtitles: dict[str, MockSubtitle],
    id_type: str,
) -> None:
    video = episodes['bbt_s07e05']
    subtitle = subtitles['bbt_s07e05==empty']
    subtitle.matches.clear()
    subtitle.matches.add(id_type)

    expected = sum(episode_scores.get(m, 0) for m in ('series', 'year', 'country'))
    assert compute_score(subtitle, video) == expected


@pytest.mark.parametrize('id_type', ['imdb_id', 'tmdb_id'])
def test_compute_score_movie_imdb_id_only(
    movies: dict[str, Movie],
    subtitles: dict[str, MockSubtitle],
    id_type: str,
) -> None:
    video = movies['man_of_steel']
    subtitle = subtitles['man_of_steel==empty']
    subtitle.matches.clear()
    subtitle.matches.add(id_type)

    expected = sum(movie_scores.get(m, 0) for m in ('title', 'year', 'country'))
    assert compute_score(subtitle, video) == expected
