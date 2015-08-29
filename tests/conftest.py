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
                  imdb_id=770828, size=7033732714, year=2013,
                  hashes={'napiprojekt': 'de2e9caa58dd53a6ab9d241e6b252e35',
                          'opensubtitles': '5b8f8f4e41ccb21e', 'thesubdb': 'ad32876133355929d814457537e12dc2'}),
            'enders_game':
            Movie('enders.game.2013.720p.bluray.x264-sparks.mkv', 'Ender\'s Game',
                  format='BluRay', release_group='sparks', resolution='720p', video_codec='h264', year=2013)}


@pytest.fixture
def episodes():
    return {'bbt_s07e05':
            Episode(os.path.join('The Big Bang Theory', 'Season 07',
                                 'The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.mkv'),
                    'The Big Bang Theory', 7, 5, format='HDTV', release_group='DIMENSION', resolution='720p',
                    video_codec='h264', audio_codec='AC3', imdb_id=3229392, size=501910737,
                    title='The Workplace Proximity', year=2007, tvdb_id=80379,
                    hashes={'napiprojekt': 'de2e9caa58dd53a6ab9d241e6b252e35',
                            'opensubtitles': '6878b3ef7c1bd19e', 'thesubdb': '9dbbfb7ba81c9a6237237dae8589fccc'}),
            'got_s03e10':
            Episode(os.path.join('Game of Thrones', 'Season 03',
                                 'Game.of.Thrones.S03E10.Mhysa.720p.WEB-DL.DD5.1.H.264-NTb.mkv'),
                    'Game of Thrones', 3, 10, format='WEB-DL', release_group='NTb', resolution='720p',
                    video_codec='h264', audio_codec='AC3', imdb_id=2178796, size=2142810931, title='Mhysa',
                    tvdb_id=121361,
                    hashes={'napiprojekt': 'de2e9caa58dd53a6ab9d241e6b252e35',
                            'opensubtitles': 'b850baa096976c22', 'thesubdb': 'b1f899c77f4c960b84b8dbf840d4e42d'}),
            'dallas_s01e03':
            Episode('Dallas.S01E03.mkv', 'Dallas', 1, 3),
            'dallas_2012_s01e03':
            Episode('Dallas.2012.S01E03.mkv', 'Dallas', 1, 3, year=2012),
            'marvels_agents_of_shield_s02e06':
            Episode('Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv', 'Marvels Agents of S.H.I.E.L.D.',
                    2, 6, format='HDTV', release_group='KILLERS', resolution='720p', video_codec='h264', year=2013)}


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
