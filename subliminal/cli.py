# ruff: noqa: FBT001
"""Subliminal uses `click <https://click.palletsprojects.com>`_ to provide a :abbr:`CLI (command-line interface)`."""

from __future__ import annotations

import glob
import logging
import os
import pathlib
import re
from collections import defaultdict
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import click
import tomli
from babelfish import Error as BabelfishError  # type: ignore[import-untyped]
from babelfish import Language
from click_option_group import OptionGroup
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
    scan_video,
    scan_videos,
)
from subliminal.core import ARCHIVE_EXTENSIONS, scan_name, search_external_subtitles
from subliminal.extensions import get_default_providers, get_default_refiners
from subliminal.utils import merge_extend_and_ignore_unions

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class MutexLock(AbstractFileLock):
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
            self.fail(f'{value} is not a valid language', param, ctx)


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


def configure(ctx: click.Context, param: click.Parameter | None, filename: str | os.PathLike) -> None:
    """Read a configuration file."""
    filename = pathlib.Path(filename).expanduser()
    msg = ''
    toml_dict = {}
    if filename.is_file():
        try:
            with open(filename, 'rb') as f:
                toml_dict = tomli.load(f)
        except tomli.TOMLDecodeError:
            msg = f'Cannot read the configuration file at "{filename}"'
        else:
            msg = f'Using configuration file at "{filename}"'
    else:
        msg = f'Not using any configuration file, not a file "{filename}"'

    options = {}

    # make default options
    default_dict = toml_dict.setdefault('default', {})
    if 'cache_dir' in default_dict:
        options['cache_dir'] = default_dict.pop('cache_dir')

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
    providers_dict = toml_dict.setdefault('provider', {})
    refiners_dict = toml_dict.setdefault('refiner', {})

    ctx.obj = {
        'debug_message': msg,
        'provider_lists': provider_lists,
        'refiner_lists': refiner_lists,
        'provider_configs': providers_dict,
        'refiner_configs': refiners_dict,
    }
    ctx.default_map = options


def plural(quantity: int, name: str, *, bold: bool = True, **kwargs: Any) -> str:
    """Format a quantity with plural."""
    return '{} {}{}'.format(
        click.style(str(quantity), bold=bold, **kwargs),
        name,
        's' if quantity > 1 else '',
    )


AGE = AgeParamType()

PROVIDER = click.Choice(['ALL', *sorted(provider_manager.names())])

REFINER = click.Choice(['ALL', *sorted(refiner_manager.names())])

dirs = PlatformDirs('subliminal')
cache_file = 'subliminal.dbm'
default_config_path = dirs.user_config_path / 'subliminal.toml'

