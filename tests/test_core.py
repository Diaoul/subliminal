from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from subliminal.core import (
    scan_name,
    scan_path,
    scan_video,
    scan_video_or_archive,
    scan_videos,
)
from subliminal.utils import timestamp
from subliminal.video import Episode, Movie
from tests.conftest import ensure

if TYPE_CHECKING:
    from pathlib import Path

# Core test
pytestmark = pytest.mark.core


def test_scan_video_movie(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = movies['man_of_steel']
    monkeypatch.chdir(tmp_path)
    ensure(tmp_path / video.name)
    scanned_video = scan_video(video.name)
    assert isinstance(scanned_video, Movie)
    assert scanned_video.name == video.name
    assert scanned_video.source == video.source
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 0
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year
    assert not scanned_video.external_ids


def test_scan_video_episode(episodes: dict[str, Episode], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = episodes['bbt_s07e05']
    monkeypatch.chdir(tmp_path)
    ensure(tmp_path / video.name)
    scanned_video = scan_video(video.name)
    assert isinstance(scanned_video, Episode)
    assert scanned_video.name == video.name
    assert scanned_video.source == video.source
    assert scanned_video.release_group == video.release_group
    assert scanned_video.resolution == video.resolution
    assert scanned_video.video_codec == video.video_codec
    assert scanned_video.audio_codec is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 0
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.series == video.series
    assert scanned_video.season == video.season
    assert scanned_video.episode == video.episode
    assert scanned_video.title is None
    assert scanned_video.year is None
    assert not scanned_video.external_ids


def test_scan_video_path_does_not_exist(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    path = movies['man_of_steel'].name
    with pytest.raises(ValueError, match='Path does not exist'):
        scan_video(path)

    with pytest.raises(ValueError, match='Path does not exist'):
        scan_video_or_archive(path)


def test_scan_video_invalid_extension(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    movie_name = os.path.splitext(movies['man_of_steel'].name)[0] + '.mp3'
    ensure(tmp_path / movie_name)
    with pytest.raises(ValueError, match=re.escape("'.mp3' is not a valid video extension")):
        scan_video(movie_name)


def test_scan_video_broken(mkv: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    broken_path = 'test1.mkv'
    with open(mkv['test1'], 'rb') as original, (tmp_path / broken_path).open('wb') as broken:
        broken.write(original.read(512))
    monkeypatch.chdir(tmp_path)
    scanned_video = scan_video(broken_path)
    assert type(scanned_video) is Movie
    assert scanned_video.name == str(broken_path)
    assert scanned_video.source is None
    assert scanned_video.release_group is None
    assert scanned_video.resolution is None
    assert scanned_video.video_codec is None
    assert scanned_video.audio_codec is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 512
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == 'test1'
    assert scanned_video.year is None
    assert not scanned_video.external_ids


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
    assert scanned_video.hashes == {}
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year
    assert not scanned_video.external_ids


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
    assert scanned_video.hashes == {}
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.series == video.series
    assert scanned_video.season == video.season
    assert scanned_video.episode == video.episode
    assert scanned_video.title is None
    assert scanned_video.year is None
    assert not scanned_video.external_ids


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
    assert scanned_video.hashes == {}
    assert scanned_video.size is None
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year
    assert not scanned_video.external_ids


def test_scan_path(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import subliminal

    mock = Mock()
    monkeypatch.setattr(subliminal.core, 'scan_video_or_archive', mock)

    video = movies['interstellar']
    ensure(tmp_path / video.name)
    monkeypatch.chdir(tmp_path)

    # Non-existing path
    scan_path(f'non-existing-{video.name}')
    mock.assert_not_called()

    # Existing path
    scan_path(video.name)
    mock.assert_called_once()


def test_scan_videos_path_does_not_exist(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match='Path does not exist'):
        scan_videos(movies['man_of_steel'].name)


def test_scan_videos_path_is_not_a_directory(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = movies['man_of_steel']
    monkeypatch.chdir(tmp_path)
    ensure(tmp_path / video.name)
    with pytest.raises(ValueError, match='Path is not a directory'):
        scan_videos(movies['man_of_steel'].name)


def test_scan_videos(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    man_of_steel = ensure(tmp_path / 'movies' / movies['man_of_steel'].name)
    ensure(tmp_path / 'movies' / '.private' / 'sextape.mkv')
    ensure(tmp_path / 'movies' / '.hidden_video.mkv')
    ensure(tmp_path / 'movies' / 'Sample' / 'video.mkv')
    ensure(tmp_path / 'movies' / 'sample.mkv')
    ensure(tmp_path / 'movies' / movies['enders_game'].name)
    ensure(tmp_path / 'movies' / movies['interstellar'].name)
    ensure(tmp_path / 'movies' / (os.path.splitext(movies['enders_game'].name)[0] + '.nfo'))
    ensure(tmp_path / 'movies' / 'watched', directory=True)
    watched_path = tmp_path / 'movies' / 'watched' / os.path.basename(movies['man_of_steel'].name)
    watched_path.symlink_to(man_of_steel)

    # mock scan_video and scan_archive with the correct types
    mock_video = Mock(subtitle_languages=set())
    mock_scan_video = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_video', mock_scan_video)
    mock_scan_archive = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_archive', mock_scan_archive)
    monkeypatch.chdir(tmp_path)
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
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

    # scan_archive calls
    kwargs = {'name': None}
    scan_archive_calls = [((os.path.join('movies', movies['interstellar'].name),), kwargs)]
    mock_scan_archive.assert_has_calls(scan_archive_calls, any_order=True)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_scan_videos_age(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ensure(tmp_path / 'movies' / movies['man_of_steel'].name)
    ts = timestamp(datetime.now(timezone.utc) - timedelta(days=10))
    os.utime(ensure(tmp_path / 'movies' / movies['enders_game'].name), (ts, ts))

    # mock scan_video and scan_archive with the correct types
    mock_video = Mock(subtitle_languages=set())
    mock_scan_video = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_video', mock_scan_video)
    mock_scan_archive = Mock(return_value=mock_video)
    monkeypatch.setattr('subliminal.core.scan_archive', mock_scan_archive)
    monkeypatch.chdir(tmp_path)
    videos = scan_videos('movies', age=timedelta(days=7))

    # general asserts
    assert len(videos) == 1
    assert mock_scan_video.call_count == 1
    assert mock_scan_archive.call_count == 0

    # scan_video calls
    kwargs: dict[str, Any] = {'name': None}
    scan_video_calls = [((os.path.join('movies', movies['man_of_steel'].name),), kwargs)]
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
