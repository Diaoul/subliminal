from __future__ import annotations

import contextlib
import functools
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
import requests
from babelfish import Country, Language  # type: ignore[import-untyped]

import subliminal
from subliminal.cache import region
from subliminal.extensions import RegistrableExtensionManager
from subliminal.providers.mock import MockSubtitle, mock_subtitle_provider
from subliminal.video import Episode, Movie

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
    from types import TracebackType
    from typing import TypeAlias

    import click

    OptExcInfo: TypeAlias = tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None]

TESTS_DIR = Path(__file__).parent


def ensure(path: str | os.PathLike[str], *, directory: bool = False) -> Path:
    """Create a file (or directory) at path."""
    path = Path(path)
    if directory:
        # Create a directory at path
        if not path.is_dir():
            path.mkdir(parents=True)

    else:
        # Create a directory at parent
        if not path.parent.is_dir():
            path.parent.mkdir(parents=True)
        # Create a file at path
        path.touch()
    return path


@pytest.fixture(autouse=True, scope='session')
def _configure_region() -> None:
    region.configure('dogpile.cache.null')
    region.configure = Mock()  # type: ignore[method-assign]


@pytest.fixture
def movies() -> dict[str, Movie]:
    return {
        'man_of_steel': Movie(
            os.path.join('Man of Steel (2013)', 'man.of.steel.2013.720p.bluray.x264-felony.mkv'),
            'Man of Steel',
            source='Blu-ray',
            release_group='felony',
            resolution='720p',
            video_codec='H.264',
            audio_codec='DTS',
            imdb_id='tt0770828',
            size=7033732714,
            year=2013,
            hashes={
                'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                'bsplayer': '5b8f8f4e41ccb21e',
                'opensubtitles': '5b8f8f4e41ccb21e',
                'shooter': (
                    '314f454ab464775498ae6f1f5ad813a9;fdaa8b702d8936feba2122e93ba5c44f;'
                    '0a6935e3436aa7db5597ef67a2c494e3;4d269733f36ddd49f71e92732a462fe5'
                ),
                'thesubdb': 'ad32876133355929d814457537e12dc2',
            },
        ),
        'enders_game': Movie(
            'enders.game.2013.720p.bluray.x264-sparks.mkv',
            "Ender's Game",
            source='Blu-ray',
            release_group='sparks',
            resolution='720p',
            video_codec='H.264',
            year=2013,
        ),
        'café_society': Movie(
            'Café Society.1080p.avc1.RARBG.mp4',
            'Café Society',
            year=2016,
        ),
        'interstellar': Movie(
            'Interstellar.2014.2014.1080p.BluRay.x264.YIFY.rar',
            'Interstellar',
            source='Blu-ray',
            release_group='YIFY',
            resolution='1080p',
            video_codec='H.264',
            year=2014,
        ),
        'jack_reacher_never_go_back': Movie(
            os.path.join(
                'Jack Reacher- Never Go Back (2016)', 'Jack.Reacher.Never.Go.Back.2016.1080p.WEBDL.AC3.x264-FGT.mkv'
            ),
            'Jack Reacher: Never Go Back',
            source='Web',
            release_group='FGT',
            resolution='1080p',
            video_codec='H.264',
            audio_codec='Dolby Digital',
            imdb_id='tt3393786',
            year=2016,
        ),
    }


