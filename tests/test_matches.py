from typing import cast

import pytest

from subliminal.matches import guess_matches
from subliminal.video import Episode, Movie

# Core test
pytestmark = pytest.mark.core


def test_guess_matches_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    guess = {
        'title': video.title.upper(),
        'year': video.year,
        'release_group': cast('str', video.release_group).upper(),
        'screen_size': video.resolution,
        'source': video.source,
        'video_codec': video.video_codec,
        'audio_codec': video.audio_codec,
    }
    expected = {'title', 'year', 'country', 'release_group', 'resolution', 'source', 'video_codec', 'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    guess = {
        'title': video.series,
        'season': video.season,
        'episode': video.episode,
        'year': video.year,
        'episode_title': cast('str', video.title).upper(),
        'release_group': cast('str', video.release_group).upper(),
        'screen_size': video.resolution,
        'source': video.source,
        'video_codec': video.video_codec,
        'audio_codec': video.audio_codec,
    }
    expected = {
        'series',
        'season',
        'episode',
        'title',
        'year',
        'country',
        'release_group',
        'resolution',
        'source',
        'video_codec',
        'audio_codec',
    }
    assert guess_matches(video, guess) == expected


def test_guess_matches_country(episodes: dict[str, Episode]) -> None:
    video = episodes['shameless_us_s08e01']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode, 'country': video.country}
    expected = {'series', 'season', 'episode', 'country'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode_equivalent_release_group(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    guess = {
        'title': video.series,
        'season': video.season,
        'episode': video.episode,
        'year': video.year,
        'episode_title': cast('str', video.title).upper(),
        'release_group': 'LOL',
        'screen_size': video.resolution,
        'source': video.source,
        'video_codec': video.video_codec,
        'audio_codec': video.audio_codec,
    }
    expected = {
        'series',
        'season',
        'episode',
        'title',
        'year',
        'country',
        'release_group',
        'resolution',
        'source',
        'video_codec',
        'audio_codec',
    }
    assert guess_matches(video, guess) == expected


def test_guess_matches_multiple_sources_no_match(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    guess = {
        'title': video.series,
        'season': video.season,
        'episode': video.episode,
        'year': video.year,
        'episode_title': cast('str', video.title).upper(),
        'release_group': 'LOL',
        'screen_size': video.resolution,
        'source': [video.source, 'Blu-ray'],
        'video_codec': video.video_codec,
        'audio_codec': video.audio_codec,
    }
    expected = {
        'series',
        'season',
        'episode',
        'title',
        'year',
        'country',
        'release_group',
        'resolution',
        'video_codec',
        'audio_codec',
    }
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode_no_year(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_s01e03']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode}
    expected = {'series', 'season', 'episode', 'year', 'country'}
    assert guess_matches(video, guess) == expected
