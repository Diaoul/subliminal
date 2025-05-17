# ruff: noqa: FBT001
"""Download best subtitles command."""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import click

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
from subliminal.utils import merge_extend_and_ignore_unions

from ._format import AgeParamType, LanguageParamType, plural

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import timedelta

    from babelfish import Language


logger = logging.getLogger(__name__)


LANGUAGE = LanguageParamType()

AGE = AgeParamType()

PROVIDER = click.Choice(['ALL', *sorted(provider_manager.names())])

REFINER = click.Choice(['ALL', *sorted(refiner_manager.names())])


@click.command()
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
