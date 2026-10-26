from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

import pytest

from subliminal.cli.cli import subliminal as subliminal_cli

if TYPE_CHECKING:
    from pathlib import Path

    from tests.conftest import CliRunner


# Core test
pytestmark = pytest.mark.core


def test_cli_help(cli_runner: CliRunner) -> None:
    # Run cli
    result = cli_runner.run(subliminal_cli, ['--help'])

    expected = 'Usage: subliminal [OPTIONS] COMMAND [ARGS]...'
    assert result.out.startswith(expected)


def test_cli_cache(cli_runner: CliRunner) -> None:
    # Do nothing
    result = cli_runner.run(subliminal_cli, ['cache'])
    assert result.exit_code == 0
    assert result.out == 'Nothing done.\n'

    # Clean cache
    result = cli_runner.run(subliminal_cli, ['cache', '--clear-subliminal'])
    assert result.exit_code == 0
    assert result.out == "Subliminal's cache cleared.\n"


def test_cli_debug_restores_logger(cli_runner: CliRunner) -> None:
    subliminal_logger = logging.getLogger('subliminal')
    level = subliminal_logger.level
    handlers = list(subliminal_logger.handlers)

    result = cli_runner.run(subliminal_cli, ['--debug', 'cache'])
    assert result.exit_code == 0

    # Check that the log message were written and the logger restored
    assert 'INFO:subliminal' in result.err
    assert subliminal_logger.level == level
    assert subliminal_logger.handlers == handlers


def test_cli_logfile_restores_logger(cli_runner: CliRunner, tmp_path: Path) -> None:
    subliminal_logger = logging.getLogger('subliminal')
    level = subliminal_logger.level
    handlers = list(subliminal_logger.handlers)
    logfile = tmp_path / 'logs' / 'subliminal.log'

    result = cli_runner.run(subliminal_cli, ['--logfile', os.fspath(logfile), '--debug', 'cache'])
    assert result.exit_code == 0

    # Check that the log message were written and the logger restored
    assert 'subliminal.cli.cli' in logfile.read_text(encoding='utf-8')
    assert subliminal_logger.level == level
    assert subliminal_logger.handlers == handlers
    logfile.unlink()


def test_cli_restores_logger_on_error(cli_runner: CliRunner) -> None:
    subliminal_logger = logging.getLogger('subliminal')
    level = subliminal_logger.level
    handlers = list(subliminal_logger.handlers)

    # The option of the subcommand is invalid, the group callback has already configured the logger
    result = cli_runner.run(subliminal_cli, ['--debug', 'cache', '--not-an-option'])
    assert result.exit_code != 0

    # Check that the log message were written and the logger restored
    assert 'INFO:subliminal' in result.err
    assert subliminal_logger.level == level
    assert subliminal_logger.handlers == handlers
