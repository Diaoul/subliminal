# ruff: noqa: FBT001
"""Subliminal uses `click <https://click.palletsprojects.com>`_ to provide a :abbr:`CLI (command-line interface)`."""

from __future__ import annotations

import logging
import os
import pathlib
import re
import traceback
import warnings
from collections import defaultdict
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import tomlkit
from babelfish import Error as BabelfishError  # type: ignore[import-untyped]
from babelfish import Language
from click_option_group import GroupedOption, OptionGroup
from dogpile.cache.backends.file import AbstractFileLock
from dogpile.util.readwrite_lock import ReadWriteMutex
from platformdirs import PlatformDirs

from subliminal import (
    AsyncProviderPool,
    Episode,
    Movie,
    Video,
    __version__,
    check_video,
    compute_score,
    get_scores,
    provider_manager,
    refine,
    refiner_manager,
    region,
    save_subtitles,
)
from subliminal.core import (
    ARCHIVE_EXTENSIONS,
    collect_video_filepaths,
    scan_path,
    search_external_subtitles,
)
from subliminal.exceptions import GuessingError
from subliminal.extensions import get_default_providers, get_default_refiners
from subliminal.utils import get_parameters_from_signature, merge_extend_and_ignore_unions

if TYPE_CHECKING:
    from collections.abc import Callable, MutableMapping, Sequence, Set

    from subliminal.utils import Parameter


logger = logging.getLogger(__name__)


class MutexLock(AbstractFileLock):  # pragma: no cover
    """:class:`MutexLock` is a thread-based rw lock based on :class:`dogpile.core.ReadWriteMutex`."""

    def __init__(self, filename: str) -> None:
        self.mutex = ReadWriteMutex()  # type: ignore[no-untyped-call]

    def acquire_read_lock(self, wait: bool) -> bool:
        """Acquire a reader lock."""
        ret = self.mutex.acquire_read_lock(wait)  # type: ignore[no-untyped-call]
        return wait or bool(ret)

    def acquire_write_lock(self, wait: bool) -> bool:
        """Acquire a writer lock."""
        ret = self.mutex.acquire_write_lock(wait)  # type: ignore[no-untyped-call]
        return wait or bool(ret)

    def release_read_lock(self) -> None:
        """Release a reader lock."""
        return self.mutex.release_read_lock()  # type: ignore[no-untyped-call,no-any-return]

    def release_write_lock(self) -> None:
        """Release a writer lock."""
        return self.mutex.release_write_lock()  # type: ignore[no-untyped-call,no-any-return]


class LanguageParamType(click.ParamType):
    """:class:`~click.ParamType` for languages that returns a :class:`~babelfish.language.Language`."""

    name = 'language'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> Language:
        """Convert ietf language to :class:`~babelfish.language.Language`."""
        try:
            return Language.fromietf(value)
        except BabelfishError:
            self.fail(f'{value} is not a valid language', param, ctx)  # pragma: no cover


LANGUAGE = LanguageParamType()


class AgeParamType(click.ParamType):
    """:class:`~click.ParamType` for age strings that returns a :class:`~datetime.timedelta`.

    An age string is in the form `number + identifier` with possible identifiers:

        * ``w`` for weeks
        * ``d`` for days
        * ``h`` for hours

    The form can be specified multiple times but only with that identifier ordering. For example:

        * ``1w2d4h`` for 1 week, 2 days and 4 hours
        * ``2w`` for 2 weeks
        * ``3w6h`` for 3 weeks and 6 hours
    """

    name = 'age'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> timedelta:
        """Convert an age string to :class:`~datetime.timedelta`."""
        match = re.match(r'^(?:(?P<weeks>\d+?)w)?(?:(?P<days>\d+?)d)?(?:(?P<hours>\d+?)h)?$', value)
        if not match:
            self.fail(f'{value} is not a valid age', param, ctx)

        return timedelta(**{k: int(v) for k, v in match.groupdict(0).items()})


PROVIDERS_OPTIONS_TEMPLATE = '_{ext}__{plugin}__{key}'
PROVIDERS_OPTIONS_CLI_TEMPLATE = '--{ext}.{plugin}.{key}'
PROVIDERS_OPTIONS_ENVVAR_TEMPLATE = 'SUBLIMINAL_{ext}_{plugin}_{key}'


