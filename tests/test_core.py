# ruff: noqa: PT011, SIM115
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import Mock

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from subliminal.core import (
    AsyncProviderPool,
    ProviderPool,
    check_video,
    download_best_subtitles,
    download_subtitles,
    list_subtitles,
    refine,
    save_subtitles,
    scan_archive,
    scan_video,
    scan_videos,
    search_external_subtitles,
)
from subliminal.extensions import provider_manager
from subliminal.providers.tvsubtitles import TVsubtitlesSubtitle
from subliminal.score import episode_scores
from subliminal.subtitle import Subtitle
from subliminal.utils import timestamp
from subliminal.video import Episode, Movie
from vcr import VCR  # type: ignore[import-untyped]

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'core')),
)


unix_platform = pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason='only on linux platform',
)


@pytest.fixture()
def _mock_providers(monkeypatch):
    for provider in provider_manager:
        monkeypatch.setattr(provider.plugin, 'initialize', Mock())
        monkeypatch.setattr(provider.plugin, 'list_subtitles', Mock(return_value=[provider.name]))
        monkeypatch.setattr(provider.plugin, 'download_subtitle', Mock())
        monkeypatch.setattr(provider.plugin, 'terminate', Mock())


def test_provider_pool_get_keyerror():
    pool = ProviderPool()
    with pytest.raises(KeyError):
        pool['de7cidda']


def test_provider_pool_del_keyerror():
    pool = ProviderPool()
    with pytest.raises(KeyError):
        del pool['addic7ed']


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_iter():
    pool = ProviderPool()
    assert len(list(pool)) == 0
    pool['tvsubtitles']
    assert len(list(pool)) == 1


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_list_subtitles_provider(episodes):
    pool = ProviderPool()
    subtitles = pool.list_subtitles_provider('tvsubtitles', episodes['bbt_s07e05'], {Language('eng')})
    assert subtitles == ['tvsubtitles']  # type: ignore[comparison-overlap]
    assert provider_manager['tvsubtitles'].plugin.initialize.called
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_list_subtitles(episodes):
    pool = ProviderPool()
    subtitles = pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
    assert sorted(subtitles) == ['gestdown', 'opensubtitles', 'opensubtitlescom', 'podnapisi', 'tvsubtitles']  # type: ignore[type-var,comparison-overlap]
    for provider in subtitles:
        assert provider_manager[provider].plugin.initialize.called
        assert provider_manager[provider].plugin.list_subtitles.called


@pytest.mark.usefixtures('_mock_providers')
def test_async_provider_pool_list_subtitles_provider(episodes):
    pool = AsyncProviderPool()
    subtitles = pool.list_subtitles_provider_tuple('tvsubtitles', episodes['bbt_s07e05'], {Language('eng')})
    assert subtitles == ('tvsubtitles', ['tvsubtitles'])  # type: ignore[comparison-overlap]
    assert provider_manager['tvsubtitles'].plugin.initialize.called
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called


@pytest.mark.usefixtures('_mock_providers')
def test_async_provider_pool_list_subtitles(episodes):
    pool = AsyncProviderPool()
    subtitles = pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
    assert sorted(subtitles) == ['gestdown', 'opensubtitles', 'opensubtitlescom', 'podnapisi', 'tvsubtitles']  # type: ignore[type-var,comparison-overlap]
    for provider in subtitles:
        assert provider_manager[provider].plugin.initialize.called
        assert provider_manager[provider].plugin.list_subtitles.called


def test_check_video_languages(movies):
    video = movies['man_of_steel']
    languages = {Language('fra'), Language('eng')}
    assert check_video(video, languages=languages)
    video.subtitle_languages = languages
    assert not check_video(video, languages=languages)


def test_check_video_age(movies, monkeypatch):
    video = movies['man_of_steel']
    monkeypatch.setattr('subliminal.video.Video.age', timedelta(weeks=2))
    assert check_video(video, age=timedelta(weeks=3))
    assert not check_video(video, age=timedelta(weeks=1))


def test_check_video_undefined(movies):
    video = movies['man_of_steel']
    assert check_video(video, undefined=False)
    assert check_video(video, undefined=True)
    video.subtitle_languages = {Language('und')}
    assert check_video(video, undefined=False)
    assert not check_video(video, undefined=True)


