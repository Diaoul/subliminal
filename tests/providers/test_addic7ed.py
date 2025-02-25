import os

import pytest
from babelfish import Language, language_converters  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.exceptions import AuthenticationError, ConfigurationError
from subliminal.providers.addic7ed import Addic7edProvider, Addic7edSubtitle, addic7ed_sanitize, series_year_re
from subliminal.video import Episode

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'addic7ed')),
)

USERNAME = 'subliminal'
PASSWORD = 'subliminal'


@pytest.mark.converter
def test_converter_convert_alpha3_country_script() -> None:
    assert language_converters['addic7ed'].convert('srp', None, 'Cyrl') == 'Serbian (Cyrillic)'


@pytest.mark.converter
def test_converter_convert_alpha3_country() -> None:
    assert language_converters['addic7ed'].convert('por', 'BR') == 'Portuguese (Brazilian)'


@pytest.mark.converter
def test_converter_convert_alpha3() -> None:
    assert language_converters['addic7ed'].convert('eus') == 'Euskera'


@pytest.mark.converter
def test_converter_convert_alpha3_name_converter() -> None:
    assert language_converters['addic7ed'].convert('fra') == 'French'


@pytest.mark.converter
def test_converter_reverse() -> None:
    assert language_converters['addic7ed'].reverse('Chinese (Traditional)') == ('zho', None, None)


@pytest.mark.converter
def test_converter_reverse_name_converter() -> None:
    assert language_converters['addic7ed'].reverse('English') == ('eng', None, None)


def test_series_year_re() -> None:
    match = series_year_re.match("That's: A-series.name!? (US) (2016)")
    assert match
    assert match.group('series') == "That's: A-series.name!? (US)"
    assert int(match.group('year')) == 2016


def test_get_matches_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = Addic7edSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        year=2007,
        release_group='DIMENSION',
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group'}


def test_get_matches_equivalent_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = Addic7edSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        year=2007,
        release_group='LOL',
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group'}


def test_get_matches_resolution_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = Addic7edSubtitle(
        language=Language('heb'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        year=2007,
        release_group='720PDIMENSION',
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'resolution'}


def test_get_matches_source_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = Addic7edSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='Game of Thrones',
        season=3,
        episode=10,
        title='Mhysa',
        year=None,
        release_group='WEB-DL-NTb',
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'source'}


def test_get_matches_streaming_service(episodes: dict[str, Episode]) -> None:
    subtitle = Addic7edSubtitle(
        language=Language('nld'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Walking Dead',
        season=8,
        episode=7,
        title=None,
        year=None,
        release_group='AMZN.WEB-DL-CasStudio',
    )
    matches = subtitle.get_matches(episodes['walking_dead_s08e07'])
    assert matches == {'series', 'season', 'episode', 'year', 'country', 'release_group', 'streaming_service', 'source'}


def test_get_matches_only_year_country(episodes: dict[str, Episode]) -> None:
    subtitle = Addic7edSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        year=None,
        release_group='DIMENSION',
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'year', 'country'}


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle = Addic7edSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        year=2007,
        release_group='DIMENSION',
    )
    matches = subtitle.get_matches(episodes['house_of_cards_us_s06e01'])
    assert matches == set()


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('The Big Bang Theory', 'the big bang theory'),
        ("Marvel's Agents of S.H.I.E.L.D.", 'marvel s agents of s h i e l d'),
        ('11.22.63', '11 22 63'),
        ('Alex, Inc.', 'alex inc'),
        ('CSI: Cyber', 'csi cyber'),
        ('Älska mig', 'alska mig'),
    ],
)
def test_sanitize(text: str, expected: str) -> None:
    sanitized = addic7ed_sanitize(text)
    assert sanitized == expected


def test_configuration_error_no_username() -> None:
    with pytest.raises(ConfigurationError):
        Addic7edProvider(password=PASSWORD)