@pytest.fixture
def episodes() -> dict[str, Episode]:
    return {
        'bbt_s07e05': Episode(
            os.path.join('The Big Bang Theory', 'Season 07', 'The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.mkv'),
            'The Big Bang Theory',
            7,
            5,
            title='The Workplace Proximity',
            year=2007,
            tvdb_id=4668379,
            series_tvdb_id=80379,
            series_imdb_id='tt0898266',
            source='HDTV',
            release_group='DIMENSION',
            resolution='720p',
            video_codec='H.264',
            audio_codec='Dolby Digital',
            frame_rate=23.976,
            imdb_id='tt3229392',
            size=501910737,
            hashes={
                'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                'bsplayer': '6878b3ef7c1bd19e',
                'opensubtitles': '6878b3ef7c1bd19e',
                'shooter': (
                    'c13e0e5243c56d280064d344676fff94;cd4184d1c0c623735f6db90841ce15fc;'
                    '3faefd72f92b63f2504269b4f484a377;8c68d1ef873afb8ba0cc9f97cbac41c1'
                ),
                'thesubdb': '9dbbfb7ba81c9a6237237dae8589fccc',
            },
        ),
        'bbt_s11e16': Episode(
            os.path.join('The Big Bang Theory', 'Season 11', 'The.Big.Bang.Theory.S11E16.720p.HDTV.x264-AVS.mkv'),
            'The Big Bang Theory',
            11,
            16,
            title='The Neonatal Nomenclature',
            year=2007,
            tvdb_id=6498115,
            series_tvdb_id=80379,
            series_imdb_id='tt0898266',
            source='HDTV',
            release_group='AVS',
            resolution='720p',
            video_codec='H.264',
            audio_codec='Dolby Digital',
            imdb_id='tt6674448',
            size=505152010,
        ),
        'got_s03e10': Episode(
            os.path.join(
                'Game of Thrones', 'Season 03', 'Game.of.Thrones.S03E10.Mhysa.720p.WEB-DL.DD5.1.H.264-NTb.mkv'
            ),
            'Game of Thrones',
            3,
            10,
            title='Mhysa',
            tvdb_id=4517466,
            series_tvdb_id=121361,
            series_imdb_id='tt0944947',
            source='Web',
            release_group='NTb',
            resolution='720p',
            video_codec='H.264',
            audio_codec='Dolby Digital',
            imdb_id='tt2178796',
            size=2142810931,
            hashes={
                'napiprojekt': '6303e7ee6a835e9fcede9fb2fb00cb36',
                'bsplayer': 'b850baa096976c22',
                'opensubtitles': 'b850baa096976c22',
                'shooter': (
                    'b02d992c04ad74b31c252bd5a097a036;ef1b32f873b2acf8f166fc266bdf011a;'
                    '82ce34a3bcee0c66ed3b26d900d31cca;78113770551f3efd1e2d4ec45898c59c'
                ),
                'thesubdb': 'b1f899c77f4c960b84b8dbf840d4e42d',
            },
        ),
        'dallas_s01e03': Episode(
            'Dallas.S01E03.mkv',
            'Dallas',
            1,
            3,
            title='Spy in the House',
            year=1978,
            tvdb_id=228224,
            imdb_id='tt0553425',
            series_tvdb_id=77092,
            series_imdb_id='tt0077000',
        ),
        'dallas_2012_s01e03': Episode(
            'Dallas.2012.S01E03.mkv',
            'Dallas',
            1,
            3,
            title='The Price You Pay',
            year=2012,
            original_series=False,
            tvdb_id=4199511,
            series_tvdb_id=242521,
            series_imdb_id='tt1723760',
            imdb_id='tt2205526',
        ),
        'marvels_agents_of_shield_s02e06': Episode(
            'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv',
            "Marvel's Agents of S.H.I.E.L.D.",
            2,
            6,
            year=2013,
            source='HDTV',
            release_group='KILLERS',
            resolution='720p',
            video_codec='H.264',
        ),
        'csi_cyber_s02e03': Episode(
            'CSI.Cyber.S02E03.hdtv-lol.mp4',
            'CSI: Cyber',
            2,
            3,
            source='HDTV',
            release_group='lol',
        ),
        'the_x_files_s10e02': Episode(
            'The.X-Files.S10E02.HDTV.x264-KILLERS.mp4',
            'The X-Files',
            10,
            2,
            source='HDTV',
            release_group='KILLERS',
            video_codec='H.264',
        ),
        'colony_s01e09': Episode(
            'Colony.S01E09.720p.HDTV.x264-KILLERS.mkv',
            'Colony',
            1,
            9,
            title='Zero Day',
            year=2016,
            tvdb_id=5463229,
            series_tvdb_id=284210,
            series_imdb_id='tt4209256',
            source='HDTV',
            release_group='KILLERS',
            resolution='720p',
            video_codec='H.264',
            imdb_id='tt4926022',
        ),
        'the_jinx_e05': Episode(
            'The.Jinx-The.Life.and.Deaths.of.Robert.Durst.E05.BDRip.x264-ROVERS.mkv',
            'The Jinx: The Life and Deaths of Robert Durst',
            1,
            5,
            year=2015,
            original_series=True,
            source='Blu-ray',
            release_group='ROVERS',
            video_codec='H.264',
        ),
        'the_100_s03e09': Episode(
            'The.100.S03E09.720p.HDTV.x264-AVS.mkv',
            'The 100',
            3,
            9,
            title='Stealing Fire',
            year=2014,
            tvdb_id=5544536,
            series_tvdb_id=268592,
            series_imdb_id='tt2661044',
            source='HDTV',
            release_group='AVS',
            resolution='720p',
            video_codec='H.264',
            imdb_id='tt4799896',
        ),
        'the fall': Episode(
            'the_fall.3x01.720p_hdtv_x264-fov.mkv',
            'The Fall',
            3,
            1,
            title='The Fall',
            year=2013,
            tvdb_id=5749493,
            series_tvdb_id=258107,
            series_imdb_id='tt2294189',
            source='HDTV',
            release_group='fov',
            resolution='720p',
            video_codec='H.264',
            imdb_id='tt4516230',
        ),
        'csi_s15e18': Episode(
            'CSI.S15E18.720p.HDTV.X264.DIMENSION.mkv',
            'CSI: Crime Scene Investigation',
            15,
            18,
            title='The End Game',
            year=2000,
            tvdb_id=5104359,
            series_tvdb_id=72546,
            series_imdb_id='tt0247082',
            source='HDTV',
            release_group='DIMENSION',
            resolution='720p',
            video_codec='H.264',
            imdb_id='tt4145952',
        ),
        'turn_s04e03': Episode(
            'Turn.S04E03.720p.HDTV.x264-AVS.mkv',
            "TURN: Washington's Spies",
            4,
            3,
            title='Blood for Blood',
            year=2014,
            tvdb_id=6124360,
            series_tvdb_id=272135,
            series_imdb_id='tt2543328',
            source='HDTV',
            release_group='AVS',
            resolution='720p',
            video_codec='H.264',
            imdb_id='tt6137686',
            alternative_series=['Turn'],
        ),
        'turn_s03e01': Episode(
            'Turn.S03E01.720p.HDTV.x264-AVS.mkv',
            "TURN: Washington's Spies",
            3,
            1,
            title='Valediction',
            year=2014,
            tvdb_id=5471384,
            series_tvdb_id=272135,
            series_imdb_id='tt2543328',
            source='HDTV',
            release_group='AVS',
            resolution='720p',
            video_codec='H.264',
            imdb_id='tt4909774',
            alternative_series=['Turn'],
        ),
        'marvels_jessica_jones_s01e13': Episode(
            'Marvels.Jessica.Jones.S01E13.720p.WEBRip.x264-2HD',
            'Marvels Jessica Jones',
            1,
            13,
            title='AKA Smile',
            year=2015,
            tvdb_id=5311273,
            series_tvdb_id=284190,
            series_imdb_id='tt2357547',
            source='Web',
            release_group='2HD',
            resolution='720p',
            video_codec='H.264',
            imdb_id='tt4162096',
            alternative_series=['Jessica Jones'],
        ),
        'fear_walking_dead_s03e10': Episode(
            'Fear.the.Walking.Dead.S03E10.1080p.WEB-DL.DD5.1.H264-RARBG',
            'Fear the Walking Dead',
            3,
            10,
            resolution='1080p',
            source='Web',
            video_codec='H.264',
            release_group='RARBG',
        ),
        'the_end_of_the_fucking_world': Episode(
            'the.end.of.the.fucking.world.s01e04.720p.web.x264-skgtv.mkv',
            'The End of the Fucking World',
            1,
            4,
            resolution='720p',
            source='Web',
            video_codec='H.264',
            release_group='skgtv',
            alternative_series=['The end of the f***ing world'],
        ),
        'Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02': Episode(
            'Marvels.Agents.of.S.H.I.E.L.D.S05E01-E02.720p.HDTV.x264-AVS',
            'Marvels.Agents.of.S.H.I.E.L.D',
            5,
            1,
            resolution='720p',
            source='HDTV',
            video_codec='H.264',
            release_group='AVS',
        ),
        'alex_inc_s01e04': Episode(
            'Alex.Inc.S01E04.HDTV.x264-SVA.mkv',
            'Alex, Inc.',
            1,
            4,
            source='HDTV',
            video_codec='H.264',
            release_group='SVA',
            year=2018,
            title='The Nanny',
            series_imdb_id='tt6466948',
            tvdb_id=6627151,
            series_tvdb_id=328635,
        ),
        'shameless_us_s08e01': Episode(
            'Shameless.US.s08e01.web.h264-convoy',
            'Shameless',
            8,
            1,
            source='Web',
            video_codec='H.264',
            country=Country('US'),
            original_series=False,
            release_group='convoy',
            year=2011,
            alternative_series=['Shameless: Hall of Shame'],
            title='We Become What We... Frank!',
            series_imdb_id='tt1586680',
            series_tvdb_id=161511,
            imdb_id='tt6347410',
            tvdb_id=6227949,
        ),
        'house_of_cards_us_s06e01': Episode(
            'house.of.cards.us.s06e01.720p.web-dl.x264',
            'House of Cards',
            6,
            1,
            source='Web',
            video_codec='H.264',
            country=Country('US'),
            year=2013,
            original_series=False,
            alternative_series=['House of Cards (2013)'],
            title='Chapter 66',
            series_imdb_id='tt1856010',
            series_tvdb_id=262980,
            imdb_id='tt7538918',
            tvdb_id=6553109,
        ),
        'walking_dead_s08e07': Episode(
            'The Walking Dead - 08x07 - Time for After.AMZN.WEB-DL-CasStudio.mkv',
            'The Walking Dead',
            8,
            7,
            source='Web',
            streaming_service='Amazon Prime',
            release_group='CasStudio',
        ),
        'suits_s06_e12': Episode(
            'Suits.S06E12.1080p.BluRay.x265-RARBG.mp4',
            'Suits',
            6,
            12,
            source='Blu-ray',
            release_group='RARBG',
            hashes={
                'napiprojekt': '32f216ee3fda2cf765e10847e7a8e90f',
            },
        ),
        'suits_s06_e13': Episode(
            'Suits.S06E13.1080p.BluRay.x265-RARBG.pl.srt',
            'Suits',
            6,
            13,
            source='Blu-ray',
            release_group='RARBG',
            hashes={
                'napiprojekt': '95bdf8ca5716166e6ad1e030a4a6b5cd',
            },
        ),
        'grimsburg_s01e01': Episode(
            'Grimsburg - S01E01 - Pilot [720p.h265.AAC.Webrip].mkv',
            'Grimsburg',
            1,
            1,
        ),
        'dw_s13e03': Episode(
            'Doctor.Who.2005.S13E03.Chapter.Three.Once.Upon.Time.1080p.AMZN.WEB-DL.DDP5.1.H.264-NOSIVID.mkv',
            'Doctor Who',
            13,
            3,
            year=2005,
        ),
        'charmed_s01e01': Episode(
            'Charmed.(2018).S01E01.Pilot.1080p.10bit.AMZN.WEB-DL.AAC5.1.HEVC-Vyndros.mkv',
            'Charmed',
            1,
            1,
            year=2018,
        ),
        'fake_show_s13e03': Episode(
            'Fake.Show.S13E03.Chapter.This.Show.Does.Not.Exist.1080p.AMZN.WEB-DL.DDP5.1.H.264-NOSIVID.mkv',
            'Fake Show',
            4,
            2,
            year=1914,
        ),
        'adam-12_s01e02': Episode(
            'Adam-12 1968 Season 1 Complete x264 [i_c]/Adam-12 S01E02 Log 141 The Color TV Bandit.mkv',
            'Adam 12',
            1,
            2,
            year=1968,
            release_group='[i_c]',
            video_codec='H.264',
        ),
    }