def read_configuration(filename: str | os.PathLike) -> dict[str, dict[str, Any]]:
    """Read a configuration file."""
    filename = pathlib.Path(filename).expanduser()
    msg = ''
    toml_dict: MutableMapping[str, Any] = {}
    if filename.is_file():
        try:
            with open(filename, 'rb') as f:
                toml_dict = tomlkit.load(f)
        except tomlkit.exceptions.TOMLKitError:
            tb = traceback.format_exc()
            msg = f'Cannot read the configuration file at {os.fspath(filename)!r}:\n{tb}'
        else:
            msg = f'Using configuration file at {os.fspath(filename)!r}'
    else:
        msg = f'Not using any configuration file, not a file {os.fspath(filename)!r}'

    # make options for subliminal from [default] section
    options = toml_dict.setdefault('default', {})

    # make cache options
    options['cache'] = toml_dict.setdefault('cache', {})

    # make download options
    download_dict = toml_dict.setdefault('download', {})
    # handle language types
    for lt in ('hearing_impaired', 'foreign_only'):
        # if an option was defined in the config file, make it a tuple, the expected type
        if lt in download_dict and (isinstance(download_dict[lt], bool) or download_dict[lt] is None):
            download_dict[lt] = (download_dict[lt],)

    # remove the provider and refiner lists to select, extend and ignore
    provider_lists = {
        'select': download_dict.pop('provider', []),
        'extend': download_dict.pop('extend_provider', []),
        'ignore': download_dict.pop('ignore_provider', []),
    }
    refiner_lists = {
        'select': download_dict.pop('refiner', []),
        'extend': download_dict.pop('extend_refiner', []),
        'ignore': download_dict.pop('ignore_refiner', []),
    }
    options['download'] = download_dict

    # make provider and refiner options
    for ext in ('provider', 'refiner'):
        for plugin, d in toml_dict.setdefault(ext, {}).items():
            if not isinstance(d, Mapping):  # pragma: no cover
                continue
            for k, v in d.items():
                name = PROVIDERS_OPTIONS_TEMPLATE.format(ext=ext, plugin=plugin, key=k)
                options[name] = v

    return {
        'obj': {
            'debug_message': msg,
            'provider_lists': provider_lists,
            'refiner_lists': refiner_lists,
        },
        'default_map': options,
    }


def configure(ctx: click.Context, param: click.Parameter | None, filename: str | os.PathLike) -> None:
    """Update :class:`click.Context` based on a configuration file."""
    config = read_configuration(filename)

    ctx.obj = config['obj']
    ctx.default_map = config['default_map']


