# ruff: noqa: PT011, SIM115
from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from subliminal.cli import subliminal as subliminal_cli
from tests.conftest import ensure

if TYPE_CHECKING:
    from collections.abc import Generator

# Core test
# Core test
pytestmark = [
    pytest.mark.core,
    pytest.mark.usefixtures('provider_manager'),
    pytest.mark.usefixtures('disabled_providers'),
]


@pytest.fixture
def _mock_save_subtitles() -> Generator[None, None, None]:
    import subliminal.cli

    original_save_subtitles = subliminal.cli.save_subtitles

    # Use mock
    subliminal.cli.save_subtitles = Mock()

    yield

    # Restore value
    subliminal.cli.save_subtitles = original_save_subtitles


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(subliminal_cli, ['--help'])
    assert result.exit_code == 0
    assert result.output.startswith('Usage: subliminal [OPTIONS] COMMAND [ARGS]...')


def test_cli_cache() -> None:
    runner = CliRunner()

    # Do nothing
    result = runner.invoke(subliminal_cli, ['cache'])
    assert result.exit_code == 0
    assert result.output == 'Nothing done.\n'

    # Clean cache
    result = runner.invoke(subliminal_cli, ['cache', '--clear-subliminal'])
    assert result.exit_code == 0
    assert result.output == "Subliminal's cache cleared.\n"