providers_config = OptionGroup('Providers configuration')
refiners_config = OptionGroup('Refiners configuration')


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
    help='Addic7ed configuration.',
)
@providers_config.option(
    '--opensubtitles',
    type=click.STRING,
    nargs=2,
    metavar='USERNAME PASSWORD',
    help='OpenSubtitles configuration.',
)
@providers_config.option(
    '--opensubtitlescom',
    type=click.STRING,
    nargs=2,
    metavar='USERNAME PASSWORD',
    help='OpenSubtitles.com configuration.',
)
@refiners_config.option('--omdb', type=click.STRING, nargs=1, metavar='APIKEY', help='OMDB API key.')
@click.option('--debug', is_flag=True, help='Print useful information for debugging subliminal and for reporting bugs.')
@click.version_option(__version__)
@click.pass_context
def subliminal(
    ctx: click.Context,
    cache_dir: str,
    debug: bool,
    addic7ed: tuple[str, str],
    opensubtitles: tuple[str, str],
    opensubtitlescom: tuple[str, str],
    omdb: str,
) -> None:
    """Subtitles, faster than your thoughts."""
    cache_dir = os.path.expanduser(cache_dir)
    # create cache directory
    try:
        os.makedirs(cache_dir)
    except OSError:
        if not os.path.isdir(cache_dir):
            raise

    # configure cache
    region.configure(
        'dogpile.cache.dbm',
        expiration_time=timedelta(days=30),
        arguments={'filename': os.path.join(cache_dir, cache_file), 'lock_factory': MutexLock},
    )

    # configure logging
    if debug:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logging.getLogger('subliminal').addHandler(handler)
        logging.getLogger('subliminal').setLevel(logging.DEBUG)
        # log about the config file
        msg = ctx.obj['debug_message']
        logger.info(msg)

    ctx.obj['debug'] = debug
    # provider configs
    provider_configs = ctx.obj['provider_configs']
    if addic7ed:
        provider_configs['addic7ed'] = {'username': addic7ed[0], 'password': addic7ed[1]}
    if opensubtitles:
        provider_configs['opensubtitles'] = {'username': opensubtitles[0], 'password': opensubtitles[1]}
        provider_configs['opensubtitlesvip'] = {'username': opensubtitles[0], 'password': opensubtitles[1]}
    if opensubtitlescom:
        provider_configs['opensubtitlescom'] = {'username': opensubtitlescom[0], 'password': opensubtitlescom[1]}
        provider_configs['opensubtitlescomvip'] = {'username': opensubtitlescom[0], 'password': opensubtitlescom[1]}

    # refiner configs
    refiner_configs = ctx.obj['refiner_configs']
    if omdb:
        refiner_configs['omdb'] = {'apikey': omdb}


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
        for file in glob.glob(os.path.join(ctx.parent.params['cache_dir'], cache_file) + '*'):
            os.remove(file)
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
@click.option('-p', '--provider', type=PROVIDER, multiple=True, help='Provider to use (can be used multiple times).')
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
@click.option('-r', '--refiner', type=REFINER, multiple=True, help='Refiner to use (can be used multiple times).')
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
@click.option('-a', '--age', type=AGE, help='Filter videos newer than AGE, e.g. 12h, 1w2d.')
@click.option(
    '--use_creation_time',
    'use_ctime',
    is_flag=True,
    default=False,
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
    help='Force subtitle file encoding, default is utf-8.',
)
@click.option(
    '--original-encoding',
    is_flag=True,
    default=False,
    help='Preserve original subtitle file encoding.',
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
@click.option('-f', '--force', is_flag=True, default=False, help='Force download even if a subtitle already exist.')
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
    '--language-type-suffix',
    is_flag=True,
    default=False,
    help='Add a suffix to the saved subtitle name to indicate a hearing impaired or foreign only subtitle.',
)
@click.option(
    '--language-format',
    default='alpha2',
    help='Format of the language code in the saved subtitle name. Default is a 2-letter language code.',
)
@click.option('-w', '--max-workers', type=click.IntRange(1, 50), default=None, help='Maximum number of threads to use.')
@click.option(
    '-z/-Z',
    '--archives/--no-archives',
    default=True,
    show_default=True,
    help=f'Scan archives for videos (supported extensions: {", ".join(ARCHIVE_EXTENSIONS)}).',
)
@providers_config.option(
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
    original_encoding: bool,
    single: bool,
    force: bool,
    hearing_impaired: tuple[bool | None, ...],
    foreign_only: tuple[bool | None, ...],
    min_score: int,
    language_type_suffix: bool,
    language_format: str,
    max_workers: int,
    archives: bool,
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

    # preserve original encoding
    if original_encoding:
        encoding = None
    # no encoding specified, default to utf-8
    elif encoding is None:
        encoding = 'utf-8'

    # language_type
    hearing_impaired_flag: bool | None = None
    if len(hearing_impaired) > 0:
        hearing_impaired_flag = hearing_impaired[-1]
    foreign_only_flag: bool | None = None
    if len(foreign_only) > 0:
        foreign_only_flag = foreign_only[-1]

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

    # scan videos
    videos = []
    ignored_videos = []
    errored_paths = []
    with click.progressbar(path, label='Collecting videos', item_show_func=lambda p: p or '') as bar:
        for p in bar:
            if debug:
                # print a new line, so the logs appear below the progressbar
                click.echo()
            p = os.path.abspath(os.path.expanduser(p))
            logger.debug('Collecting path %s', p)

            video_candidates: list[Video] = []

            # non-existing
            if not os.path.exists(p):
                try:
                    video = scan_name(p, name=name)
                except ValueError:
                    repl_p = f'{p} ({name})' if name else p
                    logger.exception('Unexpected error while collecting non-existing path %s', repl_p)
                    errored_paths.append(p)
                    continue
                video_candidates.append(video)

            # directories
            elif os.path.isdir(p):
                try:
                    scanned_videos = scan_videos(p, age=age, archives=archives, name=name)
                except ValueError:
                    repl_p = f'{p} ({name})' if name else p
                    logger.exception('Unexpected error while collecting directory path %s', repl_p)
                    errored_paths.append(p)
                    continue
                video_candidates.extend(scanned_videos)

            # other inputs
            else:
                try:
                    video = scan_video(p, name=name)
                except ValueError:
                    repl_p = f'{p} ({name})' if name else p
                    logger.exception('Unexpected error while collecting path %s', repl_p)
                    errored_paths.append(p)
                    continue
                video_candidates.append(video)

            # check and refine videos
            for video in video_candidates:
                if not force:
                    video.subtitles |= set(search_external_subtitles(video.name, directory=directory).values())
                if check_video(video, languages=language_set, age=age, use_ctime=use_ctime, undefined=single):
                    refine(
                        video,
                        refiners=use_refiners,
                        refiner_configs=obj['refiner_configs'],
                        embedded_subtitles=not force,
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
                days = f"{video.age.days:d} day{'s' if video.age.days > 1 else ''}"
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
                    only_one=single,
                    ignore_subtitles=ignore_subtitles,
                )
                downloaded_subtitles[v] = subtitles

        if pp.discarded_providers:
            click.secho(
                f"Some providers have been discarded due to unexpected errors: {', '.join(pp.discarded_providers)}",
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
            language_type_suffix=language_type_suffix,
            language_format=language_format,
        )
        total_subtitles += len(saved_subtitles)

        if verbose > 0:
            click.echo(f"{plural(len(saved_subtitles), 'subtitle')} downloaded for {os.path.split(v.name)[1]}")

        if verbose > 1:
            for s in saved_subtitles:
                matches = s.get_matches(v)
                score = compute_score(s, v)

                # score color
                score_color = None
                scores = get_scores(v)
                if isinstance(v, Movie):
                    if score < scores['title']:
                        score_color = 'red'
                    elif score < scores['title'] + scores['year'] + scores['release_group']:
                        score_color = 'yellow'
                    else:
                        score_color = 'green'
                elif isinstance(v, Episode):
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
        click.echo(f"Downloaded {plural(total_subtitles, 'subtitle')}")
