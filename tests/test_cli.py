# ruff: noqa: PT011, SIM115
from __future__ import annotations

import os
from textwrap import dedent

import pytest
from click.testing import CliRunner
from vcr import VCR

from subliminal.cli import subliminal

# Core test
pytestmark = pytest.mark.core


vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'cli')),
)


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(subliminal, ['--help'])
    assert result.exit_code == 0
    assert result.output.startswith('Usage: subliminal [OPTIONS] COMMAND [ARGS]...')


def test_cli_cache() -> None:
    runner = CliRunner()

    # Do nothing
    result = runner.invoke(subliminal, ['cache'])
    assert result.exit_code == 0
    assert result.output == 'Nothing done.\n'

    # Clean cache
    result = runner.invoke(subliminal, ['cache', '--clear-subliminal'])
    assert result.exit_code == 0
    assert result.output == "Subliminal's cache cleared.\n"


@vcr.use_cassette
def test_cli_download(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    movie_name = 'The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4'

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(subliminal, ['download', '-l', 'en', '-p', 'podnapisi', movie_name])

        assert result.exit_code == 0
        assert result.output.startswith('Collecting videos')
        assert result.output.endswith('Downloaded 1 subtitle\n')

        subtitle_filename = os.path.splitext(movie_name)[0] + '.en.srt'
        assert subtitle_filename in os.listdir(td)

        content = open(subtitle_filename, encoding='utf-8-sig').read()

    expected = dedent(
        """\
        1
        00:00:02,370 --> 00:00:04,304
        I'm just gonna run to the
        store and get a few things.

        2
        00:00:04,306 --> 00:00:05,339
        I'll pick you up
        when you're done.
        """
    )
    assert content.startswith(expected)
