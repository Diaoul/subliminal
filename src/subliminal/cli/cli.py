# ruff: noqa: FBT001
"""Subliminal uses `click <https://click.palletsprojects.com>`_ to provide a :abbr:`CLI (command-line interface)`."""

from __future__ import annotations

import logging
import os
import pathlib
import warnings
from datetime import timedelta
from pathlib import Path
from typing import Any

import click
from platformdirs import PlatformDirs

from subliminal import (
    __version__,
    region,
)

from .commands import download
from .helpers import (
    MutexLock,
    options_from_providers,
    options_from_refiners,
    providers_config,
    read_configuration,
)

logger = logging.getLogger(__name__)


def configure(ctx: click.Context, param: click.Parameter | None, filename: str | os.PathLike) -> None:
    """Update :class:`click.Context` based on a configuration file."""
    config = read_configuration(filename)

    ctx.obj = config['obj']
    ctx.default_map = config['default_map']


dirs = PlatformDirs('subliminal')
cache_file = 'subliminal.dbm'
default_config_path = dirs.user_config_path / 'subliminal.toml'


@click.group(
    context_settings={'max_content_width': 100},
    epilog='Suggestions and bug reports are greatly appreciated: https://github.com/Diaoul/subliminal/',
)
@click.option(
    '-c',
    '--config',
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    default=default_config_path,
    callback=configure,
    show_default=True,
    is_eager=True,
    expose_value=False,
    show_envvar=True,
    help='Path to the TOML configuration file.',
)
@click.option(
    '--cache-dir',
    type=click.Path(writable=True, file_okay=False),
    default=dirs.user_cache_dir,
    show_default=True,
    expose_value=True,
    help='Path to the cache directory.',
)
@providers_config.option(
    '--addic7ed',
    type=click.STRING,
    nargs=2,
    metavar='USERNAME PASSWORD',
    help='DEPRECATED: Addic7ed configuration.',
)
@providers_config.option(
    '--opensubtitles',
    type=click.STRING,
    nargs=2,
    metavar='USERNAME PASSWORD',
    help='DEPRECATED: OpenSubtitles configuration.',
)
@providers_config.option(
    '--opensubtitlescom',
    type=click.STRING,
    nargs=2,
    metavar='USERNAME PASSWORD',
    help='DEPRECATED: OpenSubtitlesCom configuration.',
)
@options_from_providers
@options_from_refiners
@click.option('--debug', is_flag=True, help='Print useful information for debugging subliminal and for reporting bugs.')
@click.option(
    '--logfile',
    type=str,
    default='',
    help=(
        'If defined, record information to the specified log file. '
        'If the file already exists, new logs are appended to the file.'
    ),
)
@click.option(
    '--logfile-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    default='DEBUG',
    help='The logging level used for the log file.',
)
@click.version_option(__version__)
@click.pass_context
def subliminal(
    ctx: click.Context,
    /,
    cache_dir: str,
    debug: bool,
    logfile: os.PathLike[str] | None,
    logfile_level: str,
    addic7ed: tuple[str, str],
    opensubtitles: tuple[str, str],
    opensubtitlescom: tuple[str, str],
    **kwargs: Any,
) -> None:
    """Subtitles, faster than your thoughts."""
    # make sure to expand user
    cache_dir_path = Path(cache_dir).expanduser()
    # create cache directory
    try:
        cache_dir_path.mkdir(parents=True)
    except OSError:  # pragma: no cover
        if not cache_dir_path.is_dir():
            raise

    # configure cache
    region.configure(
        'dogpile.cache.dbm',
        expiration_time=timedelta(days=30),
        arguments={'filename': os.fspath(cache_dir_path / cache_file), 'lock_factory': MutexLock},
    )

    # Set the logger level to DEBUG in case debug or logfile is defined
    subliminal_logger = logging.getLogger('subliminal')
    subliminal_logger.setLevel(logging.DEBUG)

    # configure logging file
    if logfile:
        # make sure to expand user
        logfile_path = Path(logfile).expanduser()
        try:
            # make sure the parent directories exist
            logfile_path.parent.mkdir(parents=True)
        except OSError:  # pragma: no cover
            if not logfile_path.parent.is_dir():
                raise

        file_handler = logging.FileHandler(logfile_path)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            ),
        )
        file_handler.setLevel(logfile_level)
        subliminal_logger.addHandler(file_handler)

    # configure logging
    if debug:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        handler.setLevel(logging.DEBUG)
        subliminal_logger.addHandler(handler)
        # log about the config file
        msg = ctx.obj['debug_message']
        logger.info(msg)

    ctx.obj['debug'] = debug

    # create provider and refiner configs
    provider_configs: dict[str, dict[str, Any]] = {}
    refiner_configs: dict[str, dict[str, Any]] = {}

    for k, v in kwargs.items():
        try_split = k.split('__')
        if len(try_split) != 3:  # pragma: no cover
            click.echo(f'Unknown option: {k}={v}')
            continue
        group, plugin, key = try_split
        if group == '_provider':
            provider_configs.setdefault(plugin, {})[key] = v

        elif group == '_refiner':  # pragma: no branch
            refiner_configs.setdefault(plugin, {})[key] = v

    ctx.obj['provider_configs'] = provider_configs
    ctx.obj['refiner_configs'] = refiner_configs

    # Deprecated options
    # To be remove in next version
    deprecated_options = {
        'addic7ed': addic7ed,
        'opensubtitles': opensubtitles,
        'opensubtitlescom': opensubtitlescom,
    }
    for provider, option_value in deprecated_options.items():
        if option_value is not None:  # pragma: no cover
            msg = (
                f'option --{provider} is deprecated, use --provider.{provider}.username and '
                f'--provider.{provider}.password'
            )
            warnings.warn(msg, DeprecationWarning, stacklevel=2)

            provider_configs[provider]['username'] = option_value[0]
            provider_configs[provider]['password'] = option_value[1]


@subliminal.command()
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


# Add commands
# Download best subtitle
subliminal.add_command(download)


def cli() -> None:  # pragma: no cover
    """CLI that recognizes environment variables."""
    subliminal(auto_envvar_prefix='SUBLIMINAL')
