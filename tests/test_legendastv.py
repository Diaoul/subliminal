# -*- coding: utf-8 -*-
import os

from babelfish import Language, language_converters
import pytest
from vcr import VCR
from subliminal.exceptions import ConfigurationError, AuthenticationError
from subliminal.providers.legendastv import LegendasTVSubtitle, LegendasTVProvider, LegendasTVArchive

USERNAME = 'python-subliminal'
PASSWORD = 'subliminal'

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=os.path.join('tests', 'cassettes', 'legendastv'))


@pytest.mark.converter
def test_converter_convert_alpha3_country():
    assert language_converters['legendastv'].convert('por', 'BR') == 1


@pytest.mark.converter
def test_converter_convert_alpha3():
    assert language_converters['legendastv'].convert('eng') == 2


@pytest.mark.converter
def test_converter_convert_unsupported_alpha3():
    with pytest.raises(ConfigurationError):
        language_converters['legendastv'].convert('rus')


@pytest.mark.converter
def test_converter_reverse():
    assert language_converters['legendastv'].reverse(10) == ('por',)


@pytest.mark.converter
def test_converter_reverse_name_converter():
    assert language_converters['legendastv'].reverse(3) == ('spa',)


@pytest.mark.converter
def test_converter_reverse_unsupported_language_number():
    with pytest.raises(ConfigurationError):
        language_converters['legendastv'].reverse(20)


def test_get_matches(episodes):
    archive = LegendasTVArchive('537a74584945b', 'The.Big.Bang.Theory.S07.HDTV.x264', True, False,
                                'http://legendas.tv/download/537a74584945b/The_Big_Bang_Theory/'
                                'The_Big_Bang_Theory_S07_HDTV_x264', 6915, 10)
    subtitle = LegendasTVSubtitle(Language('por', 'BR'), 'episode', 'The Big Bang Theory', 2013, 'tt0898266', 7,
                                  archive, 'TBBT S07 x264/The.Big.Bang.Theory.S07E05.HDTV.x264-LOL.srt')

    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'year', 'season', 'episode', 'format', 'video_codec', 'series_imdb_id'}


