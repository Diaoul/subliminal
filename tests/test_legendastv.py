# -*- coding: utf-8 -*-
import os

from babelfish import Language, language_converters
import pytest
from vcr import VCR
from subliminal.exceptions import ConfigurationError, AuthenticationError
from subliminal.providers.legendastv import LegendasTvSubtitle, LegendasTvProvider

USERNAME = 'subliminal'
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


def test_get_matches_with_format_and_video_codec(episodes):
    subtitle = LegendasTvSubtitle(Language('por', 'BR'), None, '5261e6de679eb',
                                  'The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.srt', None, type='episode',
                                  season=7, no_downloads=50073, rating=10, featured=True, multiple_episodes=False,
                                  timestamp='18/10/2013 - 22h56')

    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'resolution', 'release_group', 'video_codec', 'format', 'year'}


@pytest.mark.integration
@vcr.use_cassette
def test_login():
    provider = LegendasTvProvider(USERNAME, PASSWORD)
    assert provider.logged_in is False
    provider.initialize()
    assert provider.logged_in is True


@pytest.mark.integration
@vcr.use_cassette
def test_login_bad_password():
    provider = LegendasTvProvider(USERNAME, 'wrong')
    with pytest.raises(AuthenticationError):
        provider.initialize()


@pytest.mark.integration
@vcr.use_cassette
def test_logout():
    provider = LegendasTvProvider(USERNAME, PASSWORD)
    provider.initialize()
    provider.terminate()
    assert provider.logged_in is False


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_with_series():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('The Big Bang Theory', 7, None, None)
    assert candidates
    assert len(candidates) == 1
    assert candidates[0].get('id') == '30730'


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_with_movies():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('Man of Steel', None, None, 2013)
    assert candidates
    assert len(candidates) == 1
    assert candidates[0].get('id') == '29087'


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_with_movies_without_year():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('Man of Steel', None, None, None)
    assert candidates
    assert len(candidates) == 1
    assert candidates[0].get('id') == '29087'


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_with_movies_without_year_and_partial_name():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('Man of Ste', None, None, None)
    assert not candidates


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_keyword_with_single_quote_registered_with_single_quote():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('Marvel\'s Jessica Jones', 1, None, None)
    assert candidates
    assert len(candidates) == 1
    assert candidates[0].get('id') == '39376'


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_keyword_with_single_quote_registered_without_single_quote():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('DC\'s Legends of Tomorrow', 1, None, None)
    assert candidates
    assert len(candidates) == 1
    assert candidates[0].get('id') == '39995'


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_keyword_without_single_quote_registered_without_single_quote():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('DCs Legends of Tomorrow', 1, None, None)
    assert candidates
    assert len(candidates) == 1
    assert candidates[0].get('id') == '39995'


