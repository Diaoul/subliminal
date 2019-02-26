# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.greeksubtitles import GreekSubtitlesSubtitle, GreekSubtitlesProvider

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'greeksubtitles')))


def test_get_matches_episode(episodes):
    subtitle = GreekSubtitlesSubtitle(Language.fromalpha2('el'), '',
                                      'The Big Bang Theory S07E05 The Workplace Proximity 720p HDTV X264 DIMENSION', '')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'release_group', 'title', 'resolution', 'source', 'video_codec'}


def test_get_matches_movie(movies):
    subtitle = GreekSubtitlesSubtitle(Language.fromalpha2('el'), '',
                                      'Man Of Steel 2013 720p BluRay x264 Felony', '')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'release_group', 'title', 'resolution', 'source', 'video_codec', 'year'}


def test_get_matches_episode_no_match(episodes):
    subtitle = GreekSubtitlesSubtitle(Language.fromalpha2('el'), '',
                                      'The Big Bang Theory S07E05 The Workplace Proximity 720p HDTV X264 DIMENSION', '')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'resolution', 'video_codec'}


def test_get_matches_movie_no_match(movies):
    subtitle = GreekSubtitlesSubtitle(Language.fromalpha2('el'), '',
                                      'Man Of Steel 2013 720p BluRay x264 Felony', '')
    matches = subtitle.get_matches(movies['interstellar'])
    assert matches == {'source', 'video_codec'}


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['man_of_steel']
    expected_languages = {Language.fromalpha2('el')}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.query(video.title, year=video.year)
    assert len(subtitles) == 100
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_series(episodes):
    video = episodes['bbt_s07e05']
    expected_languages = {Language.fromalpha2('el')}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.query(video.series, video.season, video.episode)
    assert len(subtitles) == 51
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['dallas_s01e03']
    languages = {Language.fromalpha2('el')}
    expected_subtitles = {'http://www.greeksubtitles.info/getp.php?id=1025513'}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['enders_game']
    languages = {Language.fromalpha2('el')}
    expected_subtitles = {'http://www.greeksubtitles.info/getp.php?id=1579958',
                          'http://www.greeksubtitles.info/getp.php?id=1907640',
                          'http://www.greeksubtitles.info/getp.php?id=2279115',
                          'http://www.greeksubtitles.info/getp.php?id=1777195',
                          'http://www.greeksubtitles.info/getp.php?id=1792265',
                          'http://www.greeksubtitles.info/getp.php?id=1543273',
                          'http://www.greeksubtitles.info/getp.php?id=1552711',
                          'http://www.greeksubtitles.info/getp.php?id=1542877',
                          'http://www.greeksubtitles.info/getp.php?id=1761142',
                          'http://www.greeksubtitles.info/getp.php?id=1761143',
                          'http://www.greeksubtitles.info/getp.php?id=1560694',
                          'http://www.greeksubtitles.info/getp.php?id=1542886',
                          'http://www.greeksubtitles.info/getp.php?id=1773342',
                          'http://www.greeksubtitles.info/getp.php?id=1607193',
                          'http://www.greeksubtitles.info/getp.php?id=1543749',
                          'http://www.greeksubtitles.info/getp.php?id=1698179',
                          'http://www.greeksubtitles.info/getp.php?id=1543186',
                          'http://www.greeksubtitles.info/getp.php?id=1583790'}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_no_results(episodes):
    video = episodes['the_end_of_the_fucking_world']
    languages = {Language.fromalpha2('el')}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert subtitles == []
    assert {subtitle.language for subtitle in subtitles} == set()


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_no_results(movies):
    video = movies['interstellar']
    languages = {Language.fromalpha2('el')}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert subtitles == []
    assert {subtitle.language for subtitle in subtitles} == set()


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_episode(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language.fromalpha2('el')}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_movie(movies):
    video = movies['man_of_steel']
    languages = {Language.fromalpha2('el')}
    with GreekSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
