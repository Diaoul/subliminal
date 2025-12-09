from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from subliminal.cli.cli import subliminal as subliminal_cli

if TYPE_CHECKING:
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
