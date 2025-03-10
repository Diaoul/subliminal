import os

import pytest
from babelfish import Language, language_converters  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.exceptions import ConfigurationError
from subliminal.providers.opensubtitles import (
    OpenSubtitlesProvider,
    OpenSubtitlesSubtitle,
    OpenSubtitlesVipProvider,
    Unauthorized,
)
from subliminal.video import Episode, Movie

USERNAME = 'python-subliminal'
PASSWORD = 'subliminal'

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'opensubtitles')),
)


@pytest.mark.converter
def test_converter_convert_alpha3_country_script() -> None:
    assert language_converters['opensubtitles'].convert('zho', None, 'Hant') == 'zht'


@pytest.mark.converter
def test_converter_convert_alpha3_country() -> None:
    assert language_converters['opensubtitles'].convert('por', 'BR') == 'pob'


def test_get_matches_movie_hash(movies: dict[str, Movie]) -> None:
    subtitle = OpenSubtitlesSubtitle(
        language=Language('deu'),
        subtitle_id='1953771409',
        hearing_impaired=False,
        page_link=None,
        matched_by='moviehash',
        movie_kind='movie',
        moviehash='5b8f8f4e41ccb21e',
        movie_name='Man of Steel',
        movie_release_name='Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE',
        movie_year=2013,
        movie_imdb_id='tt0770828',
        series_season=0,
        series_episode=0,
        filename='Man.of.Steel.German.720p.BluRay.x264-EXQUiSiTE.srt',
        encoding=None,
    )
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'country', 'video_codec', 'imdb_id', 'hash', 'resolution', 'source'}


