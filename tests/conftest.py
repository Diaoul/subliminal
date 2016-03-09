# -*- coding: utf-8 -*-
from io import BytesIO
import os
from zipfile import ZipFile

import pytest
import requests
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from subliminal import Episode, Movie
from subliminal.cache import region


@pytest.fixture(autouse=True, scope='session')
def configure_region():
    region.configure('dogpile.cache.null')
    region.configure = Mock()


@pytest.fixture
def movies():
    return {'man_of_steel':
            Movie(os.path.join('Man of Steel (2013)', 'man.of.steel.2013.720p.bluray.x264-felony.mkv'), 'Man of Steel',
                  format='BluRay', release_group='felony', resolution='720p', video_codec='h264', audio_codec='DTS',
                  imdb_id='tt0770828', size=7033732714, year=2013,
                  hashes={'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                          'opensubtitles': '5b8f8f4e41ccb21e', 'thesubdb': 'ad32876133355929d814457537e12dc2'}),
            'enders_game':
            Movie('enders.game.2013.720p.bluray.x264-sparks.mkv', 'Ender\'s Game',
                  format='BluRay', release_group='sparks', resolution='720p', video_codec='h264', year=2013)}


@pytest.fixture
def episodes():
    return {'bbt_s07e05':
            Episode(os.path.join('The Big Bang Theory', 'Season 07',
                                 'The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.mkv'),
                    'The Big Bang Theory', 7, 5, title='The Workplace Proximity', year=2007, tvdb_id=4668379,
                    series_tvdb_id=80379, series_imdb_id='tt0898266', format='HDTV', release_group='DIMENSION',
                    resolution='720p', video_codec='h264', audio_codec='AC3', imdb_id='tt3229392', size=501910737,
                    hashes={'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                            'opensubtitles': '6878b3ef7c1bd19e', 'thesubdb': '9dbbfb7ba81c9a6237237dae8589fccc'}),
            'got_s03e10':
            Episode(os.path.join('Game of Thrones', 'Season 03',
                                 'Game.of.Thrones.S03E10.Mhysa.720p.WEB-DL.DD5.1.H.264-NTb.mkv'),
                    'Game of Thrones', 3, 10, title='Mhysa', tvdb_id=4517466, series_tvdb_id=121361,
                    series_imdb_id='tt0944947', format='WEB-DL', release_group='NTb', resolution='720p',
                    video_codec='h264', audio_codec='AC3', imdb_id='tt2178796', size=2142810931,
                    hashes={'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                            'opensubtitles': 'b850baa096976c22', 'thesubdb': 'b1f899c77f4c960b84b8dbf840d4e42d'}),
            'dallas_s01e03':
            Episode('Dallas.S01E03.mkv', 'Dallas', 1, 3),
            'dallas_2012_s01e03':
            Episode('Dallas.2012.S01E03.mkv', 'Dallas', 1, 3, year=2012, original_series=False),
            'marvels_agents_of_shield_s02e06':
            Episode('Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv',
                    'Marvel\'s Agents of S.H.I.E.L.D.', 2, 6, year=2013, format='HDTV', release_group='KILLERS',
                    resolution='720p', video_codec='h264'),
            'csi_cyber_s02e03':
            Episode('CSI.Cyber.S02E03.hdtv-lol.mp4', 'CSI: Cyber', 2, 3, format='HDTV', release_group='lol'),
            'the_x_files_s10e02':
            Episode('The.X-Files.S10E02.HDTV.x264-KILLERS.mp4', 'The X-Files', 10, 2, format='HDTV',
                    release_group='KILLERS', video_codec='h264')}


@pytest.fixture(scope='session')
def mkv():
    data_path = os.path.join('tests', 'data', 'mkv')

    # download matroska test suite
    if not os.path.exists(data_path) or len(os.listdir(data_path)) != 8:
        r = requests.get('http://downloads.sourceforge.net/project/matroska/test_files/matroska_test_w1_1.zip')
        with ZipFile(BytesIO(r.content), 'r') as f:
            f.extractall(data_path, [m for m in f.namelist() if os.path.splitext(m)[1] == '.mkv'])

    # populate a dict with mkv files
    files = {}
    for path in os.listdir(data_path):
        name, _ = os.path.splitext(path)
        files[name] = os.path.join(data_path, path)

    return files
