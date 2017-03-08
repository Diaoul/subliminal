# -*- coding: utf-8 -*-
import os
from hashlib import md5

import pytest
from babelfish import Language
from vcr import VCR

from subliminal.video import Episode
from subliminal.providers.subscene import SubsceneSubtitle, SubsceneProvider
from subliminal.exceptions import ConfigurationError


match_on = ['method', 'scheme', 'host', 'port', 'path', 'query', 'body']
vcr_dir = os.path.realpath(os.path.join('tests', 'cassettes', 'subscene'))
vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=match_on, cassette_library_dir=vcr_dir)


def test_get_matches_movie_resolution(movies):
    subtitle = SubsceneSubtitle(Language('deu'), year=2013, info='Man.of.Steel'
                                '.German.720p.BluRay.x264',
                                imdb_id='tt0770828')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'video_codec', 'imdb_id', 'source',
                       'resolution'}


def test_get_matches_episode_year(episodes):
    subtitle = SubsceneSubtitle(Language('eng'), imdb_id='tt2178796',
                                info='Game.of.Thrones.S03E10.WEBDL.XviD-AFG')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'imdb_id', 'series', 'episode', 'season', 'source'}


def test_get_matches_episode_title(episodes):
    subtitle = SubsceneSubtitle(Language('spa'), year=2012, info='Dallas.2012.'
                                'The.Price.You.Pay.S01E03.HDTV.x264-LOL',
                                imdb_id='tt2205526')
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == {'imdb_id', 'series', 'year', 'episode', 'season',
                       'title'}


def test_get_matches_episode_release_type(episodes):
    subtitle = SubsceneSubtitle(Language('spa'), year=2012, info='CSI.Cyber.S0'
                                '2E03.lol.mp4', imdb_id='tt2205526',
                                release_type='HDTV')
    matches = subtitle.get_matches(episodes['csi_cyber_s02e03'])
    assert matches == {'series', 'episode', 'season', 'source'}


def test_get_matches_episode_filename(episodes):
    subtitle = SubsceneSubtitle(Language('por', country='BR'), year=2014,
                                imdb_id='tt4078580', info='Marvels.Agents.of.S'
                                '.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv')
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {'name', 'series', 'season', 'episode', 'release_group',
                       'source', 'resolution', 'video_codec'}


def test_get_matches_movie_release_name(movies):
    subtitle = SubsceneSubtitle(Language('fas'), release_name='Interstellar')
    matches = subtitle.get_matches(movies['interstellar'])
    assert matches == {'title'}


def test_get_matches_imdb_id(movies):
    subtitle = SubsceneSubtitle(Language('fra'), year=2013, info='man.of.steel'
                                '.2013.720p.bluray.x264-felony',
                                imdb_id='tt0770828')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'name', 'title', 'year', 'video_codec', 'imdb_id',
                       'resolution', 'source', 'release_group'}


def test_get_matches_no_match(episodes):
    subtitle = SubsceneSubtitle(Language('fra'), year=2013, info='man.of.steel'
                                '.2013.720i.HDCAM.Xvid-felony',
                                imdb_id='tt0770828')
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


def test_converter_convert():
    assert Language('pus').subscene == 'Pashto'
    assert Language('deu').subscene == 'German'
    with pytest.raises(ConfigurationError, match='unsupported'):
        Language('got').subscene


def test_converter_reverse():
    assert Language.fromsubscene('Farsi/Persian') == Language('fas')
    assert Language.fromsubscene('English') == Language('eng')
    with pytest.raises(NotImplementedError, match='unspecified'):
        Language.fromsubscene('Big 5 code')
    with pytest.raises(ConfigurationError, match='unknown'):
        Language.fromsubscene('Big 4 code')


@pytest.mark.integration
@vcr.use_cassette
def test_provider_initialization():
    provider = SubsceneProvider()
    assert provider._baseurl == 'http://subscene.com'
    assert SubsceneProvider(force_ssl=True)._baseurl == 'https://subscene.com'
    assert provider._session is None
    provider.initialize()
    assert provider._session is not None
    assert provider._baseurl in ['%s://subscene.com' % protocol
                                 for protocol in ('http', 'https')]
    provider.terminate()
    assert provider._session is None


