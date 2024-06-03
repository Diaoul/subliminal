from __future__ import annotations

from babelfish import Language  # type: ignore[import-untyped]
from subliminal.providers.addic7ed import Addic7edSubtitle
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
    subtitle = Addic7edSubtitle(
        language=Language('eng'),
        subtitle_id='',
        hearing_impaired=True,
        page_link=None,
        series='the big BANG theory',
        season=6,
        episode=4,
        title=None,
        year=None,
        release_group='1080p',
    )
    expected_score = episode_scores['series'] + episode_scores['year'] + episode_scores['country']
    assert compute_score(subtitle, video) == expected_score


def test_get_score_cap(movies):
    video = movies['man_of_steel']
    subtitle = OpenSubtitlesSubtitle(
        language=Language('eng'),
        subtitle_id='1',
        hearing_impaired=True,
        page_link=None,
        matched_by='hash',
        movie_kind='movie',
        moviehash='5b8f8f4e41ccb21e',
        movie_name='Man of Steel',
        movie_release_name='man.of.steel.2013.720p.bluray.x264-felony.mkv',
        movie_year=2013,
        movie_imdb_id='tt770828',
        series_season=None,
        series_episode=None,
        filename='',
        encoding='utf-8',
    )
    assert compute_score(subtitle, video) == movie_scores['hash']


def test_compute_score_episode_imdb_id(movies):
    video = movies['man_of_steel']
    subtitle = OpenSubtitlesSubtitle(
        language=Language('eng'),
        subtitle_id='1',
        hearing_impaired=True,
        page_link=None,
        matched_by='hash',
        movie_kind='movie',
        moviehash=None,
        movie_name='Man of Steel',
        movie_release_name='man.of.steel.2013.720p.bluray.x264-felony.mkv',
        movie_year=2013,
        movie_imdb_id='tt770828',
        series_season=None,
        series_episode=None,
        filename='',
        encoding='utf-8',
    )
    assert compute_score(subtitle, video) == sum(
        movie_scores.get(m, 0)
        for m in ('imdb_id', 'title', 'year', 'country', 'release_group', 'source', 'resolution', 'video_codec')
    )


def test_compute_score_episode_title(episodes):
    video = episodes['bbt_s07e05']
    subtitle = PodnapisiSubtitle(
        language=Language('eng'),
        subtitle_id='1',
        hearing_impaired=True,
        page_link=None,
        releases=['The.Big.Bang.Theory.S07E05.The.Workplace.Proximity.720p.HDTV.x264-DIMENSION.mkv'],
        title=None,
        season=7,
        episode=5,
        year=None,
    )
    assert compute_score(subtitle, video) == sum(
        episode_scores.get(m, 0)
        for m in (
            'series',
            'year',
            'country',
            'season',
            'episode',
            'release_group',
            'source',
            'resolution',
            'video_codec',
            'title',
        )
    )


def test_compute_score_hash_hearing_impaired(movies):
    video = movies['man_of_steel']
    subtitle = OpenSubtitlesSubtitle(
        language=Language('eng'),
        subtitle_id='1',
        hearing_impaired=True,
        page_link=None,
        matched_by='hash',
        movie_kind='movie',
        moviehash='5b8f8f4e41ccb21e',
        movie_name='Man of Steel',
        movie_release_name='man.of.steel.2013.720p.bluray.x264-felony.mkv',
        movie_year=2013,
        movie_imdb_id='tt770828',
        series_season=None,
        series_episode=None,
        filename='',
        encoding='utf-8',
    )
    assert compute_score(subtitle, video, hearing_impaired=True) == (
        movie_scores['hash'] + movie_scores['hearing_impaired']
    )
