# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.exceptions import ConfigurationError, AuthenticationError
from subliminal.providers.xsubs import XSubsSubtitle, XSubsProvider

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'xsubs')))


def test_get_matches_episode(episodes):
    subtitle = XSubsSubtitle(Language.fromalpha2('el'), '', 'The Big Bang Theory', 7, 5, 2007,
                             'The Workplace Proximity', '720p.HDTV DIMENSION', '')
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'year', 'release_group', 'title', 'resolution', 'source',
                       'country'}


def test_get_matches_episode_no_match(episodes):
    subtitle = XSubsSubtitle(Language.fromalpha2('el'), '', 'The Big Bang Theory', 7, 5, 2007,
                             'The Workplace Proximity', '720p.HDTV DIMENSION', '')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'resolution', 'country'}


def test_configuration_error_no_username():
    with pytest.raises(ConfigurationError):
        XSubsProvider(password='subliminal')


def test_configuration_error_no_password():
    with pytest.raises(ConfigurationError):
        XSubsProvider(username='subliminal')


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = XSubsProvider('subliminal', 'subliminal')
    assert provider.logged_in is False
    provider.initialize()
    assert provider.logged_in is True
    r = provider.session.get(provider.server_url + '/xforum/search/?action=show_24h', allow_redirects=False)
    assert r.status_code == 200


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = XSubsProvider('subliminal', 'lanimilbus')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = XSubsProvider('subliminal', 'subliminal')
    provider.initialize()
    provider.terminate()
    assert provider.logged_in is False
    r = provider.session.get(provider.server_url + '/xforum/search/?action=show_24h', allow_redirects=False)
    assert r.status_code == 302


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id(episodes):
    video = episodes['bbt_s07e05']
    with XSubsProvider() as provider:
        titles = [video.series] + video.alternative_series
        show_id = provider.get_show_id(titles, video.year)
    assert show_id == 14


@pytest.mark.integration
@vcr.use_cassette
def test_query_series(episodes):
    video = episodes['bbt_s07e05']
    expected_languages = {Language.fromalpha2('el')}
    with XSubsProvider() as provider:
        subtitles = provider.query(14, video.series, video.season)
    assert len(subtitles) == 238
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_with_invalid_season_number():
    with XSubsProvider() as provider:
        subtitles = provider.query(622, "", 3)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_series_with_invalid_episode_number():
    with XSubsProvider() as provider:
        subtitles = provider.query(622, "", 1)
    assert len(subtitles) == 98


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language.fromalpha2('el')}
    expected_subtitles = {'http://xsubs.tv/xthru/getsub/44706',
                          'http://xsubs.tv/xthru/getsub/44707',
                          'http://xsubs.tv/xthru/getsub/63268',
                          'http://xsubs.tv/xthru/getsub/44708',
                          'http://xsubs.tv/xthru/getsub/44709',
                          'http://xsubs.tv/xthru/getsub/62937',
                          'http://xsubs.tv/xthru/getsub/44671',
                          'http://xsubs.tv/xthru/getsub/44674'}
    with XSubsProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_no_results(episodes):
    video = episodes['dallas_s01e03']
    languages = {Language.fromalpha2('el')}
    with XSubsProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert subtitles == []
    assert {subtitle.language for subtitle in subtitles} == set()


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_episode(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language.fromalpha2('el')}
    with XSubsProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
