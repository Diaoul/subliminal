import pytest
import os
from vcr import VCR
from babelfish import Language

from subliminal.providers.wizdom import WizdomProvider, WizdomSubtitle

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host',
                    'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'wizdom'))


def test_get_matches_no_match(episodes):

    subtitle = WizdomSubtitle("tt0944947", dict(versioname="Game.of.Thrones.S07E07.720p.WEB.H264-STRiFE",
                                                id="190027", score=3))
    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == set()


def test_get_matches_episode(episodes):

    subtitle = WizdomSubtitle("tt0944947", dict(versioname="Game.of.Thrones.S03E10.Mhysa.720p.WEB-DL.DD5.1.H.264-NTb",
                                                id="166995", score=9))
    matches = subtitle.get_matches(episodes['got_s03e10'])
    assert matches == {"title", "series", "year", "episode", "season",
                       "episode", "video_codec", "resolution", "release_group", "format"}


def test_get_matches_movie(movies):

    subtitle = WizdomSubtitle("tt0770828", dict(versioname="man.of.steel.2013.720p.bluray.x264-felony",
                                                id="77724", score=9))
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'video_codec',
                       'resolution', 'format', 'release_group', 'imdb_id'}


@pytest.mark.integration
@vcr.use_cassette
def test_query_file_name_series_imdb_id_season_episode(episodes):

    languages = {Language('heb')}
    expected_subtitles = {"166995", "4232", "3748", "40068",
                          "39541", "4231", "46192", "71362",
                          "40067", "61901"}

    with WizdomProvider() as provider:
        subtitles = provider.query(os.path.basename(episodes['got_s03e10'].name),
                                   episodes['got_s03e10'].series_imdb_id,
                                   episodes['got_s03e10'].season,
                                   episodes['got_s03e10'].episode)

    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_file_name_imdb_id(movies):

    languages = {Language('heb')}
    expected_subtitles = {"77724", "24384", "24382", "24368",
                          "24355", "24386", "24372", "24396",
                          "24394", "24404", "24351", "24378",
                          "185106", "24402", "24366", "24400",
                          "24405", "95805", "62797", "134088",
                          "155340", "62796", "24359", "24398",
                          "66283", "24370", "114837", "75722",
                          "90978", "24380", "24390", "24363",
                          "24374", "134091", "24361", "24408",
                          "64634", "134085", "24388", "24357",
                          "24392", "24353", "24376", "24410"}

    with WizdomProvider() as provider:
        subtitles = provider.query(os.path.basename(
            movies['man_of_steel'].name), movies['man_of_steel'].imdb_id)

    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitle_episode(episodes):

    languages = {Language('heb')}
    expected_subtitles = {"166995", "4232", "3748", "40068",
                          "39541", "4231", "46192", "71362",
                          "40067", "61901"}

    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(episodes['got_s03e10'], languages)

    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):

    languages = {Language('heb')}
    expected_subtitles = {"77724", "24384", "24382", "24368",
                          "24355", "24386", "24372", "24396",
                          "24394", "24404", "24351", "24378",
                          "185106", "24402", "24366", "24400",
                          "24405", "95805", "62797", "134088",
                          "155340", "62796", "24359", "24398",
                          "66283", "24370", "114837", "75722",
                          "90978", "24380", "24390", "24363",
                          "24374", "134091", "24361", "24408",
                          "64634", "134085", "24388", "24357",
                          "24392", "24353", "24376", "24410"}

    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(movies['man_of_steel'], languages)

    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):

    with WizdomProvider() as provider:
        subtitles = provider.list_subtitles(
            movies['man_of_steel'], {Language('heb')})
        provider.download_subtitle(subtitles[0])

    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