def generate_default_config(*, compact: bool = True, commented: bool = True) -> str:
    """Generate a default configuration file.

    :param compact: if True, generate a compact configuration without newlines between options.
    :param commented: if True, all the options are commented out.
    """

    def add_value_to_table(opt: click.Option, table: tomlkit.items.Table, *, name: str | None = None) -> str | None:
        """Add a value to a TOML table."""
        if opt.name is None:  # pragma: no cover
            return None
        # Override option name
        opt_name = name if name is not None else opt.name

        table.add(tomlkit.comment((opt.help or opt_name).capitalize()))
        # table.add(tomlkit.comment(f'{opt_name} = {opt.default}'))
        if opt.default is not None:
            if not commented:
                table.add(opt_name, opt.default)
            else:
                # Generate the entry in a dumb table
                dumb = tomlkit.table()
                dumb.add(opt_name, opt.default)
                # Add the string to the final table as a comment
                table.add(tomlkit.comment(dumb.as_string().strip('\n')))
        else:
            table.add(tomlkit.comment(f'{opt_name} = '))

        return opt_name

    # Create TOML document
    doc = tomlkit.document()
    doc.add(tomlkit.comment('Subliminal default configuration file'))
    doc.add(tomlkit.nl())

    # Get the options to the main command line
    default = tomlkit.table()
    for opt in subliminal.params:
        if not isinstance(opt, click.Option) or isinstance(opt, GroupedOption):
            continue
        if opt.name is None:  # pragma: no cover
            continue
        if opt.name.startswith(('__', 'fake')):
            continue
        if opt.name in ['version', 'config']:
            continue
        # Add key=value to table
        add_value_to_table(opt, default)
        if not compact:  # pragma: no cover
            default.add(tomlkit.nl())
    # Adding the table to the document
    doc.add('default', default)
    if not compact:  # pragma: no cover
        doc.add(tomlkit.nl())

    # Get subcommands
    for command_name, command in subliminal.commands.items():
        # Get the options for each subcommand
        com_table = tomlkit.table()
        # We need to keep track of duplicated options
        existing_options: Set[str] = set()
        for opt in command.params:
            if opt.name is None:  # pragma: no cover
                continue
            if not isinstance(opt, click.Option):
                continue
            if opt.name in existing_options:
                # Duplicated option
                continue
            # Add key=value to table
            opt_name = add_value_to_table(opt, com_table)
            if opt_name is not None:
                existing_options.add(opt_name)
            if not compact:  # pragma: no cover
                com_table.add(tomlkit.nl())

        # Adding the table to the document
        doc.add(command_name, com_table)
        if not compact:  # pragma: no cover
            doc.add(tomlkit.nl())

    # Add providers and refiners options
    for class_type in ['provider', 'refiner']:
        provider_options = [
            o
            for o in subliminal.params
            if isinstance(o, click.Option) and o.name and o.name.startswith(f'_{class_type}__')
        ]
        provider_tables: dict[str, tomlkit.items.Table] = {}
        for opt in provider_options:
            if opt.name is None:  # pragma: no cover
                continue
            _, provider, opt_name = opt.name.split('__')
            provider_table = provider_tables.setdefault(provider, tomlkit.table())
            if opt.name in provider_table:  # pragma: no cover
                # Duplicated option
                continue

            # Add key=value to table
            add_value_to_table(opt, provider_table, name=opt_name)
            if not compact:  # pragma: no cover
                provider_table.add(tomlkit.nl())

        # Adding the table to the document
        parent_provider_table = tomlkit.table()
        for provider, table in provider_tables.items():
            parent_provider_table.add(provider, table)
            if not compact:  # pragma: no cover
                doc.add(tomlkit.nl())
        doc.add(class_type, parent_provider_table)
        if not compact:  # pragma: no cover
            doc.add(tomlkit.nl())

    return tomlkit.dumps(doc)


def plural(quantity: int, name: str, *, bold: bool = True, **kwargs: Any) -> str:
    """Format a quantity with plural."""
    return '{} {}{}'.format(
        click.style(str(quantity), bold=bold, **kwargs),
        name,
        's' if quantity > 1 else '',
    )


def scan_video_path(
    filepath: str | os.PathLike[str],
    *,
    name: str | None = None,
    absolute_path: bool = False,
    verbose: int = 0,
    debug: bool = False,
) -> Video | None:
    """Try to scan a video at path, with a option to convert to absolute path before."""
    exists = os.path.exists(filepath)
    # Take the absolute path, and only if the path exists
    if absolute_path and exists:
        filepath = os.path.abspath(filepath)
    # Used for print
    filepath_or_name = f'{filepath} ({name})' if name else filepath

    try:
        video = scan_path(filepath, name=name)

    except GuessingError as e:
        logger.exception(
            'Cannot guess information about %s %s',
            'path' if exists else 'non-existing path',
            filepath_or_name,
        )
        # Show a simple error message
        if verbose > 0:  # pragma: no cover
            # new line was already added with debug
            if not debug:
                click.echo()
            click.secho(e, fg='yellow')
        return None

    except ValueError:  # pragma: no cover
        logger.exception(
            'Unexpected error while collecting %s %s',
            'path' if exists else 'non-existing path',
            filepath_or_name,
        )
        return None

    return video


AGE = AgeParamType()

PROVIDER = click.Choice(['ALL', *sorted(provider_manager.names())])

REFINER = click.Choice(['ALL', *sorted(refiner_manager.names())])

dirs = PlatformDirs('subliminal')
cache_file = 'subliminal.dbm'
default_config_path = dirs.user_config_path / 'subliminal.toml'

providers_config = OptionGroup('Providers configuration')
refiners_config = OptionGroup('Refiners configuration')


