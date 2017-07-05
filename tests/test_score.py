# -*- coding: utf-8 -*-
from __future__ import division

from babelfish import Language

from subliminal.providers.addic7ed import Addic7edSubtitle
from subliminal.providers.legendastv import LegendasTVArchive, LegendasTVSubtitle
from subliminal.providers.opensubtitles import OpenSubtitlesSubtitle
from subliminal.providers.podnapisi import PodnapisiSubtitle
from subliminal.score import compute_score, episode_scores, movie_scores, solve_episode_equations, solve_movie_equations


def test_episode_equations():
    expected_scores = {}
    for symbol, score in solve_episode_equations().items():
        expected_scores[str(symbol)] = score

    assert episode_scores == expected_scores


def test_movie_equations():
    expected_scores = {}
    for symbol, score in solve_movie_equations().items():
        expected_scores[str(symbol)] = score

    assert movie_scores == expected_scores


def test_compute_score(episodes):
    video = episodes['bbt_s07e05']
    subtitle = Addic7edSubtitle(Language('eng'), True, None, 'the big BANG theory', 6, 4, None, None, '1080p', None)
    assert compute_score(subtitle, video) == episode_scores['series'] + episode_scores['year']


def test_get_score_cap(movies):
    video = movies['man_of_steel']
    subtitle = OpenSubtitlesSubtitle(Language('eng'), True, None, 1, 'hash', 'movie', '5b8f8f4e41ccb21e',
                                     'Man of Steel', 'man.of.steel.2013.720p.bluray.x264-felony.mkv', 2013, 770828,
                                     None, None, '', 'utf-8', False)
    assert compute_score(subtitle, video) == movie_scores['hash']


def test_compute_score_episode_imdb_id(movies):
    video = movies['man_of_steel']
    subtitle = OpenSubtitlesSubtitle(Language('eng'), True, None, 1, 'hash', 'movie', None,
                                     'Man of Steel', 'man.of.steel.2013.720p.bluray.x264-felony.mkv', 2013, 770828,
                                     None, None, '', 'utf-8', False)
    assert compute_score(subtitle, video) == sum(movie_scores.get(m, 0) for m in
                                                 ('imdb_id', 'title', 'year', 'release_group', 'format', 'resolution',
                                                  'video_codec'))


def test_compute_score_episode_title(episodes):
    video = episodes['bbt_s07e05']
    subtitle = PodnapisiSubtitle(Language('eng'), True, None, 1,
                                 ['The.Big.Bang.Theory.S07E05.The.Workplace.Proximity.720p.HDTV.x264-DIMENSION.mkv'],
                                 None, 7, 5, None)
    assert compute_score(subtitle, video) == sum(episode_scores.get(m, 0) for m in
                                                 ('series', 'year', 'season', 'episode', 'release_group', 'format',
                                                  'resolution', 'video_codec', 'title'))


def test_compute_score_hash_hearing_impaired(movies):
    video = movies['man_of_steel']
    subtitle = OpenSubtitlesSubtitle(Language('eng'), True, None, 1, 'hash', 'movie', '5b8f8f4e41ccb21e',
                                     'Man of Steel', 'man.of.steel.2013.720p.bluray.x264-felony.mkv', 2013, 770828,
                                     None, None, '', 'utf-8', False)
    assert compute_score(subtitle, video, hearing_impaired=True) == (movie_scores['hash'] +
                                                                     movie_scores['hearing_impaired'])


def test_compute_score_trusted_opensubtitles(movies):
    video = movies['man_of_steel']
    subtitle = OpenSubtitlesSubtitle(Language('eng'), True, None, 1, 'hash', 'movie', '5b8f8f4e41ccb21e',
                                     'Man of Steel', 'man.of.steel.2013.720p.bluray.x264-felony.mkv', 2013, 770828,
                                     None, None, '', 'utf-8', True)
    assert compute_score(subtitle, video, trusted=True) == (movie_scores['hash'] +
                                                            movie_scores['trusted'])


def test_compute_score_trusted_legendastv(episodes):
    video = episodes['bbt_s07e05']
    archive = LegendasTVArchive('537a74584945b', 'The.Big.Bang.Theory.S07E05.HDTV.x264', True, True,
                                'http://legendas.tv/download/537a74584945b/The_Big_Bang_Theory/'
                                'The_Big_Bang_Theory_S07E05_HDTV_x264', 6915, 10)
    subtitle = LegendasTVSubtitle(Language('por', 'BR'), 'episode', 'The Big Bang Theory', 2013, 'tt0898266', 7,
                                  archive, 'TBBT S07 x264/The.Big.Bang.Theory.S07E05.HDTV.x264-LOL.srt', True)
    assert compute_score(subtitle, video, trusted=True) == (episode_scores['format'] + episode_scores['series'] +
                                                            episode_scores['season'] + episode_scores['release_group'] +
                                                            episode_scores['year'] + episode_scores['video_codec'] +
                                                            episode_scores['episode'] + episode_scores['trusted']
                                                            )


def test_compute_score_not_trusted_legendastv(episodes):
    video = episodes['bbt_s07e05']
    archive = LegendasTVArchive('537a74584945b', 'The.Big.Bang.Theory.S07E05.HDTV.x264', True, False,
                                'http://legendas.tv/download/537a74584945b/The_Big_Bang_Theory/'
                                'The_Big_Bang_Theory_S07E05_HDTV_x264', 6915, 10)
    subtitle = LegendasTVSubtitle(Language('por', 'BR'), 'episode', 'The Big Bang Theory', 2013, 'tt0898266', 7,
                                  archive, 'TBBT S07 x264/The.Big.Bang.Theory.S07E05.HDTV.x264-LOL.srt', False)
    assert compute_score(subtitle, video, trusted=False) == (episode_scores['format'] + episode_scores['series'] +
                                                             episode_scores['season'] + episode_scores['episode'] +
                                                             episode_scores['year'] + episode_scores['video_codec'] +
                                                             episode_scores['release_group']
                                                             )
