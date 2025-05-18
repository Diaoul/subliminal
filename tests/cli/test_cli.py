# ruff: noqa: PT011, SIM115
from __future__ import annotations

import os
from difflib import SequenceMatcher
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner
from tests.conftest import ensure

from subliminal.cli import generate_default_config
from subliminal.cli.cli import subliminal as subliminal_cli

# Core test
# Core test
pytestmark = [
    pytest.mark.core,
    pytest.mark.usefixtures('provider_manager'),
    pytest.mark.usefixtures('disabled_providers'),
]


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


@pytest.mark.parametrize('use_absolute_path', ['never', 'always', 'fallback'])
def test_cli_download_use_absolute_path(
    use_absolute_path: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: os.PathLike[str],
) -> None:
    runner = CliRunner()
    folder_name = Path(tmp_path) / 'Doctor Who S01'
    video_name = '1x1.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        full_video_path = folder_name / video_name
        ensure(full_video_path)
        monkeypatch.chdir(folder_name)

        # Need --verbose for the message to appear
        result = runner.invoke(
            subliminal_cli,
            ['download', '-l', 'en', '--use-absolute-path', use_absolute_path, '-v', '-p', 'podnapisi', video_name],
        )

        assert result.exit_code == 0
        if use_absolute_path == 'never':
            assert 'Insufficient data to process the guess' in result.output
            assert '0 video collected / 0 video ignored / 1 error' in result.output

        elif use_absolute_path == 'fallback':
            assert 'Insufficient data to process the guess' in result.output
            assert '1 video collected / 0 video ignored / 0 error' in result.output

        elif use_absolute_path == 'always':
            assert 'Insufficient data to process the guess' not in result.output
            assert '1 video collected / 0 video ignored / 0 error' in result.output


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

        subtitle_filename = os.path.splitext(video_name)[0] + '.[hi].en.srt'
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

        subtitle_filename = os.path.splitext(video_name)[0] + '.[fo].en.srt'
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


@pytest.mark.parametrize('only_force_external', [False, True])
def test_cli_download_force_external_subtitles(only_force_external: bool, tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create the video and a subtitle for this language
        ensure(video_name)
        ensure(Path(video_name).with_suffix('.en.srt'))

        cli_args = ['download', '-vv', '-l', 'en', '-p', 'gestdown', video_name]
        cli_args.append('--force-external-subtitles' if only_force_external else '--force')
        result = runner.invoke(subliminal_cli, cli_args)

        assert result.exit_code == 0
        assert '1 subtitle downloaded' in result.output


def test_cli_download_with_config(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        with open('subliminal.toml', 'w') as f:
            content = dedent(
                """\
                [default]
                # a default option
                debug = false

                [download]
                # a mandatory option is defined in the config file
                language = ["en"]
                # an option is used
                provider = ["gestdown"]
                # that will be transformed in tuple
                hearing_impaired = false

                [provider.gestdown]
                # provider options are parsed
                timeout = 30

                """
            )
            f.write(content)

        result = runner.invoke(subliminal_cli, ['--config', 'subliminal.toml', 'download', video_name])

        assert result.exit_code == 0
        assert result.output.startswith('Collecting videos')
        assert '1 subtitle' in result.output

        subtitle_filename = os.path.splitext(video_name)[0] + '.en.srt'
        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert subtitle_filename in files


def test_cli_download_with_config_with_toml_error(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        with open('subliminal.toml', 'w') as f:
            content = dedent(
                """\
                [default]
                # TOML value error: False -> false
                debug = False

                """
            )
            f.write(content)

        result = runner.invoke(
            subliminal_cli,
            ['--debug', '--config', 'subliminal.toml', 'download', '-l', 'en', video_name],
        )

        assert result.exit_code == 0
        # TOML error in the config file means that the config file is not used
        assert 'Cannot read the configuration file' in result.output


def test_cli_download_with_config_with_option_error(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path):
        with open('subliminal.toml', 'w') as f:
            content = dedent(
                """\
                [default]
                debug = false

                [download]
                # type error: should be a list
                language = "en"

                """
            )
            f.write(content)

        result = runner.invoke(
            subliminal_cli,
            ['--debug', '--config', 'subliminal.toml', 'download', video_name],
        )

        assert result.exit_code > 0
        # Error in the config file is treated as an error in the CLI arguments
        assert 'Value must be an iterable' in result.output


def test_cli_download_with_generated_config(tmp_path: os.PathLike[str]) -> None:
    runner = CliRunner()
    video_name = 'Marvels.Agents.of.S.H.I.E.L.D.S02E06.720p.HDTV.x264-KILLERS.mkv'

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        doc = generate_default_config(commented=False)
        with open('subliminal.toml', 'w') as f:
            f.write(doc)

        result = runner.invoke(subliminal_cli, ['--config', 'subliminal.toml', 'download', '-l', 'en', video_name])

        assert result.exit_code == 0
        assert result.output.startswith('Collecting videos')
        assert '1 subtitle' in result.output

        subtitle_filename = os.path.splitext(video_name)[0] + '.en.srt'
        # collect files recursively
        files = [os.fspath(p.relative_to(td)) for p in Path(td).rglob('*')]
        assert subtitle_filename in files


def test_generated_config() -> None:
    doc = generate_default_config(commented=False)
    doc_commented = generate_default_config(commented=True)

    doc_force_commented = ''.join(
        [
            f'# {line}' if line and not line.startswith(('[', '#', '\n')) else line
            for line in doc.splitlines(keepends=True)
        ]
    )

    x = SequenceMatcher(None, doc_commented, doc_force_commented)
    blocks = x.get_matching_blocks()

    assert len(blocks) == 2

    length = len(doc_commented)
    for match in blocks:
        assert match.size == 0 or match.size == length
