import os

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.providers.podnapisi import PodnapisiProvider, PodnapisiSubtitle
from subliminal.video import Episode, Movie

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'podnapisi')),
)


def test_get_matches_movie(movies: dict[str, Movie]) -> None:
    subtitle_releases = [
        'Man.Of.Steel.2013.720p.BRRip.x264.AAC-ViSiON',
        'Man.Of.Steel.2013.720p.BluRay.x264-Felony',
        'Man.Of.Steel.2013.1080p.BluRay.x264-SECTOR7',
        'Man.Of.Steel.2013.720p.BRRip.x264.AC3-UNDERCOVER',
        'Man.Of.Steel.2013.BDRip.XviD.MP3-RARBG',
        'Man.Of.Steel.(2013).BDRip.600MB.Ganool',
        'Man.of.Steel.2013.BDRip.x264.700MB-Micromkv',
        'Man.Of.Steel.2013.BRRip.AAC.x264-SSDD',
        'Man.Of.Steel.2013.BDRip.x264-Larceny',
        'Man.Of.Steel.2013.BDRiP.XViD-NoGRP',
        'Man.Of.Steel.2013.720p.BRRip.x264.AC3-EVO',
        'Man.of.Steel.2013.720p.BRRip.h264.AAC-RARBG',
        'Man.Of.Steel.[2013].BRRip.XviD-ETRG',
        'Man.of.Steel.[2013].BRRip.XViD.[AC3]-ETRG',
        'Man.Of.Steel.2013.BRRiP.XVID.AC3-MAJESTIC',
        'Man.of.steel.2013.BRRip.XviD.AC3-RARBG',
        'Man.Of.Steel.2013.720p.BRRip.x264.AC3-SUPERM4N',
        'Man.Of.Steel.2013.720p.BRRip.XviD.AC3-ViSiON',
        'Man.Of.Steel.2013.720p.BRRip.x264.AC3-JYK',
        'Man.of.Steel.[2013].DVDRIP.DIVX.[Eng]-DUQA',
        'Man.of.Steel.2013.1080p.BluRay.x264.YIFY',
    ]
    subtitle = PodnapisiSubtitle(
        language=Language('eng'),
        subtitle_id='EMgo',
        hearing_impaired=True,
        page_link=None,
        releases=subtitle_releases,
        title='Man of Steel',
        season=None,
        episode=None,
        year=2013,
    )
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'country', 'video_codec', 'resolution', 'source', 'release_group'}


def test_get_matches_episode(episodes: dict[str, Episode]) -> None:
    subtitle_releases = [
        'The.Big.Bang.Theory.S07E05.HDTV.x264-LOL',
        'The.Big.Bang.Theory.S07E05.720p.HDTV.x264-DIMENSION',
        'The.Big.Bang.Theory.S07E05.480p.HDTV.x264-mSD',
        'The.Big.Bang.Theory.S07E05.HDTV.XviD-AFG',
    ]
    subtitle = PodnapisiSubtitle(
        language=Language('eng'),
        subtitle_id='EdQo',
        hearing_impaired=False,
        page_link=None,
        releases=subtitle_releases,
        title='The Big Bang Theory',
        season=7,
        episode=5,
        year=2007,
    )
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {
        'series',
        'season',
        'episode',
        'video_codec',
        'resolution',
        'source',
        'release_group',
        'year',
        'country',
    }


def test_get_matches_episode_year(episodes: dict[str, Episode]) -> None:
    subtitle_releases = ['Dallas.2012.S01E03.HDTV.x264-LOL']
    subtitle = PodnapisiSubtitle(
        language=Language('eng'),
        subtitle_id='-5oa',
        hearing_impaired=True,
        page_link=None,
        releases=subtitle_releases,
        title='Dallas',
        season=1,
        episode=3,
        year=2012,
    )
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == {'series', 'year', 'season', 'episode'}


def test_get_matches_no_match(episodes: dict[str, Episode]) -> None:
    subtitle_releases = ['The.Big.Bang.Theory.S07E05.1080p.HDTV.DIMENSION']
    subtitle = PodnapisiSubtitle(
        language=Language('eng'),
        subtitle_id='EdQo',
        hearing_impaired=False,
        page_link=None,
        releases=subtitle_releases,
        title='The Big Bang Theory',
        season=7,
        episode=5,
        year=2007,
    )
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {'year', 'country'}


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    language = Language('eng')
    expected_subtitles = {
        'Nv0l',
        'EMgo',
        '8RIm',
        'whQm',
        'aoYm',
        'WMgp',
        'Tsko',
        'uYcm',
        'XnUm',
        'NLUo',
        'ZmIm',
        'MOko',
    }
    with PodnapisiProvider() as provider:
        subtitles = provider.query(language, video.title, year=video.year)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    language = Language('eng')
    expected_subtitles = {'EdQo', '2581', 'w581', 'ftUo', 'WNMo'}
    with PodnapisiProvider() as provider:
        subtitles = provider.query(language, video.series, season=video.season, episode=video.episode, year=video.year)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng'), Language('fra')}
    expected_subtitles = {
        'Tsko',
        'Nv0l',
        'XnUm',
        'EMgo',
        'ZmIm',
        'whQm',
        'MOko',
        'aoYm',
        'WMgp',
        'd_Im',
        'GMso',
        '8RIm',
        'NLUo',
        'uYcm',
    }
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['got_s03e10']
    languages = {Language('eng'), Language('fra')}
    expected_subtitles = {
        '8cMl',
        '6MMl',
        'jcYl',
        'am0s',
        'msYl',
        '7sMl',
        'k8Yl',
        '8BM5',
        'Eaom',
        'z8Ml',
        'lMYl',
        '78Ml',
        '0MMl',
        'a1I8',
    }
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng'), Language('fra')}
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)

    matched_id = 'GMso'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1
    subtitle = matched_subtitles[0]

    # Matches
    matches = subtitle.get_matches(video)
    assert matches == {'title', 'year', 'country', 'source', 'video_codec'}

    # Download
    provider.download_subtitle(subtitle)
    assert subtitle.content
    assert subtitle.is_valid()


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode_alternative_series(episodes: dict[str, Episode]) -> None:
    video = episodes['marvels_jessica_jones_s01e13']
    languages = {Language('eng')}
    expected_subtitles = {
        'JPY-',
        'BURB',
        'm_c-',
        'wFFC',
        'tVFC',
        'wlFC',
        'iZk-',
        'w_g-',
        'CJw-',
        'v5c-',
        's1FC',
        'u5c-',
    }
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitles_with_title_unicode(movies: dict[str, Movie]) -> None:
    video = movies['café_society']
    languages = {Language('fra')}
    expected_subtitles = {'iOlD', 'iulD', '2o5B', 'ielD'}
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)

    matched_id = 'iOlD'
    matched_subtitles = [s for s in subtitles if s.subtitle_id == matched_id]
    assert len(matched_subtitles) == 1
    subtitle = matched_subtitles[0]

    # Matches
    matches = subtitle.get_matches(movies['café_society'])
    assert matches == {'title', 'year', 'country'}

    # Download
    provider.download_subtitle(subtitle)
    assert {subtitle.subtitle_id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages
    assert subtitle.content
    assert subtitle.is_valid()