def test_configuration_error_no_password() -> None:
    with pytest.raises(ConfigurationError):
        Addic7edProvider(username=USERNAME)


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_login() -> None:
    provider = Addic7edProvider(USERNAME, PASSWORD)
    assert provider.logged_in is False
    provider.initialize()
    assert provider.logged_in is True
    assert provider.session is not None
    r = provider.session.get(provider.server_url + '/panel.php', allow_redirects=False, timeout=10)
    assert r.status_code == 302


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password() -> None:
    provider = Addic7edProvider(USERNAME, 'lanimilbus')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_logout() -> None:
    provider = Addic7edProvider(USERNAME, PASSWORD)
    provider.initialize()
    provider.terminate()
    assert provider.logged_in is False
    assert provider.session is not None
    r = provider.session.get(provider.server_url + '/panel.php', allow_redirects=False, timeout=10)
    assert r.status_code == 302


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids() -> None:
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'the big bang theory' in show_ids
    assert show_ids['the big bang theory'] == 126


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_no_year() -> None:
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'dallas' in show_ids
    assert show_ids['dallas'] == 802


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_year() -> None:
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'dallas 2012' in show_ids
    assert show_ids['dallas 2012'] == 2559


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_dot() -> None:
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'mr robot' in show_ids
    assert show_ids['mr robot'] == 5151


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_country() -> None:
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'being human us' in show_ids
    assert show_ids['being human us'] == 1317


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_quote() -> None:
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    assert 'marvel s agents of s h i e l d' in show_ids
    assert show_ids['marvel s agents of s h i e l d'] == 4010


@pytest.mark.integration
@vcr.use_cassette('test_get_show_ids')
def test_get_show_ids_unicode() -> None:
    with Addic7edProvider() as provider:
        show_ids = provider._get_show_ids()
    # "Älska_mig"
    assert 'alska mig' in show_ids
    assert show_ids['alska mig'] == 7816


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id() -> None:
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('The Big Bang Theory')
    assert show_id == 126


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_incomplete() -> None:
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('The Big Bang')
    assert show_id == 126


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_no_year() -> None:
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('Dallas')
    assert show_id == 802


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_year() -> None:
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('Dallas 2012')
    assert show_id == 2559


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_error() -> None:
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id('The Big How I Met Your Mother')
    assert show_id is None


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_quote() -> None:
    with Addic7edProvider() as provider:
        show_id = provider._search_show_id("Grey's Anatomy")
    assert show_id == 30


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_ids_quote_dots_mixed_case(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    with Addic7edProvider() as provider:
        series = addic7ed_sanitize(video.series)
        show_ids = provider._search_show_ids(series)
    expected = {'marvel s agents of s h i e l d': 4010, 'marvel s agents of s h i e l d slingshot': 6144}
    assert show_ids == expected


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_ids_with_comma(episodes: dict[str, Episode]) -> None:
    video = episodes['alex_inc_s01e04']
    with Addic7edProvider() as provider:
        series = addic7ed_sanitize(video.series)
        show_ids = provider._search_show_ids(series)
    expected = {'alex inc': 6388}
    assert show_ids == expected


@pytest.mark.skip
@pytest.mark.integration
@vcr.use_cassette
def test_search_show_ids_with_country(episodes: dict[str, Episode]) -> None:
    with Addic7edProvider() as provider:
        series = addic7ed_sanitize('Being Human')
        show_ids = provider._search_show_ids(series)
    expected = {'being human': 311, 'being human us': 1317, 'being human the annie broadcasts': 1325}
    assert show_ids == expected


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_quote_dots_mixed_case(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series)
    assert show_id == 4010


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_with_comma(episodes: dict[str, Episode]) -> None:
    video = episodes['alex_inc_s01e04']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series)
    assert show_id == 6388


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_country() -> None:
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id('Being Human', country_code='US')
    assert show_id == 1317


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id_year() -> None:
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id('Dallas', year=2012)
    assert show_id == 2559


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_id() -> None:
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id('Dallas')
    assert show_id == 802


