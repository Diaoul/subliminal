# ruff: noqa: PT011, SIM115
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import Mock

import pytest
from babelfish import Language  # type: ignore[import-untyped]

from subliminal.core import (
    check_video,
    save_subtitles,
    scan_archive,
    scan_name,
    scan_video,
    scan_videos,
    search_external_subtitles,
)
from subliminal.exceptions import ArchiveError
from subliminal.subtitle import Subtitle
from subliminal.utils import timestamp
from subliminal.video import Episode, Movie

# Core test
pytestmark = pytest.mark.core

unix_platform = pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason='only on linux platform',
)


def test_check_video_languages(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('fra'), Language('eng')}
    assert check_video(video, languages=languages)
    video.subtitles = {Subtitle(lang) for lang in languages}
    assert not check_video(video, languages=languages)


def test_check_video_age(movies: dict[str, Movie], monkeypatch: pytest.MonkeyPatch) -> None:
    video = movies['man_of_steel']

    def fake_age(*args: Any, **kwargs: Any) -> timedelta:
        return timedelta(weeks=2)

    monkeypatch.setattr('subliminal.video.Video.get_age', fake_age)
    assert check_video(video, age=timedelta(weeks=3))
    assert not check_video(video, age=timedelta(weeks=1))


def test_check_video_undefined(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    assert check_video(video, undefined=False)
    assert check_video(video, undefined=True)
    video.subtitles = {Subtitle(Language('und'))}
    assert check_video(video, undefined=False)
    assert not check_video(video, undefined=True)


def test_search_external_subtitles(episodes: dict[str, Episode], tmpdir) -> None:
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
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


def test_search_external_subtitles_archive(movies: dict[str, Movie], tmpdir) -> None:
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
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


def test_search_external_subtitles_no_directory(
    movies: dict[str, Movie],
    tmpdir,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_name = os.path.split(movies['man_of_steel'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    tmpdir.ensure(video_name)
    monkeypatch.chdir(str(tmpdir))
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    for path in expected_subtitles:
        tmpdir.ensure(path)
    subtitles = search_external_subtitles(video_name)
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


def test_search_external_subtitles_in_directory(episodes: dict[str, Episode], tmpdir) -> None:
    video_name = episodes['marvels_agents_of_shield_s02e06'].name
    video_root = os.path.splitext(video_name)[0]
    tmpdir.ensure('tvshows', video_name)
    subtitles_directory = str(tmpdir.ensure('subtitles', dir=True))
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    tmpdir.ensure('tvshows', video_name + '.fr.srt')
    for path in expected_subtitles:
        tmpdir.ensure('subtitles', path)
    subtitles = search_external_subtitles(video_name, directory=subtitles_directory)
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


def test_scan_video_movie(movies: dict[str, Movie], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_scan_video_episode(episodes: dict[str, Episode], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
    video = episodes['bbt_s07e05']
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(video.name)
    scanned_video = scan_video(video.name)
    assert isinstance(scanned_video, Episode)
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
    assert scanned_video.series == video.series
    assert scanned_video.season == video.season
    assert scanned_video.episode == video.episode
    assert scanned_video.title is None
    assert scanned_video.year is None
    assert scanned_video.tvdb_id is None


def test_scan_video_path_does_not_exist(movies: dict[str, Movie]) -> None:
    with pytest.raises(ValueError) as excinfo:
        scan_video(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path does not exist'


def test_scan_video_invalid_extension(movies: dict[str, Movie], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(str(tmpdir))
    movie_name = os.path.splitext(movies['man_of_steel'].name)[0] + '.mp3'
    tmpdir.ensure(movie_name)
    with pytest.raises(ValueError) as excinfo:
        scan_video(movie_name)
    assert str(excinfo.value) == "'.mp3' is not a valid video extension"


def test_scan_video_broken(mkv: dict[str, str], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_scan_video_movie_name(movies: dict[str, Movie], mkv: dict[str, str]) -> None:
    video = movies['man_of_steel']
    path = mkv['test1']
    scanned_video = scan_video(path, name=video.name)
    assert isinstance(scanned_video, Movie)
    # from real file
    assert scanned_video.name == path
    assert scanned_video.size != 0
    # from replacement name
    assert scanned_video.source == video.source
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year


def test_scan_video_episode_name(episodes: dict[str, Episode], mkv: dict[str, str]) -> None:
    video = episodes['bbt_s07e05']
    path = mkv['test1']
    scanned_video = scan_video(path, name=video.name)
    assert isinstance(scanned_video, Episode)
    # from real file
    assert scanned_video.name == path
    assert scanned_video.size != 0
    # from replacement name
    assert scanned_video.source == video.source
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.series == video.series
    assert scanned_video.season == video.season
    assert scanned_video.episode == video.episode
    assert scanned_video.title is None
    assert scanned_video.year is None
    assert scanned_video.tvdb_id is None


def test_scan_video_movie_name_path_does_not_exist(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    path = 'video_but_not_a_path.avi'
    scanned_video = scan_name(path, name=video.name)
    assert isinstance(scanned_video, Movie)
    # from real file
    assert scanned_video.name == path
    # from replacement name
    assert scanned_video.source == video.source
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size is None
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year


def test_scan_archive_invalid_extension(movies: dict[str, Movie], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(str(tmpdir))
    movie_name = os.path.splitext(movies['interstellar'].name)[0] + '.mp3'
    tmpdir.ensure(movie_name)
    with pytest.raises(ArchiveError) as excinfo:
        scan_archive(movie_name)
    assert str(excinfo.value) == "'.mp3' is not a valid archive"


def test_scan_videos_path_does_not_exist(movies: dict[str, Movie]) -> None:
    with pytest.raises(ValueError) as excinfo:
        scan_videos(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path does not exist'


def test_scan_videos_path_is_not_a_directory(
    movies: dict[str, Movie],
    tmpdir,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(str(tmpdir))
    tmpdir.ensure(movies['man_of_steel'].name)
    with pytest.raises(ValueError) as excinfo:
        scan_videos(movies['man_of_steel'].name)
    assert str(excinfo.value) == 'Path is not a directory'


def test_scan_videos(movies: dict[str, Movie], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
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
    kwargs: dict[str, Any] = {'name': None}
    scan_video_calls = [
        ((os.path.join('movies', movies['man_of_steel'].name),), kwargs),
        ((os.path.join('movies', movies['enders_game'].name),), kwargs),
    ]
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]

    # scan_archive calls
    kwargs = {'name': None}
    scan_archive_calls = [((os.path.join('movies', movies['interstellar'].name),), kwargs)]
    mock_scan_archive.assert_has_calls(scan_archive_calls, any_order=True)  # type: ignore[arg-type]


def test_scan_videos_age(movies: dict[str, Movie], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
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
    kwargs: dict[str, Any] = {'name': None}
    scan_video_calls = [((os.path.join('movies', movies['man_of_steel'].name),), kwargs)]
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]


def test_save_subtitles(movies: dict[str, Movie], tmpdir, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_save_subtitles_single_directory_encoding(movies: dict[str, Movie], tmpdir) -> None:
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


@unix_platform
def test_scan_archive_with_one_video(rar: dict[str, str], mkv: dict[str, str]) -> None:
    if 'video' not in rar:
        return
    rar_file = rar['video']
    actual = scan_archive(rar_file)

    assert actual.name == os.path.join(os.path.split(rar_file)[0], mkv['test1'])


@unix_platform
def test_scan_archive_with_multiple_videos(rar: dict[str, str], mkv: dict[str, str]) -> None:
    if 'video' not in rar:
        return
    rar_file = rar['videos']
    actual = scan_archive(rar_file)

    assert actual.name == os.path.join(os.path.split(rar_file)[0], mkv['test5'])


@unix_platform
def test_scan_archive_with_no_video(rar: dict[str, str]) -> None:
    with pytest.raises(ArchiveError) as excinfo:
        scan_archive(rar['simple'])
    assert excinfo.value.args == ('No video in archive',)


@unix_platform
def test_scan_bad_archive(mkv: dict[str, str]) -> None:
    with pytest.raises(ArchiveError) as excinfo:
        scan_archive(mkv['test1'])
    assert excinfo.value.args == ("'.mkv' is not a valid archive",)


@unix_platform
def test_scan_password_protected_archive(rar: dict[str, str]) -> None:
    with pytest.raises(ArchiveError) as excinfo:
        scan_archive(rar['pwd-protected'])
    assert excinfo.value.args == ('Rar requires a password',)
