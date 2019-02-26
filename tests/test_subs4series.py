# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.subs4series import Subs4SeriesSubtitle, Subs4SeriesProvider

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'subs4series')))


def test_get_matches_episode(episodes):
    subtitle = Subs4SeriesSubtitle(Language.fromalpha2('el'), '', 'The Big Bang Theory', 2007,
                                   'The Big Bang Theory-07x05-The Workplace Proximity DIMENSION 720p.HDTV', '')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'release_group', 'resolution', 'source', 'year'}


def test_get_matches_episode_no_match(episodes):
    subtitle = Subs4SeriesSubtitle(Language.fromalpha2('el'), '', 'The Big Bang Theory', 2007,
                                   'The Big Bang Theory-07x05-The Workplace Proximity DIMENSION 720p.HDTV', '')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'resolution'}


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_links_episode(episodes):
    video = episodes['bbt_s07e05']
    with Subs4SeriesProvider() as provider:
        show_links = provider.get_show_links(video.series, video.year)
    assert show_links == ['the-big-bang-theory/s5ab151fda0']


@pytest.mark.integration
@vcr.use_cassette
def test_query_series(episodes):
    video = episodes['got_s03e10']
    expected_languages = {Language.fromalpha2(l) for l in ['el', 'en']}
    with Subs4SeriesProvider() as provider:
        subtitles = provider.query('game-of-thrones/s8985ffc551', video.series, video.season, video.episode,
                                   video.title)
    assert len(subtitles) == 14
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_no_results(episodes):
    video = episodes['dallas_2012_s01e03']
    with Subs4SeriesProvider() as provider:
        subtitles = provider.query('dallas-2012/s0f8ede4098', video.series, video.season, video.episode,
                                   video.title)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language.fromalpha2('el')}
    expected_subtitles = {
        'https://www.subs4series.com/greek-subtitles/s7ee8587992/game-of-thrones-s03e10-480p-hdtv-x264-msd',
        'https://www.subs4series.com/greek-subtitles/s1d6fdad065/game-of-thrones-s03e10-720p-hdtv-x264-evolve',
        'https://www.subs4series.com/greek-subtitles/s2847507d55/game-of-thrones-s03e10-hdtv-x264-evolve',
        'https://www.subs4series.com/greek-subtitles/sc07bd9a689/game-of-thrones-s03e10-hdtv-xvid-3lt0n',
        'https://www.subs4series.com/greek-subtitles/s51a22613e9/game-of-thrones-s03e10-hdtv-xvid-afg',
        'https://www.subs4series.com/greek-subtitles/s1727b4efd8/game-of-thrones-s03e10-720p-hdtv-x264-evolve',
        'https://www.subs4series.com/greek-subtitles/s21eefad355/game-of-thrones-s03e10-hdtv-x264-evolve',
        'https://www.subs4series.com/greek-subtitles/s869941cf2a/game-of-thrones-s03e10-720p-hdtv-x264-evolve',
        'https://www.subs4series.com/greek-subtitles/s3a5de8717e/game-of-thrones-s03e10-mhysa-hdtv-x264-evolve-720p'
        '-1080i-web-dl-ctrlhd-xsubs-tv',
        'https://www.subs4series.com/greek-subtitles/s1d3af0eb5/game-of-thrones-s03e10-mhysa-msd-3lt0n-evolve-afg'
        '-720p-evolve',
        'https://www.subs4series.com/greek-subtitles/s777bf1e70/game-of-thrones-s03e10-mhysa-web-dl-dd5-1-h-264-ntb'}
    with Subs4SeriesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_no_results(episodes):
    video = episodes['dallas_2012_s01e03']
    languages = {Language.fromalpha2('el')}
    with Subs4SeriesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert subtitles == []


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language.fromalpha2('el')}
    with Subs4SeriesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_episode_rar(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language.fromalpha2('el')}
    with Subs4SeriesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_episode_zip(episodes):
    video = episodes['marvels_agents_of_shield_s02e06']
    languages = {Language.fromalpha2('el')}
    with Subs4SeriesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