def test_search_external_subtitles(episodes, tmpdir):
    video_name = os.path.split(episodes['bbt_s07e05'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    video_path = str(tmpdir.ensure(video_name))
    expected_subtitles = {
        video_name + '.srt': Language('und'),
        video_root + '.srt': Language('und'),
        video_root + '.en.srt': Language('eng'),
        video_name + '.fra.srt': Language('fra'),
        video_root + '.pt-BR.srt': Language('por', 'BR'),
        video_name + '.sr_cyrl.sub': Language('srp', script='Cyrl'),
        video_name + '.re.srt': Language('und'),
        video_name + '.something.srt': Language('und'),
    }
    tmpdir.ensure(os.path.split(episodes['got_s03e10'].name)[1] + '.srt')
    for path in expected_subtitles:
        tmpdir.ensure(path)
    subtitles = search_external_subtitles(video_path)
    assert subtitles == expected_subtitles


def test_search_external_subtitles_archive(movies, tmpdir):
    video_name = os.path.split(movies['interstellar'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    video_path = str(tmpdir.ensure(video_name))
    expected_subtitles = {
        video_name + '.srt': Language('und'),
        video_root + '.srt': Language('und'),
        video_root + '.en.srt': Language('eng'),
        video_name + '.fra.srt': Language('fra'),
        video_root + '.pt-BR.srt': Language('por', 'BR'),
        video_name + '.sr_cyrl.sub': Language('srp', script='Cyrl'),
        video_name + '.something.srt': Language('und'),
    }
    tmpdir.ensure(os.path.split(movies['interstellar'].name)[1] + '.srt')
    for path in expected_subtitles:
        tmpdir.ensure(path)
    subtitles = search_external_subtitles(video_path)
    assert subtitles == expected_subtitles


def test_search_external_subtitles_no_directory(movies, tmpdir, monkeypatch):
    video_name = os.path.split(movies['man_of_steel'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    tmpdir.ensure(video_name)
    monkeypatch.chdir(str(tmpdir))
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    for path in expected_subtitles:
        tmpdir.ensure(path)
    subtitles = search_external_subtitles(video_name)
    assert subtitles == expected_subtitles


def test_search_external_subtitles_in_directory(episodes, tmpdir):
    video_name = episodes['marvels_agents_of_shield_s02e06'].name
    video_root = os.path.splitext(video_name)[0]
    tmpdir.ensure('tvshows', video_name)
    subtitles_directory = str(tmpdir.ensure('subtitles', dir=True))
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    tmpdir.ensure('tvshows', video_name + '.fr.srt')
    for path in expected_subtitles:
        tmpdir.ensure('subtitles', path)
    subtitles = search_external_subtitles(video_name, directory=subtitles_directory)
    assert subtitles == expected_subtitles


def test_scan_video_movie(movies, tmpdir, monkeypatch):
    video = movies['man_of_steel']
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(video.name)
    scanned_video = scan_video(video.name)
    assert isinstance(scanned_video, Movie)
    assert scanned_video.name == video.name
    assert scanned_video.source == video.source
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 0
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year


def test_scan_video_episode(episodes, tmpdir, monkeypatch):
    video = episodes['bbt_s07e05']
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(video.name)
    scanned_video = scan_video(video.name)
    assert isinstance(scanned_video, Episode)
    assert scanned_video.name, video.name
    assert scanned_video.source == video.source
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 0
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.series == video.series
    assert scanned_video.season == video.season
    assert scanned_video.episode == video.episode
    assert scanned_video.title is None
    assert scanned_video.year is None
    assert scanned_video.tvdb_id is None


def test_refine_video_metadata(mkv):
    scanned_video = scan_video(mkv['test5'])
    refine(scanned_video, episode_refiners=('metadata',), movie_refiners=('metadata',))
    assert type(scanned_video) is Movie
    assert scanned_video.name == mkv['test5']
    assert scanned_video.source is None
    assert scanned_video.release_group is None
    assert scanned_video.resolution is None
    assert scanned_video.video_codec == 'H.264'
    assert scanned_video.audio_codec == 'AAC'
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {
        'opensubtitlescom': '49e2530ea3bd0d18',
        'opensubtitles': '49e2530ea3bd0d18',
    }
    assert scanned_video.size == 31762747
    assert scanned_video.subtitle_languages == {
        Language('spa'),
        Language('deu'),
        Language('jpn'),
        Language('und'),
        Language('ita'),
        Language('fra'),
        Language('hun'),
    }
    assert scanned_video.title == 'test5'
    assert scanned_video.year is None


def test_scan_video_path_does_not_exist(movies):
    with pytest.raises(ValueError) as excinfo:
        scan_video(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path does not exist'


def test_scan_video_invalid_extension(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    movie_name = os.path.splitext(movies['man_of_steel'].name)[0] + '.mp3'
    tmpdir.ensure(movie_name)
    with pytest.raises(ValueError) as excinfo:
        scan_video(movie_name)
    assert str(excinfo.value) == "'.mp3' is not a valid video extension"


def test_scan_video_broken(mkv, tmpdir, monkeypatch):
    broken_path = 'test1.mkv'
    with open(mkv['test1'], 'rb') as original, tmpdir.join(broken_path).open('wb') as broken:
        broken.write(original.read(512))
    monkeypatch.chdir(str(tmpdir))
    scanned_video = scan_video(broken_path)
    assert type(scanned_video) is Movie
    assert scanned_video.name == str(broken_path)
    assert scanned_video.source is None
    assert scanned_video.release_group is None
    assert scanned_video.resolution is None
    assert scanned_video.video_codec is None
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 512
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == 'test1'
    assert scanned_video.year is None


def test_scan_archive_invalid_extension(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    movie_name = os.path.splitext(movies['interstellar'].name)[0] + '.mp3'
    tmpdir.ensure(movie_name)
    with pytest.raises(ValueError) as excinfo:
        scan_archive(movie_name)
    assert str(excinfo.value) == "'.mp3' is not a valid archive"


def test_scan_videos_path_does_not_exist(movies):
    with pytest.raises(ValueError) as excinfo:
        scan_videos(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path does not exist'


def test_scan_videos_path_is_not_a_directory(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(movies['man_of_steel'].name)
    with pytest.raises(ValueError) as excinfo:
        scan_videos(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path is not a directory'


def test_scan_videos(movies, tmpdir, monkeypatch):
    man_of_steel = tmpdir.ensure('movies', movies['man_of_steel'].name)
    tmpdir.ensure('movies', '.private', 'sextape.mkv')
    tmpdir.ensure('movies', '.hidden_video.mkv')
    tmpdir.ensure('movies', 'Sample', 'video.mkv')
    tmpdir.ensure('movies', 'sample.mkv')
    tmpdir.ensure('movies', movies['enders_game'].name)
    tmpdir.ensure('movies', movies['interstellar'].name)
    tmpdir.ensure('movies', os.path.splitext(movies['enders_game'].name)[0] + '.nfo')
    tmpdir.ensure('movies', 'watched', dir=True)
    watched_path = tmpdir.join('movies', 'watched', os.path.split(movies['man_of_steel'].name)[1])
    if hasattr(watched_path, 'mksymlinkto'):
        watched_path.mksymlinkto(man_of_steel)

    # mock scan_video and scan_archive with the correct types
    mock_video = Mock(subtitle_languages=set())
    mock_scan_video = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_video', mock_scan_video)
    mock_scan_archive = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_archive', mock_scan_archive)
    monkeypatch.chdir(str(tmpdir))
    videos = scan_videos('movies')

    # general asserts
    assert len(videos) == 3
    assert mock_scan_video.call_count == 2
    assert mock_scan_archive.call_count == 1

    # scan_video calls
    kwargs: dict[str, Any] = {}
    scan_video_calls = [
        ((os.path.join('movies', movies['man_of_steel'].name),), kwargs),
        ((os.path.join('movies', movies['enders_game'].name),), kwargs),
    ]
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]

    # scan_archive calls
    kwargs = {}
    scan_archive_calls = [((os.path.join('movies', movies['interstellar'].name),), kwargs)]
    mock_scan_archive.assert_has_calls(scan_archive_calls, any_order=True)  # type: ignore[arg-type]


def test_scan_videos_age(movies, tmpdir, monkeypatch):
    tmpdir.ensure('movies', movies['man_of_steel'].name)
    tmpdir.ensure('movies', movies['enders_game'].name).setmtime(
        timestamp(datetime.now(timezone.utc) - timedelta(days=10))
    )

    # mock scan_video and scan_archive with the correct types
    mock_video = Mock(subtitle_languages=set())
    mock_scan_video = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_video', mock_scan_video)
    mock_scan_archive = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_archive', mock_scan_archive)
    monkeypatch.chdir(str(tmpdir))
    videos = scan_videos('movies', age=timedelta(days=7))

    # general asserts
    assert len(videos) == 1
    assert mock_scan_video.call_count == 1
    assert mock_scan_archive.call_count == 0

    # scan_video calls
    kwargs: dict[str, Any] = {}
    scan_video_calls = [((os.path.join('movies', movies['man_of_steel'].name),), kwargs)]
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_movie(movies):
    video = movies['man_of_steel']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitlesvip', 'tvsubtitles'):
        assert not provider_manager[name].plugin.list_subtitles.called

    for name in ('opensubtitles', 'opensubtitlescom', 'podnapisi'):
        assert provider_manager[name].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[movies['man_of_steel']]) == ['opensubtitles', 'opensubtitlescom', 'podnapisi']  # type: ignore[type-var,comparison-overlap]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_episode(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('heb')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitlesvip'):
        assert not provider_manager[name].plugin.list_subtitles.called

    for name in ('gestdown', 'opensubtitles', 'opensubtitlescom', 'podnapisi', 'tvsubtitles'):
        assert provider_manager[name].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == [  # type: ignore[type-var,comparison-overlap]
        'gestdown',
        'opensubtitles',
        'opensubtitlescom',
        'podnapisi',
        'tvsubtitles',
    ]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_providers(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages, providers=['opensubtitles'])

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitlesvip', 'podnapisi', 'tvsubtitles'):
        assert not provider_manager[name].plugin.list_subtitles.called

    for name in ('opensubtitles',):
        assert provider_manager[name].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == ['opensubtitles']  # type: ignore[type-var,comparison-overlap]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_episode_no_hash(episodes):
    video = episodes['dallas_s01e03']
    languages = {Language('eng'), Language('heb')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitlesvip'):
        assert not provider_manager[name].plugin.list_subtitles.called

    for name in ('gestdown', 'opensubtitles', 'podnapisi', 'tvsubtitles'):
        assert provider_manager[name].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['dallas_s01e03']]) == [  # type: ignore[type-var,comparison-overlap]
        'gestdown',
        'opensubtitles',
        'opensubtitlescom',
        'podnapisi',
        'tvsubtitles',
    ]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_no_language(episodes):
    video = episodes['dallas_s01e03']
    languages = {Language('eng')}
    video.subtitle_languages = languages

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitles', 'opensubtitlesvip', 'podnapisi', 'tvsubtitles'):
        assert not provider_manager[name].plugin.list_subtitles.called

    # test result
    assert len(subtitles) == 0


@pytest.mark.usefixtures('_mock_providers')
def test_download_subtitles():
    subtitles = [
        TVsubtitlesSubtitle(
            language=Language('por'),
            subtitle_id='261077',
            page_link=None,
            series='Game of Thrones',
            season=3,
            episode=10,
            year=None,
            rip='1080p.BluRay',
            release='DEMAND',
        )
    ]

    download_subtitles(subtitles)

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitles', 'opensubtitlesvip', 'podnapisi'):
        assert not provider_manager[name].plugin.download_subtitle.called

    for name in ('tvsubtitles',):
        assert provider_manager[name].plugin.download_subtitle.called


@pytest.mark.integration()
@vcr.use_cassette
def test_download_best_subtitles(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    providers = ['gestdown', 'podnapisi']
    expected_subtitles = {
        ('podnapisi', 'EdQo'),
        ('podnapisi', 'Dego'),
        # ('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6'),
        # ('gestdown', '90fe1369-fa0c-4154-bd04-d3d332dec587'),
    }

    subtitles = download_best_subtitles({video}, languages, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 2
    assert {(s.provider_name, s.id) for s in subtitles[video]} == expected_subtitles


@pytest.mark.integration()
@vcr.use_cassette
def test_download_best_subtitles_min_score(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    providers = ['gestdown']

    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 0


def test_download_best_subtitles_no_language(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    video.subtitle_languages = languages
    providers = ['gestdown']

    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], providers=providers)

    assert len(subtitles) == 0


def test_download_best_subtitles_undefined(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('und')}
    video.subtitle_languages = languages
    providers = ['gestdown']

    subtitles = download_best_subtitles(
        {video}, languages, min_score=episode_scores['hash'], only_one=True, providers=providers
    )

    assert len(subtitles) == 0


@pytest.mark.integration()
@vcr.use_cassette
def test_download_best_subtitles_only_one(episodes):
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('por', 'BR')}
    providers = ['gestdown', 'podnapisi']
    # expected_subtitles = {('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6')}
    expected_subtitles = {('podnapisi', 'EdQo')}

    subtitles = download_best_subtitles({video}, languages, only_one=True, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 1
    assert {(s.provider_name, s.id) for s in subtitles[video]} == expected_subtitles


def test_save_subtitles(movies, tmpdir, monkeypatch):
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(movies['man_of_steel'].name)
    subtitle_no_content = Subtitle(Language('eng'), '')
    subtitle = Subtitle(Language('fra'), '')
    subtitle.content = b'Some content'
    subtitle_other = Subtitle(Language('fra'), '')
    subtitle_other.content = b'Some other content'
    subtitle_pt_br = Subtitle(Language('por', 'BR'), '')
    subtitle_pt_br.content = b'Some brazilian content'
    subtitles = [subtitle_no_content, subtitle, subtitle_other, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles)

    # subtitle without content is skipped
    path = os.path.join(str(tmpdir), os.path.splitext(movies['man_of_steel'].name)[0] + '.en.srt')
    assert not os.path.exists(path)

    # first subtitle with language is saved
    path = os.path.join(str(tmpdir), os.path.splitext(movies['man_of_steel'].name)[0] + '.fr.srt')
    assert os.path.exists(path)
    assert open(path, 'rb').read() == b'Some content'

    # ietf language in path
    path = os.path.join(str(tmpdir), os.path.splitext(movies['man_of_steel'].name)[0] + '.pt-BR.srt')
    assert os.path.exists(path)
    assert open(path, 'rb').read() == b'Some brazilian content'


def test_save_subtitles_single_directory_encoding(movies, tmpdir):
    subtitle = Subtitle(Language('jpn'), '')
    subtitle.content = 'ハローワールド'.encode('shift-jis')
    subtitle_pt_br = Subtitle(Language('por', 'BR'), '')
    subtitle_pt_br.content = b'Some brazilian content'
    subtitles = [subtitle, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles, single=True, directory=str(tmpdir), encoding='utf-8')

    # first subtitle only and correctly encoded
    path = os.path.join(str(tmpdir), os.path.splitext(os.path.split(movies['man_of_steel'].name)[1])[0] + '.srt')
    assert os.path.exists(path)
    assert open(path, encoding='utf-8').read() == 'ハローワールド'


@pytest.mark.integration()
@vcr.use_cassette
def test_download_bad_subtitle(movies):
    pool = ProviderPool()
    subtitles = pool.list_subtitles_provider('opensubtitles', movies['man_of_steel'], {Language('eng')})
    assert len(subtitles) >= 1
    subtitle = subtitles[0]
    subtitle.subtitle_id = ''

    pool.download_subtitle(subtitle)

    assert subtitle.content is None
    assert subtitle.is_valid() is False


@unix_platform
def test_scan_archive_with_one_video(rar, mkv):
    if 'video' not in rar:
        return
    rar_file = rar['video']
    actual = scan_archive(rar_file)

    assert actual.name == os.path.join(os.path.split(rar_file)[0], mkv['test1'])


@unix_platform
def test_scan_archive_with_multiple_videos(rar, mkv):
    if 'video' not in rar:
        return
    rar_file = rar['videos']
    actual = scan_archive(rar_file)

    assert actual.name == os.path.join(os.path.split(rar_file)[0], mkv['test5'])


@unix_platform
def test_scan_archive_with_no_video(rar):
    with pytest.raises(ValueError) as excinfo:
        scan_archive(rar['simple'])
    assert excinfo.value.args == ('No video in archive',)


@unix_platform
def test_scan_bad_archive(mkv):
    with pytest.raises(ValueError) as excinfo:
        scan_archive(mkv['test1'])
    assert excinfo.value.args == ("'.mkv' is not a valid archive",)


@unix_platform
def test_scan_password_protected_archive(rar):
    with pytest.raises(ValueError) as excinfo:
        scan_archive(rar['pwd-protected'])
    assert excinfo.value.args == ('Rar requires a password',)