@pytest.mark.integration
@vcr.use_cassette
def test_query(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season)
    assert len(subtitles) == 474
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.year is None


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    with Addic7edProvider() as provider:
        subtitles = provider.query(0, series=video.series[:12], season=video.season, year=video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing(episodes: dict[str, Episode]) -> None:
    video = episodes['got_s03e10']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season)
    assert len(subtitles) > 0

    matched_id = 'updated/1/76311/1'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1

    subtitle = matched_subtitles[0]
    assert subtitle.language == Language('eng')
    assert subtitle.hearing_impaired is True
    assert subtitle.page_link == 'https://www.addic7ed.com/serie/Game_of_Thrones/3/10/Mhysa'
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.title == video.title
    assert subtitle.year == video.year
    assert subtitle.release_group == 'EVOLVE'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_quote_dots_mixed_case(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    show_id = 4010
    with Addic7edProvider() as provider:
        subtitles = provider.query(show_id, video.series, video.season)

    matched_id = 'updated/10/93279/9'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1

    subtitle = matched_subtitles[0]
    assert subtitle.language == Language('por', country='BR')
    assert subtitle.hearing_impaired is False
    assert (
        subtitle.page_link == 'https://www.addic7ed.com/serie/Marvel%27s_Agents_of_S.H.I.E.L.D./2/6/A_Fractured_House'
    )
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.release_group == 'KILLERS'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_colon(episodes: dict[str, Episode]) -> None:
    video = episodes['csi_cyber_s02e03']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season)
    assert show_id == 4633

    matched_id = 'updated/1/105111/2'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1

    subtitle = matched_subtitles[0]
    assert subtitle.language == Language('eng')
    assert subtitle.hearing_impaired is False
    assert subtitle.page_link == 'https://www.addic7ed.com/serie/CSI%3A_Cyber/2/3/Brown_Eyes%2C_Blue_Eyes'
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.release_group == 'DIMENSION'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_dash(episodes: dict[str, Episode]) -> None:
    video = episodes['the_x_files_s10e02']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season)

    matched_id = 'updated/8/108202/21'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1

    subtitle = matched_subtitles[0]
    assert subtitle.language == Language('fra')
    assert subtitle.hearing_impaired is False
    assert subtitle.page_link == 'https://www.addic7ed.com/serie/The_X-Files/10/2/Founder%27s_Mutation'
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.release_group == 'KILLERS'


@pytest.mark.integration
@vcr.use_cassette
def test_query_year(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_2012_s01e03']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series, video.year)
        subtitles = provider.query(show_id, series=video.series, season=video.season, year=video.year)
    assert len(subtitles) == 123
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.year == video.year


@pytest.mark.integration
@vcr.use_cassette
def test_query_no_year(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_s01e03']
    with Addic7edProvider() as provider:
        show_id = provider.get_show_id(video.series)
        assert show_id is not None
        subtitles = provider.query(show_id, video.series, video.season)
    assert len(subtitles) == 7
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.year is None


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {'updated/8/80254/1', 'updated/11/80254/5'}
    with Addic7edProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    with Addic7edProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_alternative_series(episodes: dict[str, Episode]) -> None:
    video = episodes['turn_s04e03']
    languages = {Language('eng')}
    expected_subtitles = {'updated/1/125243/0', 'updated/1/125243/1'}
    with Addic7edProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        matches = subtitles[0].get_matches(episodes['turn_s04e03'])
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
    assert matches == {'episode', 'title', 'series', 'season', 'year', 'country', 'release_group'}


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_show_with_asterisk(episodes: dict[str, Episode]) -> None:
    video = episodes['the_end_of_the_fucking_world']
    languages = {Language('eng')}
    names = {'The End of the Fucking World'}
    expected_subtitles = {'updated/1/129156/1', 'updated/1/129156/0', 'updated/1/129156/2'}
    with Addic7edProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        matches = subtitles[0].get_matches(episodes['the_end_of_the_fucking_world'])
    assert {subtitle.series for subtitle in subtitles} == names
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
    assert matches == {'year', 'country', 'series', 'episode', 'season'}