def test_get_matches_episode(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesSubtitle(
        language=Language('ell'),
        subtitle_id='1953579014',
        hearing_impaired=False,
        page_link=None,
        matched_by='fulltext',
        movie_kind='episode',
        moviehash='0',
        movie_name='"Game of Thrones" Mhysa',
        movie_release_name=' Game.of.Thrones.S03E10.HDTV.XviD-AFG',
        movie_year=2013,
        movie_imdb_id='tt2178796',
        series_season=3,
        series_episode=10,
        filename='Game.of.Thrones.S03E10.HDTV.XviD-AFG.srt',
        encoding=None,
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'imdb_id', 'series', 'year', 'country', 'episode', 'season', 'title'}


def test_get_matches_episode_year(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesSubtitle(
        language=Language('spa'),
        subtitle_id='1953369959',
        hearing_impaired=False,
        page_link=None,
        matched_by='tag',
        movie_kind='episode',
        moviehash='0',
        movie_name='"Dallas" The Price You Pay',
        movie_release_name=' Dallas.2012.S01E03.HDTV.x264-LOL',
        movie_year=2012,
        movie_imdb_id='tt2205526',
        series_season=1,
        series_episode=3,
        filename='Dallas.2012.S01E03.HDTV.x264-LOL.srt',
        encoding='cp1252',
    )
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == {'imdb_id', 'series', 'year', 'episode', 'season', 'title'}


def test_get_matches_episode_filename(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesSubtitle(
        language=Language('por', country='BR'),
        subtitle_id='1954453973',
        hearing_impaired=False,
        page_link=None,
        matched_by='fulltext',
        movie_kind='episode',
        moviehash='0',
        movie_name='"Agents of S.H.I.E.L.D." A Fractured House',
        movie_release_name='HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS',
        movie_year=2014,
        movie_imdb_id='tt4078580',
        series_season=2,
        series_episode=6,
        filename='Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.srt',
        encoding='cp1252',
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
    subtitle = OpenSubtitlesSubtitle(
        language=Language('por', country='BR'),
        subtitle_id='1954453973',
        hearing_impaired=False,
        page_link=None,
        matched_by='tag',
        movie_kind='episode',
        moviehash='0',
        movie_name='"Agents of S.H.I.E.L.D." A Fractured House',
        movie_release_name='HDTV.x264-KILLERS-mSD-AFG-EVO-KILLERS',
        movie_year=2014,
        movie_imdb_id='tt4078580',
        series_season=2,
        series_episode=6,
        filename='',
        encoding='cp1252',
    )
    matches = subtitle.get_matches(episodes['marvels_agents_of_shield_s02e06'])
    assert matches == {'series', 'year', 'country', 'season', 'episode', 'source', 'video_codec'}


def test_get_matches_imdb_id(movies: dict[str, Movie]) -> None:
    subtitle = OpenSubtitlesSubtitle(
        language=Language('fra'),
        subtitle_id='1953767650',
        hearing_impaired=True,
        page_link=None,
        matched_by='imdbid',
        movie_kind='movie',
        moviehash=None,
        movie_name='Man of Steel',
        movie_release_name='man.of.steel.2013.720p.bluray.x264-felony',
        movie_year=2013,
        movie_imdb_id='tt0770828',
        series_season=0,
        series_episode=0,
        filename='man.of.steel.2013.720p.bluray.x264-felony.srt',
        encoding=None,
    )
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'country', 'video_codec', 'imdb_id', 'resolution', 'source', 'release_group'}


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle = OpenSubtitlesSubtitle(
        language=Language('fra'),
        subtitle_id='1953767650',
        hearing_impaired=False,
        page_link=None,
        matched_by='imdbid',
        movie_kind='movie',
        moviehash=0,  # type: ignore[arg-type]
        movie_name='Man of Steel',
        movie_release_name='man.of.steel.2013.720p.bluray.x264-felony',
        movie_year=2013,
        movie_imdb_id=770828,  # type: ignore[arg-type]
        series_season=0,
        series_episode=0,
        filename='man.of.steel.2013.720p.bluray.x264-felony.srt',
        encoding=None,
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == set()


def test_configuration_error_no_username() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesProvider(password=PASSWORD)


def test_configuration_error_no_password() -> None:
    with pytest.raises(ConfigurationError):
        OpenSubtitlesProvider(username=USERNAME)


@pytest.mark.skip('authorization no longer works on the old API')
@pytest.mark.integration
@vcr.use_cassette
def test_login() -> None:
    provider = OpenSubtitlesProvider(USERNAME, PASSWORD)
    assert provider.token is None
    provider.initialize()
    assert provider.token is not None


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password() -> None:
    provider = OpenSubtitlesProvider(USERNAME, 'lanimilbus')
    with pytest.raises(Unauthorized):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_login_vip_login() -> None:
    provider = OpenSubtitlesVipProvider(USERNAME, PASSWORD)
    with pytest.raises(Unauthorized):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_login_vip_bad_password() -> None:
    provider = OpenSubtitlesVipProvider(USERNAME, 'lanimilbus')
    with pytest.raises(Unauthorized):
        provider.initialize()


@pytest.mark.skip('authorization no longer works on the old API')
@pytest.mark.integration
@vcr.use_cassette
def test_logout() -> None:
    provider = OpenSubtitlesProvider(USERNAME, PASSWORD)
    provider.initialize()
    provider.terminate()
    assert provider.token is None


@pytest.mark.integration
@vcr.use_cassette
def test_no_operation() -> None:
    with OpenSubtitlesProvider() as provider:
        provider.no_operation()


@pytest.mark.integration
@vcr.use_cassette
def test_query_not_enough_information() -> None:
    languages = {Language('eng')}
    with OpenSubtitlesProvider() as provider:  # noqa: SIM117
        with pytest.raises(ValueError) as excinfo:  # noqa: PT011
            provider.query(languages)
    assert str(excinfo.value) == 'Not enough information'


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('fra')}
    expected_subtitles = {
        '1953150292',
        '1953647841',
        '1953767244',
        '1953767650',
        '1953770526',
        '1955250359',
        '1955252613',
        '1955260179',
        '1955260793',
        '1956104848',
    }
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, query=video.title)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_2012_s01e03']
    languages = {Language('fra')}
    expected_subtitles = {'1953147577'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.skip('query by tag currently broken on opensubtitles')
@pytest.mark.integration
@vcr.use_cassette
def test_query_tag_movie(movies: dict[str, Movie]) -> None:
    video = movies['interstellar']
    languages = {Language('fra')}
    expected_subtitles = {'1954121830'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, tag=video.name)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_imdb_id(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu')}
    expected_subtitles = {
        '1953768982',
        '1953771409',
        '1955278518',
        '1955279635',
        '1955742626',
        '1956717408',
        '1957720375',
    }
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, imdb_id=video.imdb_id)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_hash_size(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}
    expected_subtitles = {
        '1953621994',
        '1953766279',
        '1953766280',
        '1953766413',
        '1953766751',
        '1953766883',
        '1953767141',
        '1953767218',
        '1953767330',
        '1953767678',
        '1953785668',
    }
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, moviehash=video.hashes['opensubtitles'], size=video.size)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_hash_wrong_size() -> None:
    languages = {Language('eng')}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, moviehash='123456787654321', size=99999)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_query_season_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('deu')}
    expected_subtitles = {'1953771908', '1956168972'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.query(languages, query=video.series, season=video.season, episode=video.episode)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {
        '1953150292',
        '1953600788',
        '1953608995',
        '1953608996',
        '1953647841',
        '1953767244',
        '1953767650',
        '1953768982',
        '1953770526',
        '1953771409',
        '1954879110',
        '1955250359',
        '1955252613',
        '1955260179',
        '1955260793',
        '1955268745',
        '1955278518',
        '1955279635',
        '1955280869',
        '1955280874',
        '1955742626',
        '1955752850',
        '1955752852',
        '1955933986',
        '1956104848',
        '1956113223',
        '1956683278',
        '1956683279',
        '1956717408',
        '1956717410',
        '1958112113',
        '1957400516',
        '1957720375',
        '1957200647',
    }
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_no_hash(movies: dict[str, Movie]) -> None:
    video = movies['enders_game']
    languages = {Language('deu')}
    expected_subtitles = {'1954157398', '1954156756', '1954443141'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    languages = {Language('hun')}
    expected_subtitles = {'1954464403', '1955344515', '1954454544'}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('deu'), Language('fra')}
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
    assert subtitles[0].encoding == 'cp1252'


@pytest.mark.skip('query by tag currently broken on opensubtitles')
@pytest.mark.integration
@vcr.use_cassette
def test_tag_match(episodes: dict[str, Episode]) -> None:
    video = episodes['the fall']
    languages = {Language('por', 'BR')}
    unwanted_subtitle_id = '1954369181'  # 'Doc.Martin.S03E01.(24 September 2007).[TVRip (Xvid)]-spa.srt'
    with OpenSubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)

    matched_subtitles = [s for s in subtitles if s.id == unwanted_subtitle_id and s.matched_by == 'tag']
    assert len(matched_subtitles) == 1
    found_subtitle = matched_subtitles[0]
    matches = found_subtitle.get_matches(video)
    assert len(subtitles) > 0
    assert unwanted_subtitle_id in {subtitle.id for subtitle in subtitles}
    # Assert is not a tag match: {'series', 'year', 'season', 'episode'}
    assert matches == {'episode', 'year', 'country', 'season'}
