import os

import pytest
from babelfish import Language, language_converters  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.providers.gestdown import GestdownProvider, GestdownSubtitle
from subliminal.video import Episode

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'gestdown')),
)


@pytest.mark.converter
def test_converter_convert_alpha3_country() -> None:
    assert language_converters['addic7ed'].convert('por', 'BR') == 'Portuguese (Brazilian)'


def test_get_matches_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = GestdownSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        release_group='DIMENSION',
        page_link=None,
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group'}


def test_get_matches_equivalent_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = GestdownSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        release_group='LOL',
        page_link=None,
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group'}


def test_get_matches_resolution_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = GestdownSubtitle(
        language=Language('heb'),
        subtitle_id='',
        hearing_impaired=True,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        release_group='720PDIMENSION',
        page_link=None,
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'resolution'}


def test_get_matches_source_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = GestdownSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        series='Game of Thrones',
        season=3,
        episode=10,
        title='Mhysa',
        release_group='WEB-DL-NTb',
        page_link=None,
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'season', 'episode', 'title', 'year', 'country', 'release_group', 'source'}


def test_get_matches_streaming_service(episodes: dict[str, Episode]) -> None:
    subtitle = GestdownSubtitle(
        language=Language('nld'),
        subtitle_id='',
        hearing_impaired=True,
        series='The Walking Dead',
        season=8,
        episode=7,
        title=None,
        release_group='AMZN.WEB-DL-CasStudio',
        page_link=None,
    )
    matches = subtitle.get_matches(episodes['walking_dead_s08e07'])
    assert matches == {'series', 'season', 'episode', 'year', 'country', 'release_group', 'streaming_service', 'source'}


