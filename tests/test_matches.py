# -*- coding: utf-8 -*-
from subliminal.matches import guess_matches


def test_guess_matches_movie(movies):
    video = movies['man_of_steel']
    guess = {'title': video.title.upper(), 'year': video.year, 'release_group': video.release_group.upper(),
             'screen_size': video.resolution, 'source': video.source, 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'title', 'year', 'country', 'release_group', 'resolution', 'source', 'video_codec', 'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode(episodes):
    video = episodes['bbt_s07e05']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode, 'year': video.year,
             'episode_title': video.title.upper(), 'release_group': video.release_group.upper(),
             'screen_size': video.resolution, 'source': video.source, 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'resolution', 'source',
                'video_codec', 'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode_equivalent_release_group(episodes):
    video = episodes['bbt_s07e05']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode, 'year': video.year,
             'episode_title': video.title.upper(), 'release_group': 'LOL',
             'screen_size': video.resolution, 'source': video.source, 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'resolution', 'source',
                'video_codec', 'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_multiple_sources(episodes):
    video = episodes['bbt_s07e05']
    video.source = [video.source, 'Blu-ray']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode, 'year': video.year,
             'episode_title': video.title.upper(), 'release_group': 'LOL',
             'screen_size': video.resolution, 'source': video.source, 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'resolution', 'source',
                'video_codec', 'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_multiple_sources_no_match(episodes):
    video = episodes['bbt_s07e05']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode, 'year': video.year,
             'episode_title': video.title.upper(), 'release_group': 'LOL',
             'screen_size': video.resolution, 'source': [video.source, 'Blu-ray'], 'video_codec': video.video_codec,
             'audio_codec': video.audio_codec}
    expected = {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'resolution', 'video_codec',
                'audio_codec'}
    assert guess_matches(video, guess) == expected


def test_guess_matches_episode_no_year(episodes):
    video = episodes['dallas_s01e03']
    guess = {'title': video.series, 'season': video.season, 'episode': video.episode}
    expected = {'series', 'season', 'episode', 'year', 'country'}
    assert guess_matches(video, guess) == expected
