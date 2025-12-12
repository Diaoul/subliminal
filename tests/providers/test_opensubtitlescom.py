import os

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.exceptions import ConfigurationError
from subliminal.providers.opensubtitlescom import (
    OpenSubtitlesComError,
    OpenSubtitlesComProvider,
    OpenSubtitlesComSubtitle,
    Unauthorized,
)
from subliminal.video import Episode, Movie

USERNAME = 'python-subliminal-test'
PASSWORD = 'subliminal'

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'opensubtitlescom')),
)


def test_get_matches_movie_hash(movies: dict[str, Movie]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('deu'),
        subtitle_id='1953771409',
        hearing_impaired=False,
        movie_kind='movie',
        movie_title='Man of Steel',
        release='Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE',
        movie_year=2013,
        movie_imdb_id='tt0770828',
        series_season=0,
        series_episode=0,
        moviehash_match=True,
        file_name='Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE.srt',
    )
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {
        'title',
        'year',
        'country',
        'video_codec',
        'resolution',
        'source',
        'hash',
    }


def test_get_matches_episode(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('ell'),
        subtitle_id='1953579014',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='Mhysa',
        release=' Game.of.Thrones.S03E10.HDTV.XviD-AFG',
        movie_year=2013,
        movie_imdb_id='tt2178796',
        series_title='Game of Thrones',
        series_season=3,
        series_episode=10,
        file_name='Game.of.Thrones.S03E10.HDTV.XviD-AFG.srt',
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {
        'series',
        'year',
        'country',
        'episode',
        'season',
        'title',
    }


def test_get_matches_episode_year(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('spa'),
        subtitle_id='1953369959',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='The Price You Pay',
        release=' Dallas.2012.S01E03.HDTV.x264-LOL',
        movie_year=2012,
        movie_imdb_id='tt2205526',
        series_title='Dallas',
        series_season=1,
        series_episode=3,
        file_name='Dallas.2012.S01E03.HDTV.x264-LOL.srt',
    )
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == {'series', 'year', 'episode', 'season', 'title'}


def test_get_matches_episode_filename(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('por', country='BR'),
        subtitle_id='1954453973',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='A Fractured House',
        release='HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS',
        movie_year=2014,
        movie_imdb_id='tt4078580',
        series_title='Agents of S.H.I.E.L.D.',
        series_season=2,
        series_episode=6,
        file_name='Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.srt',
    )
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {
        'series',
        'year',
        'country',
        'season',
        'episode',
        'release_group',
        'source',
        'resolution',
        'video_codec',
    }


def test_get_matches_episode_tag(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('por', country='BR'),
        subtitle_id='1954453973',
        hearing_impaired=False,
        movie_kind='episode',
        movie_title='A Fractured House',
        release='HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS',
        movie_year=2014,
        movie_imdb_id='tt4078580',
        series_title='Agents of S.H.I.E.L.D.',
        series_season=2,
        series_episode=6,
        file_name='',
    )
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {
        'year',
        'country',
        'season',
        'episode',
        'source',
        'video_codec',
    }


def test_get_matches_imdb_id(movies: dict[str, Movie]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('fra'),
        subtitle_id='1953767650',
        hearing_impaired=True,
        movie_kind='movie',
        movie_title='Man of Steel',
        release='man.of.steel.2013.720p.bluray.x264-felony',
        movie_year=2013,
        movie_imdb_id='tt0770828',
        imdb_match=True,
        series_season=0,
        series_episode=0,
        file_name='man.of.steel.2013.720p.bluray.x264-felony.srt',
    )
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {
        'title',
        'year',
        'country',
        'video_codec',
        'imdb_id',
        'resolution',
        'source',
        'release_group',
    }


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesComSubtitle(
        language=Language('fra'),
        subtitle_id='1953767650',
        hearing_impaired=False,
        movie_kind='movie',
        movie_title='Man of Steel',
        release='man.of.steel.2013.720p.bluray.x264-felony',
        movie_year=2013,
        movie_imdb_id=770828,  # type: ignore[arg-type]
        series_season=0,
        series_episode=0,
        file_name='man.of.steel.2013.720p.bluray.x264-felony.srt',
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


def test_configuration_error_no_username() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesComProvider(password=PASSWORD)


def test_configuration_error_no_password() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesComProvider(username=USERNAME)


@pytest.mark.integration
@vcr.use_cassette
def test_login() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    assert provider.token is None
    provider.initialize()
    provider.login(wait=True)
    assert provider.token is not None


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, 'lanimilbus')
    with pytest.raises(Unauthorized):  # noqa: PT012
        provider.initialize()
        provider.login(wait=True)


@pytest.mark.integration
@vcr.use_cassette
def test_logout() -> None:
    provider = OpenSubtitlesComProvider(USERNAME, PASSWORD)
    provider.initialize()
    provider.login(wait=True)
    provider.terminate()
    assert provider.token is None


@pytest.mark.integration
@vcr.use_cassette
def test_user_infos() -> None:
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        provider.login(wait=True)
        ret = provider.user_infos()
        assert ret


@pytest.mark.integration
@vcr.use_cassette
def test_query_not_enough_information() -> None:
    languages = {Language('eng')}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:  # noqa: SIM117
        with pytest.raises(ValueError) as excinfo:  # noqa: PT011
            provider.query(languages)
    assert str(excinfo.value) == 'Not enough information'


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('fra')}
    expected_subtitles = {
        '870964',
        '877697',
        '879122',
        '880511',
        '1546744',
        '4614499',
    }
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(languages, query=video.title)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_2012_s01e03']
    languages = {Language('fra')}
    expected_subtitles = {
        '3359298',
        '3359569',
        '3829531',
        '6915085',
    }
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_tag_movie(movies: dict[str, Movie]) -> None:
    video = movies['enders_game']
    languages = {Language('fra')}
    expected_subtitles = {'938965', '940630'}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(languages, query=video.name)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_imdb_id(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu')}
    expected_subtitles = {
        '880332',
        '880717',
        '883552',
        '883560',
        '5166256',
        '6632511',
    }
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(languages, imdb_id=video.imdb_id)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_hash_size(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}
    expected_subtitles = {
        '869742',
        '871951',
        '872093',
        '873226',
        '874537',
        '876180',
        '876365',
        '877376',
        '877471',
        '879204',
        '882182',
        '3178800',
    }
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(languages, moviehash=video.hashes['opensubtitles'])
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_hash_wrong_size() -> None:
    languages = {Language('eng')}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:  # noqa: SIM117
        with pytest.raises(OpenSubtitlesComError):
            provider.query(languages, moviehash='123456787654321')


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_season_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('deu')}
    expected_subtitles = {'2748964', '4662161'}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {
        '883560',
        '880332',
        '883552',
        '6632511',
        '5166256',
        '879122',
        '880717',
        '870964',
        '880511',
        '877697',
        '4614499',
        '1546744',
        '2627058',
        '4620011',
        '7164656',
        '6556241',
        '823209',
        '2627042',
    }
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_no_hash(movies: dict[str, Movie]) -> None:
    video = movies['enders_game']
    languages = {Language('deu')}
    expected_subtitles = {'939532', '939553', '940426'}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    languages = {Language('hun')}
    expected_subtitles = {'2491535', '2492310', '2493688'}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
    assert subtitles[0].encoding == 'utf-8'