def options_from_managers(
    group_name: str,
    options: Mapping[str, Sequence[Parameter]],
    group: OptionGroup | None = None,
) -> Callable[[Callable], Callable]:
    """Add click options dynamically from providers and refiners keyword arguments."""
    click_option = click.option if group is None else group.option

    def decorator(f: Callable) -> Callable:
        for plugin_name, opt_params in options.items():
            for opt in reversed(opt_params):
                name = opt['name']
                # CLI option has dots, variable has double-underscores to differentiate
                # with simple underscore in provider name or keyword argument.
                param_decls = (
                    PROVIDERS_OPTIONS_CLI_TEMPLATE.format(ext=group_name, plugin=plugin_name, key=name),
                    PROVIDERS_OPTIONS_TEMPLATE.format(ext=group_name, plugin=plugin_name, key=name),
                )
                # Setting the default value also decides on the type
                attrs = {
                    'default': opt['default'],
                    'help': opt['desc'],
                    'show_default': True,
                    'show_envvar': True,
                    'envvar': PROVIDERS_OPTIONS_ENVVAR_TEMPLATE.format(
                        ext=group_name.upper(),
                        plugin=plugin_name.upper(),
                        key=name.upper(),
                    ),
                }
                f = click_option(*param_decls, **attrs)(f)  # type: ignore[operator]
        return f

    return decorator


# Options from providers
provider_options = {
    name: get_parameters_from_signature(provider_manager[name].plugin) for name in provider_manager.names()
}

refiner_options = {
    name: [
        opt
        for opt in get_parameters_from_signature(refiner_manager[name].plugin)
        if opt['name'] not in ('video', 'kwargs', 'embedded_subtitles', 'providers', 'languages')
    ]
    for name in refiner_manager.names()
}

# Decorator to add click options from providers
options_from_providers = options_from_managers('provider', provider_options, group=providers_config)

# Decorator to add click options from refiners
options_from_refiners = options_from_managers('refiner', refiner_options, group=refiners_config)


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


