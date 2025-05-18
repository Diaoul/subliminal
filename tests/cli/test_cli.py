from __future__ import annotations

import pytest
from click.testing import CliRunner

from subliminal.cli.cli import subliminal as subliminal_cli

# Core test
pytestmark = [
    pytest.mark.core,
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
