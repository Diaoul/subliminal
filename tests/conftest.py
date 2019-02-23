# -*- coding: utf-8 -*-
import subprocess
from io import BytesIO
import os
from zipfile import ZipFile

import pytest
import requests
from babelfish import Country

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
                  source='Blu-ray', release_group='felony', resolution='720p', video_codec='H.264', audio_codec='DTS',
                  imdb_id='tt0770828', size=7033732714, year=2013,
                  hashes={'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                          'opensubtitles': '5b8f8f4e41ccb21e',
                          'shooter': '314f454ab464775498ae6f1f5ad813a9;fdaa8b702d8936feba2122e93ba5c44f;'
                                     '0a6935e3436aa7db5597ef67a2c494e3;4d269733f36ddd49f71e92732a462fe5',
                          'thesubdb': 'ad32876133355929d814457537e12dc2'}),
            'enders_game':
            Movie('enders.game.2013.720p.bluray.x264-sparks.mkv', 'Ender\'s Game',
                  source='Blu-ray', release_group='sparks', resolution='720p', video_codec='H.264', year=2013),
            'café_society':
            Movie(u'Café Society.1080p.avc1.RARBG.mp4', u'Café Society', year=2016),
            'interstellar':
            Movie('Interstellar.2014.2014.1080p.BluRay.x264.YIFY.rar', 'Interstellar',
                  source='Blu-ray', release_group='YIFY', resolution='1080p', video_codec='H.264', year=2014),
            'jack_reacher_never_go_back':
            Movie(os.path.join('Jack Reacher- Never Go Back (2016)',
                               'Jack.Reacher.Never.Go.Back.2016.1080p.WEBDL.AC3.x264-FGT.mkv'),
                  'Jack Reacher: Never Go Back',
                  source='Web', release_group='FGT', resolution='1080p', video_codec='H.264',
                  audio_codec='Dolby Digital', imdb_id='tt3393786', year=2016)
            }


