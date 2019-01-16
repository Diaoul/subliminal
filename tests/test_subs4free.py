# -*- coding: utf-8 -*-
import os

from babelfish import Language
import pytest
from vcr import VCR

from subliminal.providers.subs4free import Subs4FreeSubtitle, Subs4FreeProvider

vcr = VCR(path_transformer=lambda path: path + '.yaml',
          record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
          cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'subs4free')))


def test_get_matches_movie(movies):
    subtitle = Subs4FreeSubtitle(Language.fromalpha2('el'), '', 'Man of Steel', 2013,
                                 'Man Of Steel 2013 720p BluRay x264-Felony', '')
    matches = subtitle.get_matches(movies['man_of_steel'])
    assert matches == {'release_group', 'resolution', 'source', 'year', 'video_codec', 'title'}


def test_get_matches_movie_no_match(movies):
    subtitle = Subs4FreeSubtitle(Language.fromalpha2('el'), '', 'Man of Steel', 2013,
                                 'Man Of Steel 2013 720p BluRay x264-Felony', '')
    matches = subtitle.get_matches(movies['café_society'])
    assert matches == set()


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_ids_movie(movies):
    video = movies['man_of_steel']
    with Subs4FreeProvider() as provider:
        show_ids = provider.get_show_ids(video.title, video.year)
    assert show_ids == ['movie-m712248b6cf.html']


@pytest.mark.integration
@vcr.use_cassette
def test_get_show_ids_unicode(movies):
    video = movies['café_society']
    with Subs4FreeProvider() as provider:
        show_ids = provider.get_show_ids(video.title, video.year)
    assert show_ids == []


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie(movies):
    video = movies['man_of_steel']
    expected_languages = {Language.fromalpha2(l) for l in ['el', 'en']}
    with Subs4FreeProvider() as provider:
        subtitles = provider.query('movie-m712248b6cf.html', video.title, video.year)
    assert len(subtitles) == 44
    assert {subtitle.language for subtitle in subtitles} == expected_languages


@pytest.mark.integration
@vcr.use_cassette
def test_query_movie_no_results(movies):
    video = movies['café_society']
    with Subs4FreeProvider() as provider:
        subtitles = provider.query(None, video.title, video.year)
    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie(movies):
    video = movies['enders_game']
    languages = {Language.fromalpha2('el')}
    expected_subtitles = {
        'https://www.sf4-industry.com/download-s1783d2262e.html',
        'https://www.sf4-industry.com/download-s3e321a77b0.html',
        'https://www.sf4-industry.com/download-sc1b4dfecfe.html',
        'https://www.sf4-industry.com/download-s2e127a772e.html',
        'https://www.sf4-industry.com/download-sbdefca1181.html',
        'https://www.sf4-industry.com/download-sbfe85a69a8.html',
        'https://www.sf4-industry.com/download-s0c10a505d1.html',
        'https://www.sf4-industry.com/download-s0d4e79cc8c.html',
        'https://www.sf4-industry.com/download-s199433c9fc.html',
        'https://www.sf4-industry.com/download-s690ba33812.html',
        'https://www.sf4-industry.com/download-s89af177d9c.html',
        'https://www.sf4-industry.com/download-sa7b83a14e9.html',
        'https://www.sf4-industry.com/download-s9f01fe7f42.html',
        'https://www.sf4-industry.com/download-s7de44ce383.html',
        'https://www.sf4-industry.com/download-s77bdf9715f.html'}
    with Subs4FreeProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert {subtitle.id for subtitle in subtitles} == expected_subtitles
    assert {subtitle.language for subtitle in subtitles} == languages


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_movie_no_results(movies):
    video = movies['café_society']
    languages = {Language.fromalpha2('el')}
    with Subs4FreeProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
    assert subtitles == []


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_movie(movies):
    video = movies['enders_game']
    languages = {Language.fromalpha2('el')}
    with Subs4FreeProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_movie_rar(movies):
    video = movies['man_of_steel']
    languages = {Language.fromalpha2('el')}
    with Subs4FreeProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True


@pytest.mark.integration
@vcr.use_cassette
def test_download_subtitle_movie_zip(movies):
    video = movies['interstellar']
    languages = {Language.fromalpha2('el')}
    with Subs4FreeProvider() as provider:
        subtitles = provider.list_subtitles(video, languages)
        provider.download_subtitle(subtitles[0])
    assert subtitles[0].content is not None
    assert subtitles[0].is_valid() is True
