from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from textwrap import dedent
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest
from babelfish import Language  # type: ignore[import-untyped]

from subliminal.core import (
    check_video,
    save_subtitles,
    scan_name,
    scan_path,
    scan_video,
    scan_video_or_archive,
    scan_videos,
    search_external_subtitles,
)
from subliminal.subtitle import Subtitle
from subliminal.utils import timestamp
from subliminal.video import Episode, Movie
from tests.conftest import ensure

if TYPE_CHECKING:
    from pathlib import Path

# Core test
pytestmark = pytest.mark.core


def test_check_video_languages(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('fra'), Language('eng')}
    assert check_video(video, languages=languages)
    video.subtitles = [Subtitle(lang) for lang in languages]
    assert not check_video(video, languages=languages)


def test_check_video_age(movies: dict[str, Movie], monkeypatch: pytest.MonkeyPatch) -> None:
    video = movies['man_of_steel']
    monkeypatch.setattr('subliminal.video.Video.age', timedelta(weeks=2))
    assert check_video(video, age=timedelta(weeks=3))
    assert not check_video(video, age=timedelta(weeks=1))


def test_check_video_undefined(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    assert check_video(video, undefined=False)
    assert check_video(video, undefined=True)
    video.subtitles = [Subtitle(Language('und'))]
    assert check_video(video, undefined=False)
    assert not check_video(video, undefined=True)


def test_search_external_subtitles(episodes: dict[str, Episode], tmp_path: Path) -> None:
    video_name = os.path.split(episodes['bbt_s07e05'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    video_path = ensure(tmp_path / video_name)
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
    ensure(tmp_path / (os.path.basename(episodes['got_s03e10'].name) + '.srt'))
    for path in expected_subtitles:
        ensure(tmp_path / path)
    subtitles = search_external_subtitles(video_path)
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


def test_search_external_subtitles_archive(movies: dict[str, Movie], tmp_path: Path) -> None:
    video_name = os.path.split(movies['interstellar'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    video_path = ensure(tmp_path / video_name)
    expected_subtitles = {
        video_name + '.srt': Language('und'),
        video_root + '.srt': Language('und'),
        video_root + '.en.srt': Language('eng'),
        video_name + '.fra.srt': Language('fra'),
        video_root + '.pt-BR.srt': Language('por', 'BR'),
        video_name + '.sr_cyrl.sub': Language('srp', script='Cyrl'),
        video_name + '.something.srt': Language('und'),
    }
    ensure(tmp_path / (os.path.split(movies['interstellar'].name)[1] + '.srt'))
    for path in expected_subtitles:
        ensure(tmp_path / path)
    subtitles = search_external_subtitles(video_path)
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


def test_search_external_subtitles_no_directory(
    movies: dict[str, Movie],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video_name = os.path.split(movies['man_of_steel'].name)[1]
    video_root = os.path.splitext(video_name)[0]
    ensure(tmp_path / video_name)
    monkeypatch.chdir(tmp_path)
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    for path in expected_subtitles:
        ensure(tmp_path / path)
    subtitles = search_external_subtitles(video_name)
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


def test_search_external_subtitles_in_directory(episodes: dict[str, Episode], tmp_path: Path) -> None:
    video_name = episodes['marvels_agents_of_shield_s02e06'].name
    video_root = os.path.splitext(video_name)[0]
    ensure(tmp_path / 'tvshows' / video_name)
    subtitles_directory = ensure(tmp_path / 'subtitles', directory=True)
    expected_subtitles = {video_name + '.srt': Language('und'), video_root + '.en.srt': Language('eng')}
    ensure(tmp_path / 'tvshows' / (video_name + '.fr.srt'))
    for path in expected_subtitles:
        ensure(tmp_path / 'subtitles' / path)
    subtitles = search_external_subtitles(video_name, directory=subtitles_directory)
    subtitle_languages = {path: subtitle.language for path, subtitle in subtitles.items()}
    assert subtitle_languages == expected_subtitles


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
    assert scanned_video.imdb_id is None
    assert scanned_video.hashes == {}
    assert scanned_video.size == 0
    assert scanned_video.subtitle_languages == set()
    assert scanned_video.title == video.title
    assert scanned_video.year == video.year


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
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]

    # scan_archive calls
    kwargs = {'name': None}
    scan_archive_calls = [((os.path.join('movies', movies['interstellar'].name),), kwargs)]
    mock_scan_archive.assert_has_calls(scan_archive_calls, any_order=True)  # type: ignore[arg-type]


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
    mock_scan_video.assert_has_calls(scan_video_calls, any_order=True)  # type: ignore[arg-type]


def test_save_subtitles(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    ensure(tmp_path / movies['man_of_steel'].name)
    subtitle_no_content = Subtitle(Language('eng'), '')
    subtitle = Subtitle(Language('fra'), '')
    subtitle.set_content(b'Some content')
    subtitle_other = Subtitle(Language('fra'), '')
    subtitle_other.set_content(b'Some other content')
    subtitle_pt_br = Subtitle(Language('por', 'BR'), '')
    subtitle_pt_br.set_content(b'Some brazilian content')
    subtitles = [subtitle_no_content, subtitle, subtitle_other, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles)

    # subtitle without content is skipped
    path = tmp_path / (os.path.splitext(movies['man_of_steel'].name)[0] + '.en.srt')
    assert not path.is_file()

    # first subtitle with language is saved
    path = tmp_path / (os.path.splitext(movies['man_of_steel'].name)[0] + '.fr.srt')
    assert path.is_file()
    assert path.open('rb').read() == b'Some content'

    # ietf language in path
    path = tmp_path / (os.path.splitext(movies['man_of_steel'].name)[0] + '.pt-BR.srt')
    assert path.is_file()
    assert path.open('rb').read() == b'Some brazilian content'


def test_save_subtitles_single_directory_encoding(movies: dict[str, Movie], tmp_path: Path) -> None:
    subtitle = Subtitle(Language('jpn'), '')
    subtitle.set_content('ハローワールド'.encode('shift-jis'))
    subtitle_pt_br = Subtitle(Language('por', 'BR'), '')
    subtitle_pt_br.set_content(b'Some brazilian content')
    subtitles = [subtitle, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles, single=True, directory=os.fspath(tmp_path), encoding='utf-8')

    # first subtitle only and correctly encoded
    path = tmp_path / (os.path.splitext(os.path.split(movies['man_of_steel'].name)[1])[0] + '.srt')
    assert path.is_file()
    assert path.open(encoding='utf-8').read() == 'ハローワールド'


def test_save_subtitles_convert(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = movies['man_of_steel']

    monkeypatch.chdir(tmp_path)
    ensure(tmp_path / video.name)

    text = dedent(
        """\
        [Script Info]
        WrapStyle: 0
        ScaledBorderAndShadow: yes
        Collisions: Normal
        ScriptType: v4.00+

        [V4+ Styles]
        Format: Name, Fontname, Fontsize, PrimaryColour
        Style: Default,Arial,20,&H00FFFFFF

        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        Dialogue: 0,0:00:49.54,0:00:52.96,Default,,0,0,0,,Tłumaczenie:\\Nsinu6
        Dialogue: 0,0:02:11.08,0:02:12.88,Default,,0,0,0,,/Nie rozumiecie?
        """
    )
    subtitle = Subtitle(Language('pol'), '')
    subtitle.set_content(text.encode('utf-8'))
    subtitles = [subtitle]

    save_subtitles(video, subtitles, single=True, subtitle_format='srt')

    # converted to srt
    srt_text = dedent(
        """\
        1
        00:00:49,540 --> 00:00:52,960
        Tłumaczenie:
        sinu6

        2
        00:02:11,080 --> 00:02:12,880
        /Nie rozumiecie?

        """
    )
    path = tmp_path / (os.path.splitext(video.name)[0] + '.srt')
    assert path.is_file()
    assert path.open(encoding='utf-8').read() == srt_text
