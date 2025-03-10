# ruff: noqa: PT011, SIM115
from __future__ import annotations

import os
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from subliminal.cli import subliminal as subliminal_cli

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


def test_cli_download(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(subliminal_cli, ['download', '-l', 'en', '-p', 'podnapisi', video_name])

        assert result.exit_code == 0
        assert result.output.startswith('Collecting videos')
        assert result.output.endswith('Downloaded 1 subtitle\n')

        subtitle_filename = os.path.splitext(video_name)[0] + '.en.srt'
        assert subtitle_filename in os.listdir(td)

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