@pytest.mark.integration
@vcr.use_cassette
def test_search_candidates_keyword_with_colon():
    with LegendasTvProvider() as provider:
        candidates = provider.search_candidates('CSI: Cyber', 1, None, None)
    assert candidates
    assert len(candidates) == 1
    assert candidates[0].get('id') == '36937'


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['man_of_steel']
    language = Language('por', 'BR')
    expected_subtitles = {
        ('Superman Man Of Steel 2013 ANOTHER NEW SOURCE TS XViD UNiQUE.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel 2013 720p R6 x264 LiNE-JYK.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Superman The Man Of Steel 2013 TS V2 XviD-Temporal.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.2013.R6.SCR.TS.Audio.Xvid.mp3-CRYS.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.2013.TS.LiNE.READNFO.x264.HiGH.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel (2013) 720p R6 LiNE 900MB Ganool.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel 2013 R6 TS XViD-PLAYNOW .srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('MAN OF STEEL 2013 R6-1080P AC3 MURDER.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel 2013  720P TS XviD MP3 MiLLENiUM.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.2013.720p.R6.LiNE.x264.AAC-DiGiTAL.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.TS.XviD-WAR.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man Of Steel 2013 REPACK TS XViD UNiQUE (SilverTorrent).srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.Of.Steel.2013.720p.BluRay.x264-Felony.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.480p.BluRay.x264-mSD.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.480p.BRRip.Xvid.AC3-UNDERCOVER.srt', '525e738d4866b'),
        ('Man.of.Steel.2013.720p.BluRay.x264.YIFY.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.720p.BRRip.x264.AC3-EVO.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.BDRip.x264-4PlayHD.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.BDRip.x264-Larceny.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.BDRiP.XViD-NoGRP.srt', '525e738d4866b'),
        ('Man of Steel [2013] BRRip XViD [AC3]-ETRG.srt', '525e738d4866b'),
        ('Man Of Steel 2013 720p BRRiP XViD UNiQUE.srt', '525e738d4866b'),
        ('Man Of Steel 2013 BRRip x264 AC3 UNiQUE.srt', '525e738d4866b'),
        ('man.of.steel.2013.1080p.bluray.x264-sector7.srt', '526076d4af488'),
        ('Man.Of.Steel.2013.720p.BRRip.x264-YIFY.srt', '525dd8547cb72'),
        ('Man.Of.Steel.2013.BDRip.x264-Larceny.srt', '525d86f6c6560'),
        ('Man.Of.Steel.2013.720p.BluRay.x264-Felony.srt', '525d86f6c6560'),
        ('Man.Of.Steel.2013.720p.BRRip.x264.AAC-ViSiON.srt', '5262e21d58bab'),
        ('Man.Of.Steel.2013.1080p.BluRay.x264.anoXmous_.srt', '52cc3e195127e'),
        ('Man.Of.Steel.3D.2013.1080p.BluRay.Half-SBS.DTS.x264-PublicHD.srt', '527a1eda17867'),
        ('Man of Steel 2013 1080p Blu-ray Remux AVC DTS-HD MA 7.1 - KRaLiMaRKo.srt', '52604f2d2099a'),
        ('Man of Steel 2013 1080p Blu-ray 3D Remux.srt', '5285f5daac692'),
        ('Man of Steel 2013 1080p Blu-ray 3D Remux.Forced.srt', '5285f5daac692'),
        ('Man of Steel (BDRip.x264-Larceny Subrip).srt', '527d55c0c02bc'),
        ('Man of Steel (2013) DVDRip XviD-MAXSPEED.srt', '54edd551e869a')
    }

    with LegendasTvProvider(USERNAME, PASSWORD) as provider:
        provider.initialize()
        subtitles = provider.query(language, title=video.title, year=video.year)
        provider.terminate()

    assert {(subtitle.name, subtitle.subtitle_id) for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['bbt_s07e05']
    language = Language('por', 'BR')
    expected_subtitles = {
        ('The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.srt', '5261e6de679eb'),
        ('The.Big.Bang.Theory.S07E05.HDTV.XviD-AFG.srt', '5261e6de679eb'),
        ('The.Big.Bang.Theory.S07E05.HDTV.x264-LOL.srt', '5261e6de679eb'),
        ('The.Big.Bang.Theory.S07E05.The.Workplace.Proximity.1080p.WEB-DL.DD5.1.H.264.srt', '5266aecaead61'),
        ('The.Big.Bang.Theory.S07.1080p.WEB-DL.DD5.1.H.264\\'
         'The.Big.Bang.Theory.S07E05.The.Workplace.Proximity.1080p.WEB-DL.DD5.1.H.264.srt', '5376e044d892e'),
        ('The.Big.Bang.Theory.S07.720p.WEB-DL.DD5.1.H.264\\'
         'The.Big.Bang.Theory.S07E05.The.Workplace.Proximity.720p.WEB-DL.DD5.1.H.264.srt', '5376e0128cfe6'),
        ('The.Big.Bang.Theory.S07.720p.HDTV.x264-maximersk\\'
         'The.Big.Bang.Theory.S07E05.720p.HDTV.x264-maximersk.srt', '5380d44e2beb1'),
        ('The.Big.Bang.Theory.S07.1080p\\The.Big.Bang.Theory.S07E05.1080.srt', '5339b32f236c7'),
        ('The.Big.Bang.Theory.S07.720p.WEB-DL.Rus.Eng.HDCLUB\\'
         'The.Big.Bang.Theory.S07E05.720p.WEB-DL.Rus.Eng.HDCLUB.srt', '5391017f64b99'),
        ('The.Big.Bang.Theory.S07E05.HDTV.XviD-AFG.srt', '54bd9555c43aa'),
        ('The Big Bang Theory S07 Season 7 720p web dl x264 MrLss\\S07E05- The Romance Resonance.srt', '5388d55b22707'),
        ('The Big Bang Theory Season 7 S07 720p Web-dl 5.1ch [C7B]\\'
         'S07E05 - The Workplace Proximity - x264 720p Web-dl 5.1ch AAC [C7B].srt', '5387d9cfc5fff'),
        ('The Big Bang Theory S07 1080p H265 Joy\\'
         'The Big Bang Theory S07E05 The Workplace Proximity  (1080p H265 Joy).srt', '56895a04ef688'),
        ('The Big Bang Theory Season 7 S07 1080p Web-dl 5.1ch [C7B]\\'
         'S07E05 - The Workplace Proximity x264 1080p Web-dl 5.1ch AAC [C7B].srt', '5387da135c96f'),
        ('TBBT S07 x264\\The.Big.Bang.Theory.S07E05.HDTV.x264-LOL.srt', '537a74584945b')
    }

    with LegendasTvProvider(USERNAME, PASSWORD) as provider:
        provider.initialize()
        subtitles = provider.query(language, title=video.series, season=video.season, episode=video.episode,
                                   year=video.year)
        provider.terminate()

    assert {(subtitle.name, subtitle.subtitle_id) for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('por', 'BR'), Language('eng')}
    expected_subtitles = {
        ('Man.Of.Steel.2013.[BluRay.BRRip.BDRip].srt', '525d8c2444851'),
        ('Superman Man Of Steel 2013 ANOTHER NEW SOURCE TS XViD UNiQUE.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel 2013 720p R6 x264 LiNE-JYK.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Superman The Man Of Steel 2013 TS V2 XviD-Temporal.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.2013.R6.SCR.TS.Audio.Xvid.mp3-CRYS.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.2013.TS.LiNE.READNFO.x264.HiGH.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel (2013) 720p R6 LiNE 900MB Ganool.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel 2013 R6 TS XViD-PLAYNOW .srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('MAN OF STEEL 2013 R6-1080P AC3 MURDER.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man of Steel 2013  720P TS XviD MP3 MiLLENiUM.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.2013.720p.R6.LiNE.x264.AAC-DiGiTAL.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.of.Steel.TS.XviD-WAR.srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man Of Steel 2013 REPACK TS XViD UNiQUE (SilverTorrent).srt', 'a50ef54a73c490f3d7f63c333f5d3e07'),
        ('Man.Of.Steel.2013.720p.BluRay.x264-Felony.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.480p.BluRay.x264-mSD.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.480p.BRRip.Xvid.AC3-UNDERCOVER.srt', '525e738d4866b'),
        ('Man.of.Steel.2013.720p.BluRay.x264.YIFY.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.720p.BRRip.x264.AC3-EVO.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.BDRip.x264-4PlayHD.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.BDRip.x264-Larceny.srt', '525e738d4866b'),
        ('Man.Of.Steel.2013.BDRiP.XViD-NoGRP.srt', '525e738d4866b'),
        ('Man of Steel [2013] BRRip XViD [AC3]-ETRG.srt', '525e738d4866b'),
        ('Man Of Steel 2013 720p BRRiP XViD UNiQUE.srt', '525e738d4866b'),
        ('Man Of Steel 2013 BRRip x264 AC3 UNiQUE.srt', '525e738d4866b'),
        ('man.of.steel.2013.1080p.bluray.x264-sector7.srt', '526076d4af488'),
        ('Man.Of.Steel.2013.720p.BRRip.x264-YIFY.srt', '525dd8547cb72'),
        ('Man.Of.Steel.2013.BDRip.x264-Larceny.srt', '525d86f6c6560'),
        ('Man.Of.Steel.2013.720p.BluRay.x264-Felony.srt', '525d86f6c6560'),
        ('Man.Of.Steel.2013.720p.BRRip.x264.AAC-ViSiON.srt', '5262e21d58bab'),
        ('Man.Of.Steel.2013.1080p.BluRay.x264.anoXmous_.srt', '52cc3e195127e'),
        ('Man.Of.Steel.3D.2013.1080p.BluRay.Half-SBS.DTS.x264-PublicHD.srt', '527a1eda17867'),
        ('Man of Steel 2013 1080p Blu-ray Remux AVC DTS-HD MA 7.1 - KRaLiMaRKo.srt', '52604f2d2099a'),
        ('Man of Steel 2013 1080p Blu-ray 3D Remux.srt', '5285f5daac692'),
        ('Man of Steel 2013 1080p Blu-ray 3D Remux.Forced.srt', '5285f5daac692'),
        ('Man of Steel (BDRip.x264-Larceny Subrip).srt', '527d55c0c02bc'),
        ('Man of Steel (2013) DVDRip XviD-MAXSPEED.srt', '54edd551e869a')
    }

    with LegendasTvProvider(USERNAME, PASSWORD) as provider:
        provider.initialize()
        subtitles = provider.list_subtitles(video, languages)
        provider.terminate()

    assert {(subtitle.name, subtitle.subtitle_id) for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language('por', 'BR')}
    expected_subtitles = {
        ('Game.of.Thrones.S03E10.Mhysa.720p.HDTV.x264-CtrlHD.srt', '55ea0ba5f54be723d3f834e426bf0204'),
        ('Game.of.Thrones.S03E10.480p.HDTV.x264-mSD.srt', '55ea0ba5f54be723d3f834e426bf0204'),
        ('Game.of.Thrones.S03E10.720p.HDTV.x264-EVOLVE.srt', '55ea0ba5f54be723d3f834e426bf0204'),
        ('Game.of.Thrones.S03E10.HDTV.x264-EVOLVE.srt', '55ea0ba5f54be723d3f834e426bf0204'),
        ('Game.of.Thrones.S03E10.HDTV.XviD-AFG.srt', '55ea0ba5f54be723d3f834e426bf0204'),
        ('Game.of.Thrones.S03E10.Mhysa.720p.BluRay.x264-DEMAND.srt', '52e4ea1c8ba43'),
        ('Game.of.Thrones.S03E10.Mhysa.720p.HDTV.x264-CtrlHD.srt', '10308877e71f0588467a1ac46cd08a81'),
        ('Game.of.Thrones.S03E10.1080i.HDTV.MPEG2.DD5.1-CtrlHD.srt', '998c246f63f8621c96cb97fafc491b1a'),
        ('Game.of.Thrones.S03E10.HDTV.x264-EVOLVE.srt', '53b37f580d814'),
        ('Game.of.Thrones.S03.1080p.BluRay.x264-ROVERS\\'
         'Game.of.Thrones.S03E10.1080p.BluRay.x264-ROVERS.srt', '52e98a71044ce'),
        ('Game.of.Thrones.S03.BDRip.x264-DEMAND\\Game.of.Thrones.S03E10.BDRip.x264-DEMAND.srt', '52e98a71044ce'),
        ('Game.of.Thrones.S03.720p.BluRay.x264-DEMAND\\'
         'Game.of.Thrones.S03E10.720p.BluRay.x264-DEMAND.srt', '52e98a71044ce'),
        ('Game.Of.Thrones.S03.Season.3.COMPLETE.720p.HDTV.x264-PublicHD\\'
         'Game.of.Thrones.S03E10.720p.HDTV.x264-EVOLVE.srt', '5443056cb0148'),
        ('Game.of.Thrones.S03E10.Mhysa.720p.WEB-DL.DD5.1.AAC2.0.H.264-YFN.srt', 'ce9c25ba16ea2f59f659defccea873f6'),
        ('(p) Game.of.Thrones.S03.480p.HDTV.x264-mSD\\Game.of.Thrones.S03E10.480p.HDTV.x264-mSD.srt', '52d297a171971'),
        ('Game.of.Thrones.S03E10.1080p.HDTV.x264-QCF.srt', 'bbaeda55c45bfe9da2b34a196434521e'),
        ('Game.of.Thrones.S03E10.Mhysa.1080p.WEB-DL.DD5.1.AAC2.0.H.264-YFN.srt', '8b567ce2eb0852950f98ef99f6e7975c')
    }

    with LegendasTvProvider(USERNAME, PASSWORD) as provider:
        provider.initialize()
        subtitles = provider.list_subtitles(video, languages)
        provider.terminate()

    assert {(subtitle.name, subtitle.subtitle_id) for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['man_of_steel']
    languages = {Language('por', 'BR'), Language('eng')}

    with LegendasTvProvider(USERNAME, PASSWORD) as provider:
        provider.initialize()
        subtitles = provider.list_subtitles(video, languages)
        subtitle = [s for s in subtitles if s.subtitle_id == '525e738d4866b'][0]
        provider.download_subtitle(subtitle)
        provider.terminate()

    assert subtitle.content is not None
    assert subtitle.is_valid() is True
