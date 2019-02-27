# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal import Episode
from subliminal.providers.subz import SubzSubtitle, SubzProvider

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'subz')))


def test_get_matches_episode(episodes):
    subtitle = SubzSubtitle(Language.fromalpha2('el'), '', 'The Big Bang Theory', 7, 5, 'The Workplace Proximity', None,
                            'The Big Bang Theory-07x05-The Workplace Proximity DIMENSION 720p.HDTV', '')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'release_group', 'resolution', 'source', 'year', 'country',
                       'title'}


def test_get_matches_episode_no_match(episodes):
    subtitle = SubzSubtitle(Language.fromalpha2('el'), '', 'The Big Bang Theory', 7, 5, 'The Workplace Proximity', None,
                            'The Big Bang Theory-07x05-The Workplace Proximity DIMENSION 720p.HDTV', '')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'resolution', 'year', 'country'}


def test_get_matches_movie(movies):
    subtitle = SubzSubtitle(Language.fromalpha2('el'), '', None, None, None, 'Man of Steel', 2013,
                            'man-of-steel-2013-720p-bluray-x264-felony', '')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'release_group', 'title', 'resolution', 'source', 'year', 'video_codec', 'country'}


def test_get_matches_movie_no_match(movies):
    subtitle = SubzSubtitle(Language.fromalpha2('el'), '', None, None, None, 'Man of Steel', 2013,
                            'man-of-steel-2013-720p-bluray-x264-felony', '')
    matches = subtitle.get_matches(movies['enders_game'])
    assert matches == {'resolution', 'year', 'video_codec', 'source', 'country'}


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_links_episode(episodes):
    video = episodes['bbt_s07e05']
    with SubzProvider() as provider:
        show_links = provider.get_show_links(video.series, video.year, isinstance(video, Episode))
    assert show_links == ['25376-the-big-bang-theory']


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_links_movie(movies):
    video = movies['man_of_steel']
    with SubzProvider() as provider:
        show_links = provider.get_show_links(video.title, video.year, isinstance(video, Episode))
    assert show_links == ['20376-man-of-steel', '1661939-man-of-steel']


@pytest.mark.integration
@vcr.use_cassette
def test_query_series(episodes):
    video = episodes['got_s03e10']
    expected_languages = {Language.fromalpha2('el')}
    with SubzProvider() as provider:
        subtitles = provider.query('25378-game-of-thrones', video.series,  video.season, video.episode, video.title)
    assert len(subtitles) == 1
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_no_results(episodes):
    video = episodes['bbt_s07e05']
    with SubzProvider() as provider:
        subtitles = provider.query('25376-the-big-bang-theory', video.series,  video.season, video.episode, video.title)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['man_of_steel']
    expected_languages = {Language.fromalpha2('el')}
    with SubzProvider() as provider:
        subtitles = provider.query('20376-man-of-steel', None, None, None, video.title)
    assert len(subtitles) == 10
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie_no_results(movies):
    video = movies['enders_game']
    with SubzProvider() as provider:
        subtitles = provider.query('30012-enders-game', None, None, None, video.title)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language.fromalpha2('el')}
    expected_subtitles = {'http://files.subz.xyz/repository/Series/G/Game%20of%20Thrones%20%282011%29/Season%2003'
                          '/Game.of.Thrones.S03E10.HDTV-BluRay-BDRip.WEB-DL.zip'}
    with SubzProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_no_results(episodes):
    video = episodes['dallas_s01e03']
    languages = {Language.fromalpha2('el')}
    with SubzProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert subtitles == []


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language.fromalpha2('el')}
    expected_subtitles = {'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-720p-bluray-x264-felony-bluray-720p-dts-marge-a-t3ll4v1s10n8482-sub.zip',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-1080p-bluray-dts-x264-hdmaniacs-1080p-bluray-x264-sector7-a-t3ll4v1s10n8482-sub.zip',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-720p-bdrip-x264-aac-dnt-a-t3ll4v1s10n8482-sub.zip',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-1080p-bluray-dts-x264-hdmaniacs-dvd.zip',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-1080p-brrip-x264-ac3-jyk-540p-bdrip-qebsx-aac-2-0-fasm-a-t3ll4v1s10n8482-sub.zip',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-720p-bluray-x264-felony.rar',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-3d-720p-brrip-x264-yify.rar',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-720p-brrip-x264-aac-vice-a-t3ll4v1s10n8482-sub.zip',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-brrip-xvid-rarbg-larceny-cpg-4playhd-a-t3ll4v1s10n8482-sub.zip',
                          'http://files.subz.xyz/repository/Movies/M/Man%20of%20Steel%20%282013%29/man-of-steel-2013'
                          '-1080p-bluray-x264-yify.zip'}
    with SubzProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_no_results(movies):
    video = movies['enders_game']
    languages = {Language.fromalpha2('el')}
    with SubzProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert subtitles == []


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language.fromalpha2('el')}
    with SubzProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_movie(movies):
    video = movies['man_of_steel']
    languages = {Language.fromalpha2('el')}
    with SubzProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[1])
    assert subtitles[1].content is not None
    assert subtitles[1].is_valid() is True
