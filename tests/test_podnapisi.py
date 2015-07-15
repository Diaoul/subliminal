# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.podnapisi import PodnapisiProvider, PodnapisiSubtitle


vcr = VCR(path_transformer=lambda path: path + '.yaml',
          cassette_library_dir=os.path.join('tests', 'cassettes', 'podnapisi'))


def test_get_matches_movie(movies):
    subtitle_releases = [
        'Man.Of.Steel.2013.720p.BRRip.x264.AAC-ViSiON', 'Man.Of.Steel.2013.720p.BluRay.x264-Felony',
        'Man.Of.Steel.2013.1080p.BluRay.x264-SECTOR7', 'Man.Of.Steel.2013.720p.BRRip.x264.AC3-UNDERCOVER',
        'Man.Of.Steel.2013.BDRip.XviD.MP3-RARBG', 'Man.Of.Steel.(2013).BDRip.600MB.Ganool',
        'Man.of.Steel.2013.BDRip.x264.700MB-Micromkv', 'Man.Of.Steel.2013.BRRip.AAC.x264-SSDD',
        'Man.Of.Steel.2013.BDRip.x264-Larceny', 'Man.Of.Steel.2013.BDRiP.XViD-NoGRP',
        'Man.Of.Steel.2013.720p.BRRip.x264.AC3-EVO', 'Man.of.Steel.2013.720p.BRRip.h264.AAC-RARBG',
        'Man.Of.Steel.[2013].BRRip.XviD-ETRG', 'Man.of.Steel.[2013].BRRip.XViD.[AC3]-ETRG',
        'Man.Of.Steel.2013.BRRiP.XVID.AC3-MAJESTIC', 'Man.of.steel.2013.BRRip.XviD.AC3-RARBG',
        'Man.Of.Steel.2013.720p.BRRip.x264.AC3-SUPERM4N', 'Man.Of.Steel.2013.720p.BRRip.XviD.AC3-ViSiON',
        'Man.Of.Steel.2013.720p.BRRip.x264.AC3-JYK', 'Man.of.Steel.[2013].DVDRIP.DIVX.[Eng]-DUQA\u252c\xab',
        'Man.of.Steel.2013.1080p.BluRay.x264.YIFY'
    ]
    subtitle = PodnapisiSubtitle(Language('eng'), True, None, 'EMgo', subtitle_releases, 'Man of Steel', None, None,
                                 2013)
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'title', 'year', 'video_codec', 'resolution', 'format', 'release_group'}


def test_get_matches_episode(episodes):
    subtitle_releases = [
        'The.Big.Bang.Theory.S07E05.HDTV.x264-LOL', 'The.Big.Bang.Theory.S07E05.720p.HDTV.x264-DIMENSION',
        'The.Big.Bang.Theory.S07E05.480p.HDTV.x264-mSD', 'The.Big.Bang.Theory.S07E05.HDTV.XviD-AFG'
    ]
    subtitle = PodnapisiSubtitle(Language('eng'), False, None, 'EdQo', subtitle_releases, 'The Big Bang Theory', 7, 5,
                                 2007)
    matches = subtitle.get_matches(episodes['bbt_s07e05'])
    assert matches == {'series', 'season', 'episode', 'video_codec', 'resolution', 'format', 'release_group', 'year',
                       'hearing_impaired'}


def test_get_matches_no_match(episodes):
    subtitle_releases = ['The.Big.Bang.Theory.S07E05.1080p.HDTV.DIMENSION']
    subtitle = PodnapisiSubtitle(Language('eng'), False, None, 'EdQo', subtitle_releases, 'The Big Bang Theory', 7, 5,
                                 2007)
    matches = subtitle.get_matches(episodes['got_s03e10'], hearing_impaired=True)
    assert matches == {'year'}


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['man_of_steel']
    language = Language('eng')
    expected_subtitles = {'Nv0l', 'EMgo', '8RIm', 'whQm', 'aoYm', 'WMgp', 'Tsko', 'uYcm', 'XnUm', 'NLUo', 'ZmIm',
                          'MOko'}
    with PodnapisiProvider() as provider:
        subtitles = provider.query(language, video.title, year=video.year)
    print(repr({subtitle.pid for subtitle in subtitles}))
    assert {subtitle.pid for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_query_episode(episodes):
    video = episodes['bbt_s07e05']
    language = Language('eng')
    expected_subtitles = {'EdQo', '2581', 'w581', 'ftUo', 'WNMo'}
    with PodnapisiProvider() as provider:
        subtitles = provider.query(language, video.series, season=video.season, episode=video.episode,
                                   year=video.year)
    assert {subtitle.pid for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == {language}


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('eng'), Language('fra')}
    expected_subtitles = {'Tsko', 'Nv0l', 'XnUm', 'EMgo', 'ZmIm', 'whQm', 'MOko', 'aoYm', 'WMgp', 'd_Im', 'GMso',
                          '8RIm', 'NLUo', 'uYcm'}
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.pid for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_episode(episodes):
    video = episodes['got_s03e10']
    languages = {Language('eng'), Language('fra')}
    expected_subtitles = {'8cMl', '6MMl', 'jcYl', 'am0s', 'msYl', '7sMl', 'k8Yl', '8BM5', 'Eaom', 'z8Ml', 'lMYl',
                          '78Ml', '0MMl', 'a1I8'}
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.pid for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle(movies):
    video = movies['man_of_steel']
    languages = {Language('eng'), Language('fra')}
    with PodnapisiProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        subtitle = [s for s in subtitles if s.pid == 'GMso'][0]
        provider.download_subtitle(subtitle)
    assert subtitle.content is not None
    assert subtitle.is_valid() is True
