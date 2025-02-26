import os

import pytest
from babelfish import Language, language_converters  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.providers.tvsubtitles import TVsubtitlesProvider, TVsubtitlesSubtitle
from subliminal.video import Episode

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'tvsubtitles')),
)


@pytest.mark.converter
def test_converter_convert_alpha3_country() -> None:
    assert language_converters['tvsubtitles'].convert('por', 'BR') == 'br'


@pytest.mark.converter
def test_converter_convert_alpha3() -> None:
    assert language_converters['tvsubtitles'].convert('ukr') == 'ua'


@pytest.mark.converter
def test_converter_convert_alpha3_alpha2_converter() -> None:
    assert language_converters['tvsubtitles'].convert('fra') == 'fr'


@pytest.mark.converter
def test_converter_reverse() -> None:
    assert language_converters['tvsubtitles'].reverse('gr') == ('ell', None, None)


@pytest.mark.converter
def test_converter_reverse_name_converter() -> None:
    assert language_converters['tvsubtitles'].reverse('en') == ('eng', None, None)


def test_get_matches_format_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = TVsubtitlesSubtitle(
        language=Language('fra'),
        subtitle_id='249518',
        page_link=None,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        year=2007,
        rip='HDTV',
        release='lol-dimension',
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'year', 'country', 'source', 'release_group'}


def test_get_matches_format_equivalent_release_group(episodes: dict[str, Episode]) -> None:
    subtitle = TVsubtitlesSubtitle(
        language=Language('fra'),
        subtitle_id='249518',
        page_link=None,
        series='The Big Bang Theory',
        season=7,
        episode=5,
        year=2007,
        rip='HDTV',
        release='lol',
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'year', 'country', 'source', 'release_group'}


def test_get_matches_video_codec_resolution(episodes: dict[str, Episode]) -> None:
    subtitle = TVsubtitlesSubtitle(
        language=Language('por'),
        subtitle_id='261077',
        page_link=None,
        series='Game of Thrones',
        season=3,
        episode=10,
        year=None,
        rip='720p.BluRay',
        release='x264-DEMAND',
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'series', 'season', 'episode', 'year', 'country', 'video_codec', 'resolution'}


def test_get_matches_only_year_country(episodes: dict[str, Episode]) -> None:
    subtitle = TVsubtitlesSubtitle(
        language=Language('por'),
        subtitle_id='261077',
        page_link=None,
        series='Game of Thrones',
        season=3,
        episode=10,
        year=None,
        rip='1080p.BluRay',
        release='DEMAND',
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'year', 'country'}


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle = TVsubtitlesSubtitle(
        language=Language('por'),
        subtitle_id='261077',
        page_link=None,
        series='Game of Thrones',
        season=3,
        episode=10,
        year=2011,
        rip='1080p.BluRay',
        release='DEMAND',
    )
    matches = subtitle.get_matches(episodes['house_of_cards_us_s06e01'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('The Big Bang Theory')
    assert show_id == 154


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_incomplete() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('The Big Bang')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_ambiguous() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('New Girl')
    assert show_id == 977


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_us() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('House of Cards', 2013)
    assert show_id == 1246


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_uk() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('Beautiful People')
    assert show_id == 657


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_no_year() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('Dallas')
    assert show_id == 646


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_year_in_title() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('Dallas', 2012)
    assert show_id == 1127


@pytest.mark.integration
@vcr.use_cassette
def test_search_show_id_error() -> None:
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id('The Big How I Met Your Mother')
    assert show_id is None


@pytest.mark.integration
@vcr.use_cassette
def test_get_episode_ids() -> None:
    expected_episode_ids = {
        1: 34274,
        2: 34275,
        3: 34276,
        4: 34277,
        5: 34849,
        6: 34923,
        7: 35022,
        8: 35023,
        9: 35436,
        10: 35503,
        11: 35887,
        12: 36369,
        13: 36513,
        14: 36610,
        15: 36718,
        16: 36795,
        17: 37152,
        18: 37153,
        19: 37407,
        20: 37863,
        21: 38218,
        22: 38574,
        23: 38686,
        24: 38687,
    }
    with TVsubtitlesProvider() as provider:
        episode_ids = provider.get_episode_ids(154, 5)
    assert episode_ids == expected_episode_ids


@pytest.mark.integration
@vcr.use_cassette
def test_get_episode_ids_wrong_season() -> None:
    with TVsubtitlesProvider() as provider:
        episode_ids = provider.get_episode_ids(154, 55)
    assert len(episode_ids) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    expected_subtitles = {
        '268673',
        '249733',
        '249518',
        '249519',
        '249714',
        '32596',
        '249590',
        '249592',
        '249499',
        '261214',
    }
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season, video.episode, video.year)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_no_year(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_s01e03']
    expected_subtitles = {'124753', '167064'}
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season, video.episode, video.year)
    assert show_id == 646
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_with_quote(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    expected_subtitles = {'91420', '278637', '278909', '278910', '278972', '279205', '279216', '279217', '285917'}
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season, video.episode, video.year)
    assert show_id == 1340
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_series(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    with TVsubtitlesProvider() as provider:
        subtitles = provider.query(155, video.series[:12], video.season, video.episode, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_query_wrong_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    with TVsubtitlesProvider() as provider:
        show_id = provider.search_show_id(video.series, video.year)
        subtitles = provider.query(show_id, video.series, video.season, 55, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    expected_subtitles = {'249592', '249499', '32596', '249518'}
    with TVsubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
    assert subtitles[0].release == 'The Big Bang Theory 7x05 (HDTV.LOL)'


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_alternative_series(episodes: dict[str, Episode]) -> None:
    video = episodes['turn_s03e01']
    languages = {Language('fra')}
    expected_subtitles = {'307588'}
    with TVsubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    with TVsubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_with_quote(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_agents_of_shield_s02e06']
    languages = {Language('eng'), Language('fra')}
    with TVsubtitlesProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