@subliminal.command()
@click.option(
    '-l',
    '--language',
    type=LANGUAGE,
    required=True,
    multiple=True,
    help='Language as IETF code, e.g. en, pt-BR (can be used multiple times).',
)
@click.option(
    '-p',
    '--provider',
    type=PROVIDER,
    multiple=True,
    help='Provider to use (can be used multiple times).',
)
@click.option(
    '-pp',
    '--extend-provider',
    type=PROVIDER,
    multiple=True,
    help=(
        'Provider to use, on top of the default list (can be used multiple times). '
        'Supersedes the providers used or ignored in the configuration file.'
    ),
)
@click.option(
    '-P',
    '--ignore-provider',
    type=PROVIDER,
    multiple=True,
    help=(
        'Provider to ignore (can be used multiple times). '
        'Supersedes the providers used or ignored in the configuration file.'
    ),
)
@click.option(
    '-r',
    '--refiner',
    type=REFINER,
    multiple=True,
    help='Refiner to use (can be used multiple times).',
)
@click.option(
    '-rr',
    '--extend-refiner',
    type=REFINER,
    multiple=True,
    help=(
        'Refiner to use, on top of the default list (can be used multiple times). '
        'Supersedes the refiners used or ignored in the configuration file.'
    ),
)
@click.option(
    '-R',
    '--ignore-refiner',
    type=REFINER,
    multiple=True,
    help=(
        'Refiner to ignore (can be used multiple times). '
        'Supersedes the refiners used or ignored in the configuration file.'
    ),
)
@click.option(
    '-I',
    '--ignore-subtitles',
    type=click.STRING,
    multiple=True,
    help='Subtitle ids to ignore (can be used multiple times).',
)
@click.option(
    '-a',
    '--age',
    type=AGE,
    help='Filter videos newer than AGE, e.g. 12h, 1w2d.',
)
@click.option(
    '--use-ctime/--no-use-ctime',
    is_flag=True,
    default=True,
    help=(
        'Use the latest of modification date and creation date to calculate the age. '
        'Otherwise, just use the modification date.'
    ),
)
@click.option(
    '-d',
    '--directory',
    type=click.STRING,
    metavar='DIR',
    help='Directory where to save subtitles, default is next to the video file.',
)
@click.option(
    '-e',
    '--encoding',
    type=click.STRING,
    metavar='ENC',
    default='utf-8',
    help='Force subtitle file encoding, set to an empty string to preserve the original encoding. Default is utf-8.',
)
@click.option(
    '-F',
    '--subtitle-format',
    type=click.STRING,
    metavar='FORMAT',
    default='',
    help="Force subtitle format, set to an empty string to preserve the original format. Default is ''.",
)
@click.option(
    '-s',
    '--single',
    is_flag=True,
    default=False,
    help=(
        'Save subtitle without language code in the file name, i.e. use .srt extension. '
        'Do not use this unless your media player requires it.'
    ),
)
@click.option(
    '--force-external-subtitles',
    is_flag=True,
    default=False,
    help='Force download even if an external subtitle already exists. Superseded by `--force`.',
)
@click.option(
    '--force-embedded-subtitles',
    is_flag=True,
    default=False,
    help='Force download even if an embedded subtitle already exists. Superseded by `--force`.',
)
@click.option(
    '-f',
    '--force',
    is_flag=True,
    default=False,
    help=(
        'Force download even if a subtitle already exists. '
        'Supersedes `--force-external-subtitles` and `--force-embedded-subtitles`.'
    ),
)
@click.option(
    '-W',
    '--skip-wrong-fps',
    is_flag=True,
    default=False,
    help='Skip subtitles with an FPS that do not match the video (if it can be detected).',
)
@click.option(
    '-fo',
    '--foreign-only',
    'foreign_only',
    is_flag=True,
    flag_value=True,
    multiple=True,
    help='Prefer foreign-only subtitles.',
)
@click.option(
    '-FO',
    '--no-foreign-only',
    'foreign_only',
    is_flag=True,
    flag_value=False,
    multiple=True,
    help='Disfavor foreign-only subtitles.',
)
@click.option(
    '-hi',
    '--hearing-impaired',
    'hearing_impaired',
    is_flag=True,
    flag_value=True,
    multiple=True,
    help='Prefer hearing-impaired subtitles.',
)
@click.option(
    '-HI',
    '--no-hearing-impaired',
    'hearing_impaired',
    is_flag=True,
    flag_value=False,
    multiple=True,
    help='Disfavor hearing-impaired subtitles.',
)
@click.option(
    '-m',
    '--min-score',
    type=click.IntRange(0, 100),
    default=0,
    help='Minimum score for a subtitle to be downloaded (0 to 100).',
)
@click.option(
    '--language-type-suffix/--no-language-type-suffix',
    is_flag=True,
    default=False,
    help='Add a suffix to the saved subtitle name to indicate a hearing impaired or foreign only subtitle.',
)
@click.option(
    '--language-format',
    default='alpha2',
    help='Format of the language code in the saved subtitle name. Default is a 2-letter language code.',
)
@click.option(
    '-w',
    '--max-workers',
    type=click.IntRange(1, 50),
    default=None,
    help='Maximum number of threads to use.',
)
@click.option(
    '-z/-Z',
    '--archives/--no-archives',
    default=True,
    show_default=True,
    help=f'Scan archives for videos (supported extensions: {", ".join(ARCHIVE_EXTENSIONS)}).',
)
@click.option(
    '--use-absolute-path',
    type=click.Choice(['fallback', 'always', 'never']),
    default='fallback',
    show_default=True,
    show_choices=True,
    help=(
        'Convert the given path to an absolute path if "always" or leave the path as-is if "never". '
        'If "fallback", first try without converting to absolute path, then if the guess failed, '
        'retry after converting to absolute path.'
    ),
)
@click.option(
    '-n',
    '--name',
    type=click.STRING,
    metavar='NAME',
    help=(
        'Name used instead of the path name for guessing information about the file. '
        'If used with multiple paths or a directory, `name` is passed to ALL the files.'
    ),
)
@click.option('-v', '--verbose', count=True, help='Increase verbosity.')
@click.argument('path', type=click.Path(), required=True, nargs=-1)
@click.pass_obj
def download(
    obj: dict[str, Any],
    provider: Sequence[str],
    extend_provider: Sequence[str],
    ignore_provider: Sequence[str],
    refiner: Sequence[str],
    extend_refiner: Sequence[str],
    ignore_refiner: Sequence[str],
    ignore_subtitles: Sequence[str],
    language: Sequence[Language],
    age: timedelta | None,
    use_ctime: bool,
    directory: str | None,
    encoding: str | None,
    subtitle_format: str | None,
    single: bool,
    force_external_subtitles: bool,
    force_embedded_subtitles: bool,
    force: bool,
    skip_wrong_fps: bool,
    hearing_impaired: tuple[bool | None, ...],
    foreign_only: tuple[bool | None, ...],
    min_score: int,
    language_type_suffix: bool,
    language_format: str,
    max_workers: int,
    archives: bool,
    use_absolute_path: str,
    name: str | None,
    verbose: int,
    path: list[str],
) -> None:
    """Download best subtitles.

    PATH can be an directory containing videos, a video file path or a video file name. It can be used multiple times.

    If an existing subtitle is detected (external or embedded) in the correct language, the download is skipped for
    the associated video.

    """
    # process parameters
    language_set = set(language)

    # no encoding specified, default to None. Also convert to None --encoding=''
    if not encoding or encoding in ['""', "''"]:
        encoding = None
    # no subtitle_format specified, default to None Also convert to None --subtitle_format=''
    if not subtitle_format or subtitle_format in ['""', "''"]:
        subtitle_format = None

    # language_type
    hearing_impaired_flag: bool | None = None
    if len(hearing_impaired) > 0:
        hearing_impaired_flag = hearing_impaired[-1]
    foreign_only_flag: bool | None = None
    if len(foreign_only) > 0:
        foreign_only_flag = foreign_only[-1]

    logger.info('Download with subliminal version %s', __version__)
    # Make sure verbose is maximal if debug is specified to show ALL the messages
    debug = obj.get('debug', False)
    if debug:
        verbose = 3

    # parse list of refiners
    use_providers = merge_extend_and_ignore_unions(
        {
            'select': provider,
            'extend': extend_provider,
            'ignore': ignore_provider,
        },
        obj['provider_lists'],
        get_default_providers(),
    )
    logger.info('Use providers: %s', use_providers)
    use_refiners = merge_extend_and_ignore_unions(
        {
            'select': refiner,
            'extend': extend_refiner,
            'ignore': ignore_refiner,
        },
        obj['refiner_lists'],
        get_default_refiners(),
    )
    logger.info('Use refiners: %s', use_refiners)

    # Convert to absolute path only with 'always'
    absolute_path = use_absolute_path == 'always'

    # scan videos
    videos = []
    ignored_videos = []
    errored_paths = []
    with click.progressbar(path, label='Collecting videos', item_show_func=lambda p: p or '') as bar:
        for p in bar:
            if debug:
                # print a new line, so the logs appear below the progressbar
                click.echo()
            # expand user in case an absolute path is provided
            p = os.path.expanduser(p)
            logger.debug('Collecting path %s', p)

            # collect files from directory
            collected_filepaths = [p]
            if os.path.isdir(p):
                # collect video files
                try:
                    collected_filepaths = collect_video_filepaths(p, age=age, archives=archives, use_ctime=use_ctime)
                except ValueError:  # pragma: no cover
                    logger.exception('Unexpected error while collecting directory path %s', p)
                    errored_paths.append(p)
                    continue

            # scan videos
            video_candidates: list[Video] = []
            for filepath in collected_filepaths:
                # Try scanning the video at path
                video = scan_video_path(filepath, absolute_path=absolute_path, name=name, verbose=verbose, debug=debug)
                if video is None:
                    # Fallback to scanning with absolute path
                    if use_absolute_path == 'fallback':
                        video = scan_video_path(
                            filepath,
                            absolute_path=True,
                            name=name,
                            verbose=verbose,
                            debug=debug,
                        )
                    # Cannot scan the video
                    if video is None:
                        errored_paths.append(filepath)
                        continue

                # Set the use_time attribute before refining
                video.use_ctime = use_ctime
                video_candidates.append(video)

            # check and refine videos
            for video in video_candidates:
                if not force and not force_external_subtitles:
                    video.subtitles.extend(search_external_subtitles(video.name, directory=directory).values())
                if check_video(video, languages=language_set, age=age, undefined=single):
                    refine(
                        video,
                        refiners=use_refiners,
                        refiner_configs=obj['refiner_configs'],
                        embedded_subtitles=not force and not force_embedded_subtitles,
                        providers=use_providers,
                        languages=language_set,
                    )
                    videos.append(video)
                else:
                    ignored_videos.append(video)

    # output errored paths
    if verbose > 0:
        for p in errored_paths:
            click.secho(f'{p} errored', fg='red')

    # output ignored videos
    if verbose > 1:
        for video in ignored_videos:
            video_name = os.path.split(video.name)[1]
            msg = f'{video_name!r} ignored'
            if video.exists:
                langs = ', '.join(str(s) for s in video.subtitle_languages) or 'none'
                days = f'{video.age.days:d} day{"s" if video.age.days > 1 else ""}'
                msg += f' - subtitles: {langs} / age: {days}'
            else:
                msg += ' - not a video file'
            click.secho(msg, fg='yellow')

    # report collected videos
    click.echo(
        '{} collected / {} ignored / {}'.format(
            plural(len(videos), 'video', fg='green' if videos else None),
            plural(len(ignored_videos), 'video', fg='yellow' if ignored_videos else None),
            plural(len(errored_paths), 'error', fg='red' if errored_paths else None),
        ),
    )

    # exit if no video collected
    if not videos:
        return

    # exit if no providers are used
    if len(use_providers) == 0:
        click.echo('No provider was selected to download subtitles.')
        if verbose > 0:  # pragma: no cover
            if 'ALL' in ignore_provider:
                click.echo('All ignored from CLI argument: `--ignore-provider=ALL`')
            elif 'ALL' in obj['provider_lists']['ignore']:
                config_ignore = list(obj['provider_lists']['ignore'])
                click.echo(f'All ignored from configuration: `ignore_provider={config_ignore}`')
        return

    # download best subtitles
    downloaded_subtitles = defaultdict(list)
    with AsyncProviderPool(
        max_workers=max_workers,
        providers=use_providers,
        provider_configs=obj['provider_configs'],
    ) as pp:
        with click.progressbar(
            videos,
            label='Downloading subtitles',
            item_show_func=lambda v: os.path.split(v.name)[1] if v is not None else '',
        ) as bar:
            for v in bar:
                if debug:
                    # print a new line, so the logs appear below the progressbar
                    click.echo()
                scores = get_scores(v)
                subtitles = pp.download_best_subtitles(
                    pp.list_subtitles(v, language_set - v.subtitle_languages),
                    v,
                    language_set,
                    min_score=scores['hash'] * min_score // 100,
                    hearing_impaired=hearing_impaired_flag,
                    foreign_only=foreign_only_flag,
                    skip_wrong_fps=skip_wrong_fps,
                    only_one=single,
                    ignore_subtitles=ignore_subtitles,
                )
                downloaded_subtitles[v] = subtitles

        if pp.discarded_providers:  # pragma: no cover
            click.secho(
                f'Some providers have been discarded due to unexpected errors: {", ".join(pp.discarded_providers)}',
                fg='yellow',
            )

    # save subtitles
    total_subtitles = 0
    for v, subtitles in downloaded_subtitles.items():
        saved_subtitles = save_subtitles(
            v,
            subtitles,
            single=single,
            directory=directory,
            encoding=encoding,
            subtitle_format=subtitle_format,
            language_type_suffix=language_type_suffix,
            language_format=language_format,
        )
        total_subtitles += len(saved_subtitles)

        if verbose > 0:
            click.echo(f'{plural(len(saved_subtitles), "subtitle")} downloaded for {os.path.split(v.name)[1]}')

        if verbose > 1:
            for s in saved_subtitles:
                matches = s.get_matches(v)
                score = compute_score(s, v)

                # score color
                score_color = None
                scores = get_scores(v)
                if isinstance(v, Movie):  # pragma: no cover
                    if score < scores['title']:
                        score_color = 'red'
                    elif score < scores['title'] + scores['year'] + scores['release_group']:
                        score_color = 'yellow'
                    else:
                        score_color = 'green'
                elif isinstance(v, Episode):  # pragma: no cover
                    if score < scores['series'] + scores['season'] + scores['episode']:
                        score_color = 'red'
                    elif score < scores['series'] + scores['season'] + scores['episode'] + scores['release_group']:
                        score_color = 'yellow'
                    else:
                        score_color = 'green'

                # scale score from 0 to 100
                scaled_score = score * 100 / scores['hash']

                # echo some nice colored output
                language_str = (
                    s.language.name if s.language.country is None else f'{s.language.name} ({s.language.country.name})'
                )
                click.echo(
                    '  - [{score}] {language} subtitle from {provider_name} (match on {matches})'.format(
                        score=click.style(f'{scaled_score:5.1f}', fg=score_color, bold=score >= scores['hash']),
                        language=language_str,
                        provider_name=s.provider_name,
                        matches=', '.join(sorted(matches, key=lambda m: scores.get(m, 0), reverse=True)),
                    ),
                )

    if verbose == 0:
        click.echo(f'Downloaded {plural(total_subtitles, "subtitle")}')


def cli() -> None:  # pragma: no cover
    """CLI that recognizes environment variables."""
    subliminal(auto_envvar_prefix='SUBLIMINAL')