@pytest.fixture
def subtitles() -> dict[str, MockSubtitle]:
    return {
        'man_of_steel==empty': MockSubtitle(
            language=Language('eng'),
            subtitle_id='man_of_steel==empty',
            hearing_impaired=True,
            page_link=None,
            encoding='utf-8',
        ),
        'bbt_s07e05==empty': MockSubtitle(
            language=Language('eng'),
            subtitle_id='bbt_s07e05==empty',
            foreign_only=False,
            page_link=None,
        ),
        'bbt_s07e05==series_year_country': MockSubtitle(
            language=Language('eng'),
            subtitle_id='bbt_s07e05==series_year_country',
            hearing_impaired=False,
            page_link=None,
            parameters={
                'title': 'the big BANG theory',
                'season': 6,
                'episode': 4,
                'episode_title': None,
                'year': None,
                'release_group': '1080p',
            },
        ),
        'man_of_steel==hash': MockSubtitle(
            language=Language('eng'),
            subtitle_id='man_of_steel==hash',
            foreign_only=True,
            page_link=None,
            encoding='utf-8',
            matches={'hash'},
        ),
        'man_of_steel==imdb_id': MockSubtitle(
            language=Language('eng'),
            subtitle_id='man_of_steel==imdb_id',
            page_link=None,
            encoding='utf-8',
            matches={'imdb_id', 'country'},
            parameters={
                'title': 'Man of Steel',
                'year': 2013,
                'imdb_id': 'tt770828',
                'season': None,
                'episode': None,
            },
            release_name='man.of.steel.2013.720p.bluray.x264-felony.mkv',
        ),
        'bbt_s07e05==episode_title': MockSubtitle(
            language=Language('pol'),
            subtitle_id='bbt_s07e05==episode_title',
            page_link=None,
            encoding='utf-8',
            parameters={
                'title': None,
                'season': 7,
                'episode': 5,
                'year': None,
            },
            release_name='The.Big.Bang.Theory.S07E05.The.Workplace.Proximity.720p.HDTV.x264-DIMENSION.mkv',
        ),
    }


