from __future__ import annotations

from difflib import SequenceMatcher

import click
import pytest
import tomlkit

from subliminal.cli import generate_default_config
from subliminal.cli.generate_config import _add_value_to_table

# Core test
pytestmark = pytest.mark.core


@pytest.mark.parametrize('commented', [False, True])
def test_add_value_to_table(commented: bool) -> None:
    table = tomlkit.table()

    opt = click.Option(['--title'], default=True)

    ret = _add_value_to_table(opt, table, commented=commented)
    expected = 'title'
    assert ret == expected


@pytest.mark.parametrize('commented', [False, True])
def test_add_value_to_table_not_valid(commented: bool) -> None:
    table = tomlkit.table()

    # The default value is not a valid TOML value
    opt = click.Option(['--title'], default=[None, None], multiple=True)

    ret = _add_value_to_table(opt, table, commented=commented)
    expected = 'title'
    assert ret == expected


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