@pytest.mark.integration
@vcr.use_cassette
def test_provider_query_movie(movies):
    video = movies['man_of_steel']
    with SubsceneProvider() as provider:
        subtitles = provider.query(video.title, video.year)
    assert len(subtitles) == 626
    subtitle = subtitles.pop()
    assert subtitle.imdb_id == video.imdb_id
    assert subtitle.year == video.year
    assert subtitle.release_name == video.title


@pytest.mark.integration
@vcr.use_cassette
def test_provider_query_episode(episodes):
    video = episodes['colony_s01e09']
    title = '%s - First Season' % video.series
    with SubsceneProvider() as provider:
        subtitles = provider.query(title, video.year)
    assert len(subtitles) >= 254


@pytest.mark.integration
@vcr.use_cassette
def test_provider_query_movie_ssf(movies):
    video = movies['man_of_steel']
    lang = Language('deu')
    with SubsceneProvider() as provider:
        subtitles = provider.query(video.title, video.year, {lang})
    assert len(subtitles) == 8
    assert all(map(lambda sub: sub.language == lang, subtitles))
    assert all(map(lambda sub: sub.num_files == 1, subtitles))
    assert any(map(lambda sub: sub.hearing_impaired, subtitles))
    assert any(map(lambda sub: not sub.hearing_impaired, subtitles))


@pytest.mark.integration
@vcr.use_cassette
def test_provider_query_movie_manual_filter(movies):
    video = movies['interstellar']
    langs = {Language('fin'), Language('heb'), Language('hin'), Language('kor')}
    with SubsceneProvider() as provider:
        subtitles = provider.query(video.title, video.year, langs)
    assert len(subtitles) == 21
    assert all(map(lambda sub: sub.language in langs, subtitles))


@pytest.mark.integration
@vcr.use_cassette
def test_provider_list_subtitles(movies):
    video = movies['café_society']
    with SubsceneProvider() as provider:
        subtitles = provider.list_subtitles(video, {Language('deu')})
    assert len(subtitles) == 4
    assert all(map(lambda sub: sub.year == video.year, subtitles))
    assert all(map(lambda sub: sub.imdb_id == 'tt4513674', subtitles))


@pytest.mark.integration
@vcr.use_cassette
def test_provider_list_subtitles_episode(episodes):
    video = episodes['colony_s01e09']
    langs = {Language('nor'), Language('tur'), Language('kor')}
    with SubsceneProvider() as provider:
        subtitles = provider.list_subtitles(video, langs)
    assert len(subtitles) == 5
    assert all(map(lambda sub: sub.imdb_id == 'tt4209256', subtitles))
    assert all(map(lambda sub: sub.language in langs, subtitles))


@pytest.mark.integration
@vcr.use_cassette
def test_provider_download_subtitle_movie(movies):
    video = movies['café_society']
    with SubsceneProvider() as provider:
        subtitles = provider.list_subtitles(video, {Language('fas')})
        assert len(subtitles) > 10
        subtitle = next(iter(filter(lambda s: s.id.endswith('1406621'), subtitles)))
        assert subtitle.year == video.year
        assert subtitle.zip_link is None
        provider.download_subtitle(subtitle)
        assert subtitle.zip_link is not None
        subtitle.encoding = 'cp1256'
        hashed = md5(subtitle.text.encode('UTF-8')).hexdigest()
        assert hashed == '14d07996637bfd881532ef1d45a2157c'


@pytest.mark.integration
@vcr.use_cassette
def test_provider_download_subtitle_episode():
    video = Episode('Breaking.Bad.S03E13.Full.Measure.HDTV.XviD-FQM',
                    'Breaking Bad', 3, 13, 'Full Measure')
    with SubsceneProvider() as provider:
        subtitles = provider.list_subtitles(video, {Language('swe')})
        assert len(subtitles) == 4
        subtitle = next(iter(filter(lambda s: s.id.endswith('385845'), subtitles)))
        assert subtitle.zip_link is None
        provider.download_subtitle(subtitle)
        assert subtitle.zip_link is not None
        hashed = md5(subtitle.text.encode('UTF-8')).hexdigest()
        assert hashed == '9b97d0d2259170d019907e85519cb42d'