@pytest.fixture
def provider_manager(monkeypatch: pytest.MonkeyPatch) -> Generator[RegistrableExtensionManager, None, None]:
    """Patch the subliminal.extensions.provider_manager to use mock providers."""
    original_provider_manager = subliminal.extensions.provider_manager

    # Create a mock provider manager (namespace cannot be 'subliminal.providers')
    patched_provider_manager = RegistrableExtensionManager('subliminal.mock-providers', [])

    # Replace the provider_manager in all the module were it is imported
    subliminal.extensions.provider_manager = patched_provider_manager
    subliminal.core.provider_manager = patched_provider_manager
    subliminal.refiners.hash.provider_manager = patched_provider_manager  # type: ignore[attr-defined]

    movie_name = os.path.join('Man of Steel (2013)', 'man.of.steel.2013.720p.bluray.x264-felony.mkv')
    episode_name = os.path.join(
        'The Big Bang Theory', 'Season 07', 'The.Big.Bang.Theory.S07E05.720p.HDTV.X264-DIMENSION.mkv'
    )
    episode2_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    # Podnapisi, subtitle pool
    subtitle_pool_podnapisi = [
        {
            'language': Language.fromietf('en'),
            'subtitle_id': 'EdQo',
            'fake_content': (
                b'1\n00:00:04,254 --> 00:00:07,214\n'
                b"I'm gonna run to the store.\nI'll pick you up when you're done.\n\n"
                b'2\n00:00:07,424 --> 00:00:10,968\n'
                b'Okay. L like it a little better\nwhen you stay, but all right.\n\n'
                b'3\n00:00:11,511 --> 00:00:12,803\n'
                b'- Hey, Sheldon.\n- Hello.\n\n'
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'season', 'series', 'video_codec', 'year'},
        },
        {
            'language': Language.fromietf('hu'),
            'subtitle_id': 'ZtAW',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Elszaladok a boltba\nn\xe9h\xe1ny apr\xf3s\xe1g\xe9rt.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'\xc9rted j\xf6v\xf6k, mikor v\xe9gezt\xe9l.\n\n'
                b'3\n00:00:05,650 --> 00:00:08,390\n'
                b'J\xf3l van. \xc9n jobb szeretem,\nmikor itt maradsz, de j\xf3l van...\n\n'
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'release_group', 'season', 'series', 'source', 'video_codec', 'year'},
        },
        {
            'language': Language.fromietf('fr'),
            'subtitle_id': 'Dego',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Je vais au magasin\n\npour quelques petites choses.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'Je passerai te prendre quand tu auras fini.\n\n'
                b'3\n00:00:05,650 --> 00:00:08,390\n'
                b"D'accord. Je pr\xc3\xa9f\xc3\xa8re\nque tu restes ici, mais d'accord...\n\n"
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'season', 'series', 'source', 'year'},
        },
        {
            'language': Language.fromietf('en'),
            'subtitle_id': 'EMgo',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Say something.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'Say something else.\n\n'
            ),
            'video_name': movie_name,
            'matches': {'title', 'country', 'year'},
        },
        {
            'language': Language.fromietf('en'),
            'subtitle_id': 'Dadi',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\nGreetings.\n\n2\n00:00:04,080 --> 00:00:05,550\nSgniteerg.\n\n'
            ),
            'video_name': episode2_name,
            'matches': {'episode', 'season', 'series', 'year'},
        },
        {
            'language': Language.fromietf('ukr'),
            'subtitle_id': 'WeOa',
            'fake_content': (  # windows-1251
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'\xcf\xf0\xe8\xe2\xb3\xf2!\n\n'  # Привіт!\n\n
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'\xd2\xb3\xe2\xe8\xf0\xef!\n\n'  # Тівирп!\n\n
            ),
            'video_name': episode2_name,
            'matches': {'episode', 'season', 'series', 'year'},
        },
    ]

    ep_podnapisi = mock_subtitle_provider('Podnapisi', subtitle_pool_podnapisi)
    patched_provider_manager.register(ep_podnapisi)

    # OpenSubtitlesCom, subtitle pool
    subtitle_pool_opensubtitlescom: list[dict[str, Any]] = [
        {
            'language': Language.fromietf('en'),
            'fake_content': (
                b'1\n00:00:04,254 --> 00:00:07,214\n'
                b"I'm gonna run to the store.\nI'll pick you up when you're done.\n\n"
                b'2\n00:00:07,424 --> 00:00:10,968\n'
                b'Okay. L like it a little better\nwhen you stay, but all right.\n\n'
                b'3\n00:00:11,511 --> 00:00:12,803\n'
                b'- Hey, Sheldon.\n- Hello.\n\n'
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'season', 'series', 'video_codec', 'year'},
        },
        {
            'language': Language.fromietf('hu'),
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Elszaladok a boltba\nn\xe9h\xe1ny apr\xf3s\xe1g\xe9rt.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'\xc9rted j\xf6v\xf6k, mikor v\xe9gezt\xe9l.\n\n'
                b'3\n00:00:05,650 --> 00:00:08,390\n'
                b'J\xf3l van. \xc9n jobb szeretem,\nmikor itt maradsz, de j\xf3l van...\n\n'
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'release_group', 'season', 'series', 'source', 'video_codec', 'year'},
        },
        {
            'language': Language.fromietf('fr'),
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Je vais au magasin\n\npour quelques petites choses.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'Je passerai te prendre quand tu auras fini.\n\n'
                b'3\n00:00:05,650 --> 00:00:08,390\n'
                b"D'accord. Je pr\xc3\xa9f\xc3\xa8re\nque tu restes ici, mais d'accord...\n\n"
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'season', 'series', 'source', 'year'},
        },
        {
            'language': Language.fromietf('en'),
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Say something.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'Say something else.\n\n'
            ),
            'video_name': movie_name,
            'matches': {'title', 'country', 'year'},
        },
        {
            'language': Language.fromietf('tr'),
            # No content for testing a bad subtitle
            'fake_content': None,
            'video_name': movie_name,
            'matches': {'title', 'country', 'year'},
        },
    ]

    ep_opensubtitlescom = mock_subtitle_provider('OpenSubtitlesCom', subtitle_pool_opensubtitlescom)
    patched_provider_manager.register(ep_opensubtitlescom)

    # OpenSubtitlesComVIP, no subtitles
    ep_opensubtitlescomvip = mock_subtitle_provider('OpenSubtitlesComVip', [])
    patched_provider_manager.register(ep_opensubtitlescomvip)

    # Gestdown, subtitle pool
    subtitle_pool_gestdown = [
        {
            'language': Language.fromietf('en'),
            'subtitle_id': 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6',
            'fake_content': (
                b'1\n00:00:04,254 --> 00:00:07,214\n'
                b"I'm gonna run to the store.\nI'll pick you up when you're done.\n\n"
                b'2\n00:00:07,424 --> 00:00:10,968\n'
                b'Okay. L like it a little better\nwhen you stay, but all right.\n\n'
                b'3\n00:00:11,511 --> 00:00:12,803\n'
                b'- Hey, Sheldon.\n- Hello.\n\n'
            ),
            'video_name': episode_name,
            'matches': {'episode', 'season', 'series'},
            'fps': 24,
        },
        {
            'language': Language.fromietf('hu'),
            'subtitle_id': '12c63596-b6dd-4f1b-a55f-4eac8a94c3c3',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Elszaladok a boltba\nn\xe9h\xe1ny apr\xf3s\xe1g\xe9rt.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'\xc9rted j\xf6v\xf6k, mikor v\xe9gezt\xe9l.\n\n'
                b'3\n00:00:05,650 --> 00:00:08,390\n'
                b'J\xf3l van. \xc9n jobb szeretem,\nmikor itt maradsz, de j\xf3l van...\n\n'
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'release_group', 'season', 'series', 'source', 'video_codec', 'year'},
        },
        {
            'language': Language.fromietf('fr'),
            'subtitle_id': '90fe1369-fa0c-4154-bd04-d3d332dec587',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'Je vais au magasin\n\npour quelques petites choses.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'Je passerai te prendre quand tu auras fini.\n\n'
                b'3\n00:00:05,650 --> 00:00:08,390\n'
                b"D'accord. Je pr\xc3\xa9f\xc3\xa8re\nque tu restes ici, mais d'accord...\n\n"
            ),
            'video_name': episode_name,
            'matches': {'episode', 'season', 'series'},
        },
        {
            'language': Language.fromietf('en'),
            'subtitle_id': 'f7fe1369-4154-fa0c-bd04-d3d332de614c',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'[hearing impaired] Greetings.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'Sgniteerg.\n\n'
            ),
            'video_name': episode2_name,
            'matches': {'episode', 'season', 'series', 'year'},
            'hearing_impaired': True,
        },
        {
            'language': Language.fromietf('en'),
            'subtitle_id': 'b5fe1369-fa0c-bd04-4154-d3d332d1234e',
            'fake_content': (
                b'1\n00:00:02,090 --> 00:00:03,970\n'
                b'[foreign only] Greetings.\n\n'
                b'2\n00:00:04,080 --> 00:00:05,550\n'
                b'Sgniteerg.\n\n'
            ),
            'video_name': episode2_name,
            'matches': {'episode', 'season', 'series', 'year'},
            'foreign_only': True,
        },
    ]

    ep_gestdown = mock_subtitle_provider(
        'Gestdown',
        subtitle_pool_gestdown,
        video_types=(Episode,),
        # Mock a provider with limited language support
        languages={Language('eng'), Language('fra'), Language('hun')},
    )
    patched_provider_manager.register(ep_gestdown)

    # TVSubtitles, subtitle pool
    subtitle_pool_tvsubtitles = [
        {
            'language': Language.fromietf('en'),
            'hearing_impaired': True,
            'subtitle_id': '23329',
            'fake_content': (
                b'1\n00:00:04,254 --> 00:00:07,214\n'
                b"I'm gonna run to the store.\nI'll pick you up when you're done.\n\n"
                b'2\n00:00:07,424 --> 00:00:10,968\n'
                b'Okay. L like it a little better\nwhen you stay, but all right.\n\n'
                b'3\n00:00:11,511 --> 00:00:12,803\n'
                b'- Hey, Sheldon.\n- Hello.\n\n'
            ),
            'video_name': episode_name,
            'matches': {'country', 'episode', 'season', 'series', 'video_codec', 'year'},
            'fps': 60,
        },
    ]

    ep_tvsubtitles = mock_subtitle_provider('TVSubtitles', subtitle_pool_tvsubtitles, video_types=(Episode,))
    patched_provider_manager.register(ep_tvsubtitles)

    # Yield the mocked provider_manager
    yield patched_provider_manager

    # Recover the original provider_manager in all the modules
    subliminal.extensions.provider_manager = original_provider_manager
    subliminal.core.provider_manager = original_provider_manager
    subliminal.refiners.hash.provider_manager = original_provider_manager  # type: ignore[attr-defined]