def test_cli_download_wrong_language(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(subliminal_cli, ['download', '-l', 'zzz', '-p', 'podnapisi', video_name])

        assert result.exit_code > 0


def test_cli_download_guessing_error(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = '1x1.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Need --verbose for the message to appear
        result = runner.invoke(subliminal_cli, ['download', '-l', 'en', '--verbose', '-p', 'podnapisi', video_name])

        assert result.exit_code == 0
        assert 'Insufficient data to process the guess' in result.output


def test_cli_download_age(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Wrong age
        result = runner.invoke(subliminal_cli, ['download', '-l', 'en', '--age', '1h2y', '-p', 'podnapisi', video_name])

        assert result.exit_code > 0

        # Right age
        result = runner.invoke(subliminal_cli, ['download', '-l', 'en', '--age', '3w6h', '-p', 'podnapisi', video_name])

        assert result.exit_code == 0


def test_cli_download_debug(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(subliminal_cli, ['--debug', 'download', '-l', 'en', '-p', 'podnapisi', video_name])

        assert result.exit_code == 0
        assert 'DEBUG' in result.output


def test_cli_download_logfile(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    logfile = 'subliminal.log'
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            subliminal_cli,
            ['--logfile', logfile, 'download', '-l', 'en', '-p', 'podnapisi', video_name],
        )

        assert result.exit_code == 0
        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert logfile in files

        log_content = open(logfile).read()
        assert 'DEBUG' in log_content


@pytest.mark.parametrize('count', [0, 1, 2])
@pytest.mark.parametrize('video_type', ['movie', 'episode'])
def test_cli_download_verbose(count: int, video_type: str, tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    if video_type == 'episode':
        video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'
    else:  # elif video_type == 'movie':
        video_name = os.path.join('Man of Steel (2013)', 'man.of.steel.2013.720p.bluray.x264-felony.mkv')

    verbose = '' if not count else f'-{"v" * count}'
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Ensure that the file exists, otherwise the movie errors
        ensure(video_name)
        result = runner.invoke(subliminal_cli, ['download', verbose, '-l', 'en', '-p', 'podnapisi', video_name])

        assert result.exit_code == 0
        if count > 0:
            assert '1 subtitle downloaded' in result.output
        else:
            assert '1 subtitle downloaded' not in result.output
        if count > 1:
            assert 'English subtitle from podnapisi' in result.output
        else:
            assert 'English subtitle from podnapisi' not in result.output


def test_cli_download_no_provider(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            subliminal_cli,
            ['download', '-vv', '-l', 'en', '-p', 'podnapisi', '-P', 'podnapisi', video_name],
        )

        assert result.exit_code == 0
        assert 'No provider was selected to download subtitles.' in result.output


def test_cli_download(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(subliminal_cli, ['download', '-l', 'en', '-p', 'podnapisi', video_name])

        assert result.exit_code == 0
        assert result.output.startswith('Collecting videos')
        assert result.output.endswith('Downloaded 1 subtitle\n')

        subtitle_filename = os.path.splitext(video_name)[0] + '.en.srt'
        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert subtitle_filename in files

        content = open(subtitle_filename, encoding='utf-8-sig').read()

    expected = dedent(
        """\
        1
        00:00:02,090 --> 00:00:03,970
        Greetings.

        2
        00:00:04,080 --> 00:00:05,550
        Sgniteerg.

        """
    )
    assert content.startswith(expected)


def test_cli_download_directory(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    movie_name = os.path.join('Man of Steel (2013)', 'man.of.steel.2013.720p.bluray.x264-felony.mkv')
    episode_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        ensure(movie_name)
        ensure(episode_name)

        result = runner.invoke(subliminal_cli, ['download', '-l', 'en', '-p', 'podnapisi', '.'])

        assert result.exit_code == 0
        assert result.output.startswith('Collecting videos')
        assert result.output.endswith('Downloaded 2 subtitles\n')

        subtitle_movie_filename = os.path.splitext(movie_name)[0] + '.en.srt'
        subtitle_episode_filename = os.path.splitext(episode_name)[0] + '.en.srt'

        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert subtitle_movie_filename in files
        assert subtitle_episode_filename in files


@pytest.mark.parametrize(
    ('encoding', 'real_encoding'),
    [
        ('', 'windows-1251'),
        ('""', 'windows-1251'),
        ("''", 'windows-1251'),
        (None, 'utf-8'),
        ('utf-8', 'utf-8'),
    ],
)
def test_cli_download_encoding(encoding: str | None, real_encoding: str, tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    cli_args = ['download', '-l', 'ukr', '-p', 'podnapisi', video_name]
    if encoding is not None:
        cli_args.extend([f'--encoding={encoding}'])

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(subliminal_cli, cli_args)

        assert result.exit_code == 0
        subtitle_filename = os.path.splitext(video_name)[0] + '.uk.srt'
        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert subtitle_filename in files

        content = open(subtitle_filename, encoding=real_encoding).read()

    expected = dedent(
        """\
        1
        00:00:02,090 --> 00:00:03,970
        Привіт!

        2
        00:00:04,080 --> 00:00:05,550
        Тівирп!

        """
    )
    assert content.startswith(expected)


def test_cli_download_subtitle_format(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(
            subliminal_cli,
            ['download', '-l', 'en', '-p', 'podnapisi', video_name, '--subtitle-format', 'ass'],
        )

        assert result.exit_code == 0
        subtitle_filename = os.path.splitext(video_name)[0] + '.en.ass'
        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert subtitle_filename in files

        content = open(subtitle_filename).read()

    expected = dedent(
        """\
        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        Dialogue: 0,0:00:02.09,0:00:03.97,Default,,0,0,0,,Greetings.
        Dialogue: 0,0:00:04.08,0:00:05.55,Default,,0,0,0,,Sgniteerg.
        """
    )
    assert content.endswith(expected)


def test_cli_download_hearing_impaired(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    cli_args = ['download', '-l', 'en', '--hearing-impaired', '--language-type-suffix', '-p', 'gestdown', video_name]
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(subliminal_cli, cli_args)

        assert result.exit_code == 0
        assert result.output.endswith('Downloaded 1 subtitle\n')

        subtitle_filename = os.path.splitext(video_name)[0] + '.hi.en.srt'
        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert subtitle_filename in files

        content = open(subtitle_filename, encoding='utf-8-sig').read()

    assert '[hearing impaired]' in content


def test_cli_download_foreign_only(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    cli_args = ['download', '-l', 'en', '--foreign-only', '--language-type-suffix', '-p', 'gestdown', video_name]
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(subliminal_cli, cli_args)

        assert result.exit_code == 0
        assert result.output.endswith('Downloaded 1 subtitle\n')

        subtitle_filename = os.path.splitext(video_name)[0] + '.fo.en.srt'
        assert subtitle_filename in os.listdir(td)

        content = open(subtitle_filename, encoding='utf-8-sig').read()

    assert '[foreign only]' in content


@pytest.mark.parametrize('video_exists', [False, True])
def test_cli_download_ignored_video(video_exists: bool, tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create the video and a subtitle for this language
        if video_exists:
            ensure(video_name)
        ensure(Path(video_name).with_suffix('.en.srt'))
        result = runner.invoke(subliminal_cli, ['download', '-vv', '-l', 'en', '-p', 'gestdown', video_name])

        assert result.exit_code == 0
        assert '1 video ignored' in result.output


@pytest.mark.parametrize('force', [False, True])
@pytest.mark.parametrize('force_external', [False, True])
def test_cli_download_force_external_subtitles(force: bool, force_external: bool, tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create the video and a subtitle for this language
        ensure(video_name)
        ensure(Path(video_name).with_suffix('.en.srt'))

        cli_args = ['download', '-vv', '-l', 'en', '-p', 'gestdown', video_name]
        if force:
            cli_args.append('--force')
        if force_external:
            cli_args.append('--force-external-subtitles')
        result = runner.invoke(subliminal_cli, cli_args)

        assert result.exit_code == 0
        match = '1 video ignored' if not force and not force_external else '1 subtitle downloaded'
        assert match in result.output