@pytest.mark.integration
@vcr.use_cassette
def test_tag_match(episodes: dict[str, Episode]) -> None:
    video = episodes['the fall']
    languages = {Language('por', 'BR')}
    with OpenSubtitlesComProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)

    assert len(subtitles) > 0

    # 'Doc.Martin.S03E01.(24 September 2007).[TVRip (Xvid)]-spa.srt'
    unwanted_subtitle_id = '2852678'
    found_subtitles = [s for s in subtitles if s.subtitle_id == unwanted_subtitle_id]
    assert len(found_subtitles) > 0

    found_subtitle = found_subtitles[0]
    matches = found_subtitle.get_matches(video)
    # Assert is not a tag match: {'series', 'year', 'season', 'episode'}
    assert matches == {'episode', 'year', 'country', 'season'}


@pytest.mark.integration
@vcr.use_cassette
def test_query_max_result_pages(movies: dict[str, Movie]) -> None:
    # choose a movie with a lot of results
    query = 'James Bond'
    languages = {Language('eng')}

    with OpenSubtitlesComProvider(USERNAME, PASSWORD, max_result_pages=0) as provider:
        all_subtitles = provider.query(languages, query=query)

    with OpenSubtitlesComProvider(USERNAME, PASSWORD, max_result_pages=1) as provider:
        subtitles = provider.query(languages, query=query)
    assert len(subtitles) < len(all_subtitles)