@pytest.fixture
def disabled_providers(monkeypatch: pytest.MonkeyPatch) -> Generator[list[str], None, None]:
    original_disabled_providers = subliminal.extensions.disabled_providers

    patched_disabled_providers: list[str] = ['opensubtitlescomvip']

    # Replace disabled_providers
    subliminal.extensions.disabled_providers = patched_disabled_providers

    # Yield the mocked disabled_providers
    yield patched_disabled_providers

    # Recover the original disabled_providers
    subliminal.extensions.disabled_providers = original_disabled_providers


@pytest.fixture
def refiner_manager(monkeypatch: pytest.MonkeyPatch) -> Generator[RegistrableExtensionManager, None, None]:
    """Patch the subliminal.extensions.refiner_manager to use a mock refiner."""
    original_refiner_manager = subliminal.extensions.refiner_manager

    # Create a mock refiner manager (namespace cannot be 'subliminal.refiners')
    patched_refiner_manager = RegistrableExtensionManager('subliminal.mock-refiners', [])

    # Replace the provider_manager in all the module were it is imported
    subliminal.extensions.refiner_manager = patched_refiner_manager
    subliminal.core.refiner_manager = patched_refiner_manager

    # Yield the mocked refiner_manager
    yield patched_refiner_manager

    # Recover the original refiner_manager in all the modules
    subliminal.extensions.refiner_manager = original_refiner_manager
    subliminal.core.refiner_manager = original_refiner_manager


