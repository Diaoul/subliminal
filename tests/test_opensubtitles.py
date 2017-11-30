# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.exceptions import ConfigurationError
from subliminal.providers.opensubtitles import OpenSubtitlesProvider, OpenSubtitlesSubtitle, Unauthorized


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'opensubtitles')))


def test_get_matches_movie_hash(movies):
    subtitle = OpenSubtitlesSubtitle(Language('deu'), False, None, '1953771409', 'moviehash', 'movie',
                                     '5b8f8f4e41ccb21e', 'Man of Steel',
                                     'Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE', 2013, 'tt0770828', 0, 0,
                                     'Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE.srt', None)
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'video_codec', 'imdb_id', 'hash', 'resolution', 'format'}


def test_get_matches_episode(episodes):
    subtitle = OpenSubtitlesSubtitle(Language('ell'), False, None, '1953579014', 'fulltext', 'episode',
                                     '0', '"Game of Thrones" Mhysa',
                                     ' Game.of.Thrones.S03E10.HDTV.XviD-AFG', 2013, 'tt2178796', 3, 10,
                                     'Game.of.Thrones.S03E10.HDTV.XviD-AFG.srt', None)
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'imdb_id', 'series', 'year', 'episode', 'season', 'title'}


def test_get_matches_episode_year(episodes):
    subtitle = OpenSubtitlesSubtitle(Language('spa'), False, None, '1953369959', 'tag', 'episode',
                                     '0', '"Dallas" The Price You Pay',
                                     ' Dallas.2012.S01E03.HDTV.x264-LOL', 2012, 'tt2205526', 1, 3,
                                     'Dallas.2012.S01E03.HDTV.x264-LOL.srt', 'cp1252')
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == {'imdb_id', 'series', 'year', 'episode', 'season', 'title'}


def test_get_matches_episode_filename(episodes):
    subtitle = OpenSubtitlesSubtitle(Language('por', country='BR'), False, None, '1954453973', 'fulltext', 'episode',
                                     '0', '"Agents of S.H.I.E.L.D." A Fractured House',
                                     'HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS', 2014, 'tt4078580', 2, 6,
                                     'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.srt', 'cp1252')
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {'series', 'year', 'season', 'episode', 'release_group', 'format', 'resolution', 'video_codec'}


def test_get_matches_episode_tag(episodes):
    subtitle = OpenSubtitlesSubtitle(Language('por', country='BR'), False, None, '1954453973', 'tag', 'episode',
                                     '0', '"Agents of S.H.I.E.L.D." A Fractured House',
                                     'HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS', 2014, 'tt4078580', 2, 6,
                                     '', 'cp1252')
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {'series', 'year', 'season', 'episode', 'format', 'video_codec'}


def test_get_matches_imdb_id(movies):
    subtitle = OpenSubtitlesSubtitle(Language('fra'), True, None, '1953767650', 'imdbid', 'movie', 0, 'Man of Steel',
                                     'man.of.steel.2013.720p.bluray.x264-felony', 2013, 'tt0770828', 0, 0,
                                     'man.of.steel.2013.720p.bluray.x264-felony.srt', None)
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'video_codec', 'imdb_id', 'resolution', 'format', 'release_group'}


def test_get_matches_no_match(episodes):
    subtitle = OpenSubtitlesSubtitle(Language('fra'), False, None, '1953767650', 'imdbid', 'movie', 0, 'Man of Steel',
                                     'man.of.steel.2013.720p.bluray.x264-felony', 2013, 770828, 0, 0,
                                     'man.of.steel.2013.720p.bluray.x264-felony.srt', None)
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


def test_configuration_error_no_username():
    with pytest.raises(ConfigurationError):
        OpenSubtitlesProvider(password='subliminal')


def test_configuration_error_no_password():
    with pytest.raises(ConfigurationError):
        OpenSubtitlesProvider(username='subliminal')


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = OpenSubtitlesProvider('python-subliminal', 'subliminal')
    assert provider.token is None
    provider.initialize()
    assert provider.token is not None


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = OpenSubtitlesProvider('python-subliminal', 'lanimilbus')
    with pytest.raises(Unauthorized):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = OpenSubtitlesProvider('python-subliminal', 'subliminal')
    provider.initialize()
    provider.terminate()
    assert provider.token is None


@pytest.mark.integration
@vcr.use_cassette
def test_no_operation():
    with OpenSubtitlesProvider() as provider:
        provider.no_operation()


@pytest.mark.integration
@vcr.use_cassette
def test_query_not_enough_information():
    languages = {Language('eng')}
    with OpenSubtitlesProvider() as provider:
        with pytest.raises(ValueError) as excinfo:
            provider.query(languages)
    assert str(excinfo.value) == 'Not enough information'


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('fra')}
    expected_subtitles = {'1953767244', '1953770526', '1953150292', '1953647841', '1953767650', '1955181172'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, query=video.title)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_episode(episodes):
    video = episodes['dallas_2012_s01e03']
    languages = {Language('fra')}
    expected_subtitles = {'1953147577'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_tag_movie(movies):
    video = movies['enders_game']
    languages = {Language('fra')}
    expected_subtitles = {'1954121830'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, tag=video.name)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_imdb_id(movies):
    video = movies['man_of_steel']
    languages = {Language('deu')}
    expected_subtitles = {'1953771409', '1953768982'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, imdb_id=video.imdb_id)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_hash_size(movies):
    video = movies['man_of_steel']
    languages = {Language('eng')}
    expected_subtitles = {'1953767678', '1953800590', '1953766751', '1953621994', '1953766883', '1953767330',
                          '1953766488', '1953766413', '1953766280', '1953767141', '1953766279', '1953785668',
                          '1953767218'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, hash=video.hashes['opensubtitles'], size=video.size)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_hash_wrong_size():
    languages = {Language('eng')}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, hash='123456787654321', size=99999)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_season_episode(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('deu')}
    expected_subtitles = {'1953771908'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {'1953767244', '1953647841', '1953767650', '1953771409', '1953768982', '1953770526',
                          '1953608995', '1953608996', '1953150292', '1953600788', '1954879110', '1955181172'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_no_hash(movies):
    video = movies['enders_game']
    languages = {Language('deu')}
    expected_subtitles = {'1954157398', '1954156756', '1954443141'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['marvels_agents_of_shield_s02e06']
    languages = {Language('hun')}
    expected_subtitles = {'1954464403', '1954454544'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
    assert subtitles[0].encoding == 'cp1252'


@pytest.mark.integration
@vcr.use_cassette
def test_tag_match(episodes):
    video = episodes['the fall']
    languages = {Language('por', 'BR')}
    unwanted_subtitle_id = '1954369181'  # 'Doc.Martin.S03E01.(24 September 2007).[TVRip (Xvid)]-spa.srt'
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        found_subtitle = [s for s in subtitles if s.id == unwanted_subtitle_id and s.matched_by == 'tag'][0]
        matches = found_subtitle.get_matches(video)
    assert len(subtitles) > 0
    assert unwanted_subtitle_id in {subtitle.id for subtitle in subtitles}
    # Assert is not a tag match: {'series', 'year', 'season', 'episode'}
    assert matches == {'episode', 'year', 'season'}