def test_get_matches_no_match(episodes):
    archive = LegendasTVArchive('537a74584945b', 'The.Big.Bang.Theory.S07.HDTV.x264', True, False,
                                'http://legendas.tv/download/537a74584945b/The_Big_Bang_Theory/'
                                'The_Big_Bang_Theory_S07_HDTV_x264', 6915, 10)
    subtitle = LegendasTVSubtitle(Language('por', 'BR'), 'episode', 'The Big Bang Theory', 2013, 'tt0898266', 7,
                                  archive, 'TBBT S07 x264/The.Big.Bang.Theory.S07E05.HDTV.x264-LOL.srt')

    matches = subtitle.get_matches(episodes['dallas_2012_s01e03'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = LegendasTVProvider(USERNAME, PASSWORD)
    assert provider.logged_in is False
    provider.initialize()
    assert provider.logged_in is True


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = LegendasTVProvider(USERNAME, 'wrong')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = LegendasTVProvider(USERNAME, PASSWORD)
    provider.initialize()
    provider.terminate()
    assert provider.logged_in is False


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_episode(episodes):
    with LegendasTVProvider() as provider:
        titles = provider.search_titles(episodes['bbt_s07e05'].series)
    assert len(titles) == 10
    assert set(titles.keys()) == {7623, 12620, 17710, 22056, 25314, 28507, 28900, 30730, 34546, 38908}
    assert {t['title'] for t in titles.values()} == {episodes['bbt_s07e05'].series}
    assert {t['season'] for t in titles.values() if t['type'] == 'episode'} == set(range(1, 10))


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_movie(movies):
    with LegendasTVProvider() as provider:
        titles = provider.search_titles(movies['interstellar'].title)
    assert len(titles) == 2
    assert set(titles.keys()) == {34084, 37333}
    assert {t['title'] for t in titles.values()} == {movies['interstellar'].title, 'The Science of Interstellar'}


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_dots():
    with LegendasTVProvider() as provider:
        titles = provider.search_titles('11.22.63')
    assert len(titles) == 1
    assert set(titles.keys()) == {40092}


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_quote():
    with LegendasTVProvider() as provider:
        titles = provider.search_titles('Marvel\'s Jessica Jones')
    assert len(titles) == 1
    assert set(titles.keys()) == {39376}


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_with_invalid_year():
    with LegendasTVProvider() as provider:
        titles = provider.search_titles('Grave Danger')
    assert len(titles) == 1
    assert set(titles.keys()) == {22034}


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_with_season_information_in_english():
    with LegendasTVProvider() as provider:
        titles = provider.search_titles('Pretty Little Liars')
    assert len(titles) == 7
    assert set(titles.keys()) == {20917, 24586, 27500, 28332, 30303, 33223, 38105}


@pytest.mark.integration
@vcr.use_cassette
def test_search_titles_without_season_information():
    with LegendasTVProvider() as provider:
        titles = provider.search_titles('The Walking Dead Webisodes Torn Apart')
    assert len(titles) == 1
    assert set(titles.keys()) == {25770}


@pytest.mark.integration
@vcr.use_cassette
def test_get_archives():
    with LegendasTVProvider() as provider:
        archives = provider.get_archives(34084, 2)
    assert len(archives) == 2
    assert {a.id for a in archives} == {'5515d27a72921', '54a2e41d8cae4'}
    assert {a.content for a in archives} == {None}


@pytest.mark.integration
@vcr.use_cassette
def test_get_archives_no_result():
    with LegendasTVProvider() as provider:
        archives = provider.get_archives(34084, 17)
    assert len(archives) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_download_archive():
    with LegendasTVProvider(USERNAME, PASSWORD) as provider:
        archive = provider.get_archives(34084, 2)[0]
        provider.download_archive(archive)
    assert archive.content is not None


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['interstellar']
    language = Language('eng')
    expected_subtitles = {
        ('54a2e41d8cae4', 'Interstellar 2014 HDCAM NEW SOURCE READNFO XVID AC3 ACAB.srt'),
        ('5515d27a72921', 'Interstellar.2014.1080p.BluRay.x264.DTS-RARBG.eng.srt'),
    }
    with LegendasTVProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(language, video.title, year=video.year)
    assert {(s.archive.id, s.name) for s in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['colony_s01e09']
    language = Language('por', 'BR')
    expected_subtitles = {
        ('56ed8159e36ec', 'Colony.S01E09.HDTV.XviD-FUM.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.HDTV.x264-FLEET.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.1080p.WEB-DL.x265.HEVC.AAC.5.1.Condo.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.720p.HDTV.HEVC.x265-RMTeam.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.WEB-DL.x264-RARBG.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.Zero.Day.1080p.WEB-DL.6CH.x265.HEVC-PSA.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.720p.HDTV.x264-KILLERS.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.720p.WEB-DL.HEVC.x265-RMTeam.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.HDTV.XviD-AFG.srt'),
        ('56ed812f354f6', 'Colony.S01E09.HDTV.x264-FUM.srt'),
        ('56eb3817111be', 'Colony S01E09 1080p WEB DL DD5 1 H264 RARBG /'
                          'Colony S01E09 1080p WEB DL DD5 1 H264 RARBG .srt'),
        ('56ed8159e36ec', 'Colony.S01E09.Zero.Day.1080p.WEB-DL.DD5.1.H265-LGC.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.Zero.Day.720p.WEB-DL.2CH.x265.HEVC-PSA.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.1080p.WEB-DL.6CH.HEVC.x265-RMTeam.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.720p.HDTV.2CH.x265.HEVC-PSA.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.1080p.WEB-DL.DD5.1.H264-RARBG.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.HDTV.x264-FUM.srt'),
        ('56ed8159e36ec', 'Colony.S01E09.720p.WEB-DL.DD5.1.H264-RARBG.srt'),
        ('56e442ddbb615', 'Colony.S01E09.720p.HDTV.x264-KILLERS.srt')
    }
    with LegendasTVProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.query(language, video.series, video.season, video.episode, video.year)
    assert {(s.archive.id, s.name) for s in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['the_x_files_s10e02']
    languages = {Language('eng')}
    expected_subtitles = {('56a756935a76c', 'The.X-Files.S10E02.720p.HDTV.AVS.en.srt')}
    with LegendasTVProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {(s.archive.id, s.name) for s in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('eng')}
    expected_subtitles = {('525d8c2444851', 'Man.Of.Steel.2013.[BluRay.BRRip.BDRip].srt')}
    with LegendasTVProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {(s.archive.id, s.name) for s in subtitles} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['man_of_steel']
    languages = {Language('eng')}
    with LegendasTVProvider(USERNAME, PASSWORD) as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