@pytest.fixture(scope='session')
def mkv() -> dict[str, str]:
    """Collect a dict of mkv paths.

    Run scripts/prepare_tests.py to download the files before if tests are run
    in parallel or if they are repeated to avoid multiple downloads.
    """
    data_path = TESTS_DIR / 'data' / 'mkv'
    data_path.mkdir(parents=True, exist_ok=True)

    wanted_files = [f'test{i}.mkv' for i in range(1, 9)]

    # check for missing files
    missing_files = [f for f in wanted_files if not os.path.exists(os.path.join(data_path, f))]
    if missing_files:
        # download matroska test suite
        r = requests.get(
            'https://downloads.sourceforge.net/project/matroska/test_files/matroska_test_w1_1.zip',
            timeout=20,
        )
        with ZipFile(BytesIO(r.content), 'r') as f:
            for missing_file in missing_files:
                f.extract(missing_file, data_path)

    # populate a dict with mkv files
    files = {}
    for path in os.listdir(data_path):
        if path not in wanted_files:
            continue
        name, _ = os.path.splitext(path)
        files[name] = os.fspath(data_path / path)

    return files


@pytest.fixture(scope='session')
def rar(mkv: dict[str, str]) -> dict[str, str]:
    """Collect a dict of rar paths.

    Run scripts/prepare_tests.py to download the files before if tests are run
    in parallel or if they are repeated to avoid multiple downloads.
    """
    data_path = TESTS_DIR / 'data' / 'rar'
    data_path.mkdir(parents=True, exist_ok=True)

    downloaded_files = {
        'pwd-protected': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-psw.rar?raw=true',
        'simple': 'https://github.com/markokr/rarfile/blob/master/test/files/rar5-quick-open.rar?raw=true',
    }

    generated_files = {
        'video': [mkv.get('test1')],
        'videos': [mkv.get('test3'), mkv.get('test4'), mkv.get('test5')],
    }

    files = {}
    # Add downloaded files
    for name, download_url in downloaded_files.items():
        filename = os.path.join(data_path, name + '.rar')
        if not os.path.exists(filename):
            r = requests.get(download_url, timeout=20)
            with open(filename, 'wb') as f:
                f.write(r.content)
        files[name] = filename

    # Add generated files
    for name, videos in generated_files.items():
        existing_videos = [v for v in videos if v and os.path.isfile(v)]
        filename = os.path.join(data_path, name + '.rar')
        if not os.path.exists(filename):
            try:
                subprocess.run(
                    ['rar', 'a', '-ep', filename, *existing_videos],
                    check=True,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                print('`rar` command took too long')  # noqa: T201
            except FileNotFoundError:
                # rar command line is not installed
                print('rar is not installed')  # noqa: T201
        if os.path.exists(filename):
            files[name] = filename

    return files


@dataclass
class CliResult:
    """Result of the CLI command."""

    return_value: Any
    exit_code: int
    exception: BaseException | None = None
    exc_info: OptExcInfo | None = None
    out: str = ''
    err: str = ''


class CliRunner:
    env: dict[str, str | None]
    temp_dir: str | os.PathLike[str] | None

    def __init__(
        self,
        env: Mapping[str, str | None] | None = None,
        temp_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        self.env = dict(env) if env else {}
        self.temp_dir = temp_dir

    def get_default_prog_name(self, cli: click.Command) -> str:
        """Given a command object it will return the default program name
        for it.  The default is the `name` attribute or ``"root"`` if not
        set.
        """
        return cli.name or 'root'

    def make_env(self, overrides: Mapping[str, str | None] | None = None) -> dict[str, str | None]:
        """Returns the environment overrides for invoking a script."""
        # Copy the envs
        rv = dict(self.env)
        if overrides:
            rv.update(overrides)
        return rv

    @contextlib.contextmanager
    def setenv(self, env: Mapping[str, str | None] | None = None) -> Iterator[None]:
        env = self.make_env(env)

        old_env = {}
        try:
            # Set new env variables
            for key, value in env.items():
                old_env[key] = os.environ.get(key)
                if value is None:
                    with contextlib.suppress(Exception):
                        del os.environ[key]
                else:
                    os.environ[key] = value
            yield

        finally:
            # Reset old env variables
            for key, value in old_env.items():
                if value is None:
                    with contextlib.suppress(Exception):
                        del os.environ[key]
                else:
                    os.environ[key] = value

    @contextlib.contextmanager
    def isolated_filesystem(self, temp_dir: str | os.PathLike[str] | None = None) -> Iterator[str]:
        """A context manager change directory. This isolates tests
        that affect the contents of the CWD to prevent them from
        interfering with each other.

        :param temp_dir: The given temporary directory, otherwise
            defaults to the current directory.

        """
        cwd = os.getcwd()
        dt = os.fspath(temp_dir or Path('.').resolve())
        os.chdir(dt)

        try:
            yield dt
        finally:
            os.chdir(cwd)

    def run(
        self,
        cli: click.Command,
        args: str | Sequence[str] | None = None,
        *,
        env: Mapping[str, str | None] | None = None,
        prog_name: str | None = None,
        **extra: Any,
    ) -> CliResult:
        """Run the cli and return the output."""
        exc_info: OptExcInfo | None = None
        return_value = None
        exception: BaseException | None = None
        exit_code = 0

        if isinstance(args, str):
            args = shlex.split(args)

        if prog_name is None:
            prog_name = self.get_default_prog_name(cli)

        with self.setenv(env):
            try:
                return_value = cli.main(args=args or (), prog_name=prog_name, **extra)
            except SystemExit as e:
                exc_info = sys.exc_info()
                e_code = cast('int | Any | None', e.code)

                if e_code is None:
                    e_code = 0

                if e_code != 0:
                    exception = e

                if not isinstance(e_code, int):
                    sys.stdout.write(str(e_code))
                    sys.stdout.write('\n')
                    e_code = 1

                exit_code = e_code

            except Exception as e:  # noqa: BLE001
                exception = e
                exit_code = 1
                exc_info = sys.exc_info()

        return CliResult(
            return_value=return_value,
            exit_code=exit_code,
            exception=exception,
            exc_info=exc_info,
        )


@pytest.fixture
def cli_runner(capsys: pytest.CaptureFixture[str], tmp_path: os.PathLike[str]) -> dict[str, str]:
    """Click CLI runner withoud stdin/stdout/stderr catching."""

    def with_capture(method: Callable[..., CliResult]) -> Callable[..., CliResult]:
        """Capture stdout and stderr when running the command."""

        @functools.wraps(method)
        def run_with_capture(self: CliRunner, *args: Any, **kwargs: Any) -> CliResult:
            """Run command while capturing stdout/stderr."""
            # Clear stdout/stderr buffers
            capsys.readouterr()

            # Run
            ret = method(self, *args, **kwargs)

            # Attach captured buffers
            captured = capsys.readouterr()
            ret.err = captured.err
            ret.out = captured.out

            return ret

        return run_with_capture

    @contextlib.contextmanager
    def isolated_filesystem(self: CliRunner) -> Iterator[str]:
        """A context manager that creates a temporary directory and
        changes the current working directory to it. This isolates tests
        that affect the contents of the CWD to prevent them from
        interfering with each other.

        """
        cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            yield os.fspath(tmp_path)
        finally:
            os.chdir(cwd)

    # Decorate the run method to capture stdout and stderr
    CliRunner_s = type('CliRunner_s', (CliRunner,), {})
    CliRunner_s.run = with_capture(CliRunner.run)  # type: ignore[attr-defined]

    # Change directory to the temporary path
    CliRunner_s.isolated_filesystem = isolated_filesystem  # type: ignore[attr-defined]

    return CliRunner_s()