def test_get_matches_only_year_country(episodes: dict[str, Episode]) -> None:
    subtitle = GestdownSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        release_group='DIMENSION',
        page_link=None,
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'year', 'country'}


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle = GestdownSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        title='The Workplace Proximity',
        release_group='DIMENSION',
        page_link=None,
    )
    matches = subtitle.get_matches(episodes['house_of_cards_us_s06e01'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id() -> None:
    with GestdownProvider() as provider:
        show_id = provider._search_show_id('The Big Bang Theory')
    assert show_id == '91eb9278-8cf5-4ddd-9111-7f60b15958cb'


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_incomplete() -> None:
    with GestdownProvider() as provider:
        show_id = provider._search_show_id('The Big Bang')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_no_year() -> None:
    with GestdownProvider() as provider:
        show_id = provider._search_show_id('Dallas')
    assert show_id == '226d7f34-a9f5-4fe2-98d7-ecf944243714'


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_error() -> None:
    with GestdownProvider() as provider:
        show_id = provider._search_show_id('The Big How I Met Your Mother')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_quote() -> None:
    with GestdownProvider() as provider:
        show_id = provider._search_show_id("Grey's Anatomy")
    assert show_id == 'cb13bb68-c637-4e0f-b79d-d4f1b4972380'


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_series_tvdb_id() -> None:
    with GestdownProvider() as provider:
        # The Big Bang Theory
        show_id = provider._search_show_id('', series_tvdb_id='80379')
    assert show_id == '91eb9278-8cf5-4ddd-9111-7f60b15958cb'


@pytest.mark.integration
@vcr.use_cassette
def test_get_title_and_show_id_only_title(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
    assert title == "Marvel's Agents of S.H.I.E.L.D."
    assert show_id == '8976d3bb-a213-4210-9a03-f4b6d17ce540'


@pytest.mark.integration
@vcr.use_cassette
def test_get_title_and_show_id_with_tvdb_id(episodes: dict[str, Episode]) -> None:
    video = episodes['alex_inc_s01e04']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
    assert title == 'Alex, Inc.'
    assert show_id == '6e507429-0994-443f-833e-1b06cbc18705'


@pytest.mark.integration
@vcr.use_cassette
def test_get_title_and_show_id_alternative_name(episodes: dict[str, Episode]) -> None:
    video = episodes['the_end_of_the_fucking_world']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
    assert title == 'The end of the f***ing world'
    assert show_id == 'e789f371-ae07-4db4-b9aa-6b34e7e9e7b0'


@pytest.mark.integration
@vcr.use_cassette
def test_get_title_and_show_id_no_year(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_s01e03']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
    assert title == 'Dallas'
    assert show_id == '226d7f34-a9f5-4fe2-98d7-ecf944243714'


@pytest.mark.integration
@vcr.use_cassette
def test_query(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
        subtitles = provider.query(show_id, title, video.season, video.episode, Language('eng'))
    assert len(subtitles) == 5
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
        assert subtitle.episode == video.episode


@pytest.mark.integration
@vcr.use_cassette
def test_query_no_language(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
        subtitles = provider.query(show_id, title, video.season, video.episode, None)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    with GestdownProvider() as provider:
        subtitles = provider.query('', video.series[:12], video.season, video.episode, Language('eng'))
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing(episodes: dict[str, Episode]) -> None:
    lang = Language('por', country='BR')
    video = episodes['got_s03e10']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
        subtitles = provider.query(show_id, title, video.season, video.episode, lang)

    matched_id = '9f486fef-ce86-4918-a292-dacd5dda07c8'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1

    subtitle = matched_subtitles[0]
    assert subtitle.language == lang
    assert subtitle.hearing_impaired is False
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.title == video.title
    assert subtitle.release_group == 'All_with_preview'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_quote_dots_mixed_case(episodes: dict[str, Episode]) -> None:
    lang = Language('eng')
    video = episodes['marvels_agents_of_shield_s02e06']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
        subtitles = provider.query(show_id, title, video.season, video.episode, lang)

    matched_id = '2dea1511-0b72-40db-89b5-eb6f0fb218a5'
    matched_subtitles = [s for s in subtitles if s.page_link and s.page_link.endswith(matched_id)]
    assert len(matched_subtitles) == 1

    subtitle = matched_subtitles[0]
    assert subtitle.language == lang
    assert subtitle.hearing_impaired is False
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.release_group == '720p-KILLERS'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_colon(episodes: dict[str, Episode]) -> None:
    lang = Language('eng')
    video = episodes['csi_cyber_s02e03']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
        subtitles = provider.query(show_id, title, video.season, video.episode, lang)

    matched_id = 'be0fedf1-3863-42bc-a026-88af7f6a9461'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1

    subtitle = matched_subtitles[0]
    assert subtitle.language == lang
    assert subtitle.hearing_impaired is False
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.release_group == 'DIMENSION'


@pytest.mark.integration
@vcr.use_cassette
def test_query_parsing_dash(episodes: dict[str, Episode]) -> None:
    lang = Language('fra')
    video = episodes['the_x_files_s10e02']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
        subtitles = provider.query(show_id, title, video.season, video.episode, lang)

    matched_id = '82efacfe-9a35-49ae-9ea8-a43af308e7e2'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1
    subtitle = matched_subtitles[0]

    assert subtitle.language == lang
    assert subtitle.hearing_impaired is False
    assert subtitle.series == video.series
    assert subtitle.season == video.season
    assert subtitle.episode == video.episode
    assert subtitle.release_group == 'KILLERS'


@pytest.mark.integration
@vcr.use_cassette
def test_query_all_series(episodes: dict[str, Episode]) -> None:
    lang = Language('eng')
    video = episodes['got_s03e10']
    with GestdownProvider() as provider:
        title, show_id = provider.get_title_and_show_id(video)
        subtitles = provider.query(show_id, title, video.season, None, lang)
    assert len(subtitles) == 85
    for subtitle in subtitles:
        assert subtitle.series == video.series
        assert subtitle.season == video.season
    assert not all(sub.episode == video.episode for sub in subtitles)


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('deu'), Language('fra')}
    expected_subtitles = {
        '90fe1369-fa0c-4154-bd04-d3d332dec587',
        '712de981-a7cc-4ce0-842c-0da9a06d1472',
    }
    with GestdownProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    with GestdownProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_alternative_series(episodes: dict[str, Episode]) -> None:
    video = episodes['turn_s04e03']
    languages = {Language('eng')}
    expected_subtitles = {
        '6081b9e1-a57c-4082-8e65-aa07d5547b64',
        '6b789fec-02e9-4a8d-b0a1-fd701a817d75',
    }
    with GestdownProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        matches = subtitles[0].get_matches(episodes['turn_s04e03'])
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
    assert matches == {'episode', 'title', 'series', 'season', 'country', 'year', 'release_group'}


@pytest.mark.integration
@vcr.use_cassette
def test_show_with_asterisk(episodes: dict[str, Episode]) -> None:
    video = episodes['the_end_of_the_fucking_world']
    languages = {Language('eng')}
    expected_subtitles = {
        '425506e2-2981-481a-b048-6b4e1efa145f',
        '0594bbe3-aef4-41a7-8673-c7d7c1b40334',
        'b54fb204-c809-4405-844b-f1fd6fe12925',
    }
    with GestdownProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        matches = subtitles[0].get_matches(episodes['the_end_of_the_fucking_world'])
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
    assert matches == {'country', 'series', 'episode', 'season', 'year'}


@pytest.mark.integration
@vcr.use_cassette
def test_download_with_bom(episodes: dict[str, Episode]) -> None:
    video = episodes['grimsburg_s01e01']
    languages = {Language('eng')}
    with GestdownProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert len(subtitles) > 0
    subtitle = subtitles[0]
    provider.download_subtitle(subtitle)
    assert subtitle.content is not None
    assert subtitle.is_valid() is True
