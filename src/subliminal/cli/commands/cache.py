# ruff: noqa: FBT001
"""Cache command."""

from __future__ import annotations

import logging
from pathlib import Path

import click

logger = logging.getLogger(__name__)

cache_file = 'subliminal.dbm'


@click.command()
@click.option(
    '--clear-subliminal',
    is_flag=True,
    help='Clear subliminal cache. Use this ONLY if your cache is corrupted or if you experience issues.',
)
@click.pass_context
def cache(ctx: click.Context, clear_subliminal: bool) -> None:
    """Cache management."""
    if clear_subliminal and ctx.parent and 'cache_dir' in ctx.parent.params:
        cache_dir_path = Path(ctx.parent.params['cache_dir'])
        for file in (cache_dir_path / cache_file).glob('*'):  # pragma: no cover
            file.unlink()
        click.echo("Subliminal's cache cleared.")
    else:
        click.echo('Nothing done.')