@pytest.fixture
def episodes():
    return {'bbt_s07e05':
            Episode(os.path.join('The Big Bang Theory', 'Season 07',
                                 'The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.mkv'),
                    'The Big Bang Theory', 7, 5, title='The Workplace Proximity', year=2007, tvdb_id=4668379,
                    series_tvdb_id=80379, series_imdb_id='tt0898266', source='HDTV', release_group='DIMENSION',
                    resolution='720p', video_codec='H.264', audio_codec='Dolby Digital',
                    imdb_id='tt3229392', size=501910737,
                    hashes={'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                            'opensubtitles': '6878b3ef7c1bd19e',
                            'shooter': 'c13e0e5243c56d280064d344676fff94;cd4184d1c0c623735f6db90841ce15fc;'
                                       '3faefd72f92b63f2504269b4f484a377;8c68d1ef873afb8ba0cc9f97cbac41c1',
                            'thesubdb': '9dbbfb7ba81c9a6237237dae8589fccc'}),
            'got_s03e10':
            Episode(os.path.join('Game of Thrones', 'Season 03',
                                 'Game.of.Thrones.S03E10.Mhysa.720p.WEB-DL.DD5.1.H.264-NTb.mkv'),
                    'Game of Thrones', 3, 10, title='Mhysa', tvdb_id=4517466, series_tvdb_id=121361,
                    series_imdb_id='tt0944947', source='Web', release_group='NTb', resolution='720p',
                    video_codec='H.264', audio_codec='Dolby Digital', imdb_id='tt2178796', size=2142810931,
                    hashes={'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                            'opensubtitles': 'b850baa096976c22',
                            'shooter': 'b02d992c04ad74b31c252bd5a097a036;ef1b32f873b2acf8f166fc266bdf011a;'
                                       '82ce34a3bcee0c66ed3b26d900d31cca;78113770551f3efd1e2d4ec45898c59c',
                            'thesubdb': 'b1f899c77f4c960b84b8dbf840d4e42d'}),
            'dallas_s01e03':
            Episode('Dallas.S01E03.mkv', 'Dallas', 1, 3, title='Spy in the House', year=1978, tvdb_id=228224,
                    series_tvdb_id=77092, series_imdb_id='tt0077000'),
            'dallas_2012_s01e03':
            Episode('Dallas.2012.S01E03.mkv', 'Dallas', 1, 3, title='The Price You Pay', year=2012,
                    original_series=False, tvdb_id=4199511, series_tvdb_id=242521, series_imdb_id='tt1723760',
                    imdb_id='tt2205526'),
            'marvels_agents_of_shield_s02e06':
            Episode('Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv',
                    'Marvel\'s Agents of S.H.I.E.L.D.', 2, 6, year=2013, source='HDTV', release_group='KILLERS',
                    resolution='720p', video_codec='H.264'),
            'csi_cyber_s02e03':
            Episode('CSI.Cyber.S02E03.hdtv-lol.mp4', 'CSI: Cyber', 2, 3, source='HDTV', release_group='lol'),
            'the_x_files_s10e02':
            Episode('The.X-Files.S10E02.HDTV.x264-KILLERS.mp4', 'The X-Files', 10, 2, source='HDTV',
                    release_group='KILLERS', video_codec='H.264'),
            'colony_s01e09':
            Episode('Colony.S01E09.720p.HDTV.x264-KILLERS.mkv', 'Colony', 1, 9, title='Zero Day', year=2016,
                    tvdb_id=5463229, series_tvdb_id=284210, series_imdb_id='tt4209256', source='HDTV',
                    release_group='KILLERS', resolution='720p', video_codec='H.264', imdb_id='tt4926022'),
            'the_jinx_e05':
            Episode('The.Jinx-The.Life.and.Deaths.of.Robert.Durst.E05.BDRip.x264-ROVERS.mkv',
                    'The Jinx: The Life and Deaths of Robert Durst', 1, 5, year=2015, original_series=True,
                    source='Blu-ray', release_group='ROVERS', video_codec='H.264'),
            'the_100_s03e09':
            Episode('The.100.S03E09.720p.HDTV.x264-AVS.mkv', 'The 100', 3, 9, title='Stealing Fire', year=2014,
                    tvdb_id=5544536, series_tvdb_id=268592, series_imdb_id='tt2661044', source='HDTV',
                    release_group='AVS', resolution='720p', video_codec='H.264', imdb_id='tt4799896'),
            'the fall':
            Episode('the_fall.3x01.720p_hdtv_x264-fov.mkv', 'The Fall', 3, 1, title='The Fall', year=2013,
                    tvdb_id=5749493, series_tvdb_id=258107, series_imdb_id='tt2294189', source='HDTV',
                    release_group='fov', resolution='720p', video_codec='H.264', imdb_id='tt4516230'),
            'csi_s15e18':
            Episode('CSI.S15E18.720p.HDTV.X264.DIMENSION.mkv', 'CSI: Crime Scene Investigation', 15, 18,
                    title='The End Game', year=2000, tvdb_id=5104359, series_tvdb_id=72546, series_imdb_id='tt0247082',
                    source='HDTV', release_group='DIMENSION', resolution='720p', video_codec='H.264',
                    imdb_id='tt4145952'),
            'turn_s04e03':
            Episode('Turn.S04E03.720p.HDTV.x264-AVS.mkv', "TURN: Washington's Spies", 4, 3,
                    title='Blood for Blood', year=2014, tvdb_id=6124360, series_tvdb_id=272135,
                    series_imdb_id='tt2543328',
                    source='HDTV', release_group='AVS', resolution='720p', video_codec='H.264',
                    imdb_id='tt6137686', alternative_series=['Turn']),
            'turn_s03e01':
            Episode('Turn.S03E01.720p.HDTV.x264-AVS.mkv', "TURN: Washington's Spies", 3, 1,
                    title='Valediction', year=2014, tvdb_id=5471384, series_tvdb_id=272135,
                    series_imdb_id='tt2543328',
                    source='HDTV', release_group='AVS', resolution='720p', video_codec='H.264',
                    imdb_id='tt4909774', alternative_series=['Turn']),
            'marvels_jessica_jones_s01e13':
            Episode('Marvels.Jessica.Jones.S01E13.720p.WEBRip.x264-2HD', "Marvels Jessica Jones", 1, 13,
                    title='AKA Smile', year=2015, tvdb_id=5311273, series_tvdb_id=284190,
                    series_imdb_id='tt2357547',
                    source='Web', release_group='2HD', resolution='720p', video_codec='H.264',
                    imdb_id='tt4162096', alternative_series=['Jessica Jones']),
            'fear_walking_dead_s03e10':
            Episode('Fear.the.Walking.Dead.S03E10.1080p.WEB-DL.DD5.1.H264-RARBG', 'Fear the Walking Dead', 3, 10,
                    resolution='1080p', source='Web', video_codec='H.264', release_group='RARBG'),
            'the_end_of_the_fucking_world':
            Episode('the.end.of.the.fucking.world.s01e04.720p.web.x264-skgtv.mkv', 'The End of the Fucking World', 1, 4,
                    resolution='720p', source='Web', video_codec='H.264', release_group='skgtv',
                    alternative_series=['The end of the f***ing world']),
            'Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02':
            Episode('Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02.720p.HDTV.x264-AVS', 'Marvels.Agents.of.S.H.I.E.L.D', 5,
                    1, resolution='720p', source='HDTV', video_codec='H.264', release_group='AVS'),
            'alex_inc_s01e04':
            Episode('Alex.Inc.S01E04.HDTV.x264-SVA.mkv', 'Alex, Inc.', 1, 4, source='HDTV', video_codec='H.264',
                    release_group='SVA', year=2018, title='The Nanny', series_imdb_id='tt6466948', tvdb_id=6627151,
                    series_tvdb_id=328635),
            'shameless_us_s08e01':
            Episode('Shameless.US.s08e01.web.h264-convoy', 'Shameless', 8, 1, source='Web', video_codec='H.264',
                    country=Country('US'), original_series=False, release_group='convoy', year=2011,
                    alternative_series=['Shameless US'], title='We Become What We... Frank!',
                    series_imdb_id='tt1586680', series_tvdb_id=161511, imdb_id='tt6347410', tvdb_id=6227949),
            'house_of_cards_us_s06e01':
            Episode('house.of.cards.us.s06e01.720p.web-dl.x264', 'House of Cards', 6, 1, source='Web',
                    video_codec='H.264', country=Country('US'), year=2013, original_series=False,
                    alternative_series=['House of Cards (2013)'], title='Chapter 66', series_imdb_id='tt1856010',
                    series_tvdb_id=262980, imdb_id='tt7538918', tvdb_id=6553109),
            'walking_dead_s08e07':
            Episode('The Walking Dead - 08x07 - Time for After.AMZN.WEB-DL-CasStudio.mkv', 'The Walking Dead',
                    8, 7, source='Web', streaming_service='Amazon Prime', release_group='CasStudio')
            }


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


@pytest.fixture(scope='session')
def rar(mkv):
    data_path = os.path.join('tests', 'data', 'rar')
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    downloaded_files = {
        'pwd-protected': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-psw.rar?raw=true',
        'simple': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-quick-open.rar?raw=true'
    }

    generated_files = {
        'video': [mkv['test1']],
        'videos': [mkv['test3'], mkv['test4'], mkv['test5']],
    }

    files = {}
    for filename, download_url in downloaded_files.items():
        files[filename] = os.path.join(data_path, filename) + '.rar'
        if not os.path.exists(files[filename]):
            r = requests.get(download_url)
            with open(files[filename], 'wb') as f:
                f.write(r.content)

    for filename, videos in generated_files.items():
        files[filename] = os.path.join(data_path, filename) + '.rar'
        if not os.path.exists(files[filename]):
            subprocess.call(['rar', 'a', files[filename]] + videos)

    return files
