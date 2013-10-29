# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from subliminal import Movie, Episode


MOVIES = [Movie('Man of Steel (2013)/man.of.steel.2013.720p.bluray.x264-felony.mkv', 'Man of Steel',
                release_group='felony', resolution='720p', video_codec='h264', audio_codec='DTS', imdb_id=770828,
                size=7033732714, year=2013,
                hashes={'opensubtitles': '5b8f8f4e41ccb21e', 'thesubdb': 'ad32876133355929d814457537e12dc2'})]

EPISODES = [Episode('The Big Bang Theory/Season 07/The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.mkv',
                    'The Big Bang Theory', 7, 5, release_group='DIMENSION', resolution='720p', video_codec='h264',
                    audio_codec='AC3', imdb_id=3229392, size=501910737, title='The Workplace Proximity',
                    tvdb_id=80379,
                    hashes={'opensubtitles': '6878b3ef7c1bd19e', 'thesubdb': '9dbbfb7ba81c9a6237237dae8589fccc'}),
            Episode('Game of Thrones/Season 03/Game.of.Thrones.S03E10.Mhysa.720p.WEB-DL.DD5.1.H.264-NTb.mkv',
                    'Game of Thrones', 3, 10, release_group='NTb', resolution='720p', video_codec='h264',
                    audio_codec='AC3', imdb_id=2178796, size=2142810931, title='Mhysa', tvdb_id=121361,
                    hashes={'opensubtitles': 'b850baa096976c22', 'thesubdb': 'b1f899c77f4c960b84b8dbf840d4e42d'})]
