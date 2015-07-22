# -*- coding: utf-8 -*-
"""
Subliminal uses `click <http://click.pocoo.org>`_ to provide a powerful :abbr:`CLI (command-line interface)`.

"""
from __future__ import unicode_literals, division
from collections import defaultdict
from datetime import timedelta
import logging
import os
import re
import sys

from babelfish import Error as BabelfishError, Language
import click
from dogpile.cache.backends.file import AbstractFileLock
from dogpile.core import ReadWriteMutex

from subliminal import (Episode, Movie, ProviderPool, Video, __version__, check_video, provider_manager, region,
                        save_subtitles, scan_video, scan_videos)
from subliminal.subtitle import compute_score

logger = logging.getLogger(__name__)


class MutexLock(AbstractFileLock):
    """:class:`MutexLock` is a thread-based rw lock based on :class:`dogpile.core.ReadWriteMutex`."""
    def __init__(self, filename):
        self.mutex = ReadWriteMutex()

    def acquire_read_lock(self, wait):
        ret = self.mutex.acquire_read_lock(wait)
        return wait or ret

    def acquire_write_lock(self, wait):
        ret = self.mutex.acquire_write_lock(wait)
        return wait or ret

    def release_read_lock(self):
        return self.mutex.release_read_lock()

    def release_write_lock(self):
        return self.mutex.release_write_lock()


class StringPath(click.Path):
    """A :class:`~click.Path` as :class:`str`."""
    def convert(self, value, param, ctx):
        if isinstance(value, bytes):
            try:
                enc = getattr(sys.stdin, 'encoding', None)
                if enc is not None:
                    value = value.decode(enc)
            except UnicodeDecodeError:
                try:
                    value = value.decode(click.utils.get_filesystem_encoding())
                except UnicodeDecodeError:
                    self.fail('%s is not a correctly encoded path' % value.decode('utf-8', 'replace'))
        return super(StringPath, self).convert(value, param, ctx)


class LanguageParamType(click.ParamType):
    """:class:`~click.ParamType` for languages that returns a :class:`~babelfish.language.Language`"""
    name = 'language'

    def convert(self, value, param, ctx):
        try:
            return Language.fromietf(value)
        except BabelfishError:
            self.fail('%s is not a valid language' % value)

LANGUAGE = LanguageParamType()


class AgeParamType(click.ParamType):
    """:class:`~click.ParamType` for age strings that returns a :class:`~datetime.timedelta`

    An age string is in the form `number + identifier` with possible identifiers:

        * ``w`` for weeks
        * ``d`` for days
        * ``h`` for hours

    The form can be specified multiple times but only with that idenfier ordering. For example:

        * ``1w2d4h`` for 1 week, 2 days and 4 hours
        * ``2w`` for 2 weeks
        * ``3w6h`` for 3 weeks and 6 hours

    """
    name = 'age'

    def convert(self, value, param, ctx):
        match = re.match(r'^(?:(?P<weeks>\d+?)w)?(?:(?P<days>\d+?)d)?(?:(?P<hours>\d+?)h)?$', value)
        if not match:
            self.fail('%s is not a valid age' % value)

        return timedelta(**{k: int(v) for k, v in match.groupdict(0).items()})

AGE = AgeParamType()

PROVIDER = click.Choice(sorted(provider_manager.names()))

subliminal_cache = 'subliminal.dbm'


@click.group(context_settings={'max_content_width': 100}, epilog='Suggestions and bug reports are greatly appreciated: '
             'https://github.com/Diaoul/subliminal/')
@click.option('--addic7ed', type=click.STRING, nargs=2, metavar='USERNAME PASSWORD', help='Addic7ed configuration.')
@click.option('--cache-dir', type=click.Path(writable=True, resolve_path=True, file_okay=False),
              default=click.get_app_dir('subliminal'), show_default=True, expose_value=True,
              help='Path to the cache directory.')
@click.option('--debug', is_flag=True, help='Print useful information for debugging subliminal and for reporting bugs.')
@click.version_option(__version__)
@click.pass_context
def subliminal(ctx, addic7ed, cache_dir, debug):
    """Subtitles, faster than your thoughts."""
    # create cache directory
    try:
        os.makedirs(cache_dir)
    except OSError:
        if not os.path.isdir(cache_dir):
            raise

    # configure cache
    region.configure('dogpile.cache.dbm', expiration_time=timedelta(days=30),
                     arguments={'filename': os.path.join(cache_dir, subliminal_cache), 'lock_factory': MutexLock})

    # configure logging
    if debug:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logging.getLogger('subliminal').addHandler(handler)
        logging.getLogger('subliminal').setLevel(logging.DEBUG)

    # provider configs
    ctx.obj = {'provider_configs': {}}
    if addic7ed:
        ctx.obj['provider_configs']['addic7ed'] = {'username': addic7ed[0], 'password': addic7ed[1]}


@subliminal.command()
@click.option('--clear-subliminal', is_flag=True, help='Clear subliminal\'s cache. Use this ONLY if your cache is '
              'corrupted or if you experience issues.')
@click.pass_context
def cache(ctx, clear_subliminal):
    """Cache management."""
    if clear_subliminal:
        os.remove(os.path.join(ctx.parent.params['cache_dir'], subliminal_cache))
        click.echo('Subliminal\'s cache cleared.')
    else:
        click.echo('Nothing done.')


@subliminal.command()
@click.option('-l', '--language', type=LANGUAGE, required=True, multiple=True, help='Language as IETF code, '
              'e.g. en, pt-BR (can be used multiple times).')
@click.option('-p', '--provider', type=PROVIDER, multiple=True, help='Provider to use (can be used multiple times).')
@click.option('-a', '--age', type=AGE, help='Filter videos newer than AGE, e.g. 12h, 1w2d.')
@click.option('-d', '--directory', type=click.STRING, metavar='DIR', help='Directory where to save subtitles, '
              'default is next to the video file.')
@click.option('-e', '--encoding', type=click.STRING, metavar='ENC', help='Subtitle file encoding, default is to '
              'preserve original encoding.')
@click.option('-s', '--single', is_flag=True, default=False, help='Save subtitle without language code in the file '
              'name, i.e. use .srt extension.')
@click.option('-f', '--force', is_flag=True, default=False, help='Force download even if a subtitle already exist.')
@click.option('-hi', '--hearing-impaired', is_flag=True, default=False, help='Prefer hearing impaired subtitles.')
@click.option('-m', '--min-score', type=click.IntRange(0, 100), default=0, help='Minimum score for a subtitle '
              'to be downloaded (0 to 100).')
@click.option('-v', '--verbose', count=True, help='Increase verbosity.')
@click.argument('path', type=StringPath(), required=True, nargs=-1)
@click.pass_obj
def download(obj, provider, language, age, directory, encoding, single, force, hearing_impaired, min_score, verbose,
             path):
    """Download best subtitles.

    PATH can be an directory containing videos, a video file path or a video file name. It can be used multiple times.

    If an existing subtitle is detected (external or embedded) in the correct language, the download is skipped for
    the associated video.

    """
    # process parameters
    language = set(language)

    # scan videos
    videos = []
    ignored_videos = []
    errored_paths = []
    with click.progressbar(path, label='Collecting videos', item_show_func=lambda p: p or '') as bar:
        for p in bar:
            logger.debug('Collecting path %s', p)

            # non-existing
            if not os.path.exists(p):
                try:
                    video = Video.fromname(p)
                except:
                    logger.exception('Unexpected error while collecting non-existing path %s', p)
                    errored_paths.append(p)
                    continue
                videos.append(video)
                continue

            # directories
            if os.path.isdir(p):
                try:
                    scanned_videos = scan_videos(p, subtitles=not force, embedded_subtitles=not force)
                except:
                    logger.exception('Unexpected error while collecting directory path %s', p)
                    errored_paths.append(p)
                    continue
                for video in scanned_videos:
                    if check_video(video, languages=language, age=age, undefined=single):
                        videos.append(video)
                    else:
                        ignored_videos.append(video)
                continue

            # other inputs
            try:
                video = scan_video(p, subtitles=not force, embedded_subtitles=not force)
            except:
                logger.exception('Unexpected error while collecting path %s', p)
                errored_paths.append(p)
                continue
            if check_video(video, languages=language, age=age, undefined=single):
                videos.append(video)
            else:
                ignored_videos.append(video)

    # output errored paths
    if verbose > 0:
        for p in errored_paths:
            click.secho('%s errored' % p, fg='red')

    # output ignored videos
    if verbose > 1:
        for video in ignored_videos:
            click.secho('%s ignored - subtitles: %s / age: %d day%s' % (
                os.path.split(video.name)[1],
                ', '.join(str(s) for s in video.subtitle_languages) or 'none',
                video.age.days,
                's' if video.age.days > 1 else ''
            ), fg='yellow')

    # report collected videos
    click.echo('%s video%s collected / %s video%s ignored / %s error%s' % (
        click.style(str(len(videos)), bold=True, fg='green' if videos else None),
        's' if len(videos) > 1 else '',
        click.style(str(len(ignored_videos)), bold=True, fg='yellow' if ignored_videos else None),
        's' if len(ignored_videos) > 1 else '',
        click.style(str(len(errored_paths)), bold=True, fg='red' if errored_paths else None),
        's' if len(errored_paths) > 1 else '',
    ))

    # exit if no video collected
    if not videos:
        return

    # download best subtitles
    downloaded_subtitles = defaultdict(list)
    with ProviderPool(providers=provider, provider_configs=obj['provider_configs']) as pool:
        with click.progressbar(videos, label='Downloading subtitles',
                               item_show_func=lambda v: os.path.split(v.name)[1] if v is not None else '') as bar:
            for v in bar:
                subtitles = pool.download_best_subtitles(pool.list_subtitles(v, language - v.subtitle_languages),
                                                         v, language, min_score=v.scores['hash'] * min_score / 100,
                                                         hearing_impaired=hearing_impaired, only_one=single)
                downloaded_subtitles[v] = subtitles

    # save subtitles
    total_subtitles = 0
    for v, subtitles in downloaded_subtitles.items():
        saved_subtitles = save_subtitles(v, subtitles, single=single, directory=directory, encoding=encoding)
        total_subtitles += len(saved_subtitles)

        if verbose > 0:
            click.echo('%s subtitle%s downloaded for %s' % (click.style(str(len(saved_subtitles)), bold=True),
                                                            's' if len(saved_subtitles) > 1 else '',
                                                            os.path.split(v.name)[1]))

        if verbose > 1:
            for s in saved_subtitles:
                matches = s.get_matches(v, hearing_impaired=hearing_impaired)
                score = compute_score(matches, v)

                # score color
                score_color = None
                if isinstance(v, Movie):
                    if score < v.scores['title']:
                        score_color = 'red'
                    elif score < v.scores['title'] + v.scores['year'] + v.scores['release_group']:
                        score_color = 'yellow'
                    else:
                        score_color = 'green'
                elif isinstance(v, Episode):
                    if score < v.scores['series'] + v.scores['season'] + v.scores['episode']:
                        score_color = 'red'
                    elif score < (v.scores['series'] + v.scores['season'] + v.scores['episode'] +
                                  v.scores['release_group']):
                        score_color = 'yellow'
                    else:
                        score_color = 'green'

                # scale score from 0 to 100 taking out preferences
                scaled_score = score
                if s.hearing_impaired == hearing_impaired:
                    scaled_score -= v.scores['hearing_impaired']
                scaled_score *= 100 / v.scores['hash']

                # echo some nice colored output
                click.echo('  - [{score}] {language} subtitle from {provider_name} (match on {matches})'.format(
                    score=click.style('{:5.1f}'.format(scaled_score), fg=score_color, bold=score >= v.scores['hash']),
                    language=s.language.name if s.language.country is None else '%s (%s)' % (s.language.name,
                                                                                             s.language.country.name),
                    provider_name=s.provider_name,
                    matches=', '.join(sorted(matches, key=v.scores.get, reverse=True))
                ))

    if verbose == 0:
        click.echo('Downloaded %s subtitle%s' % (click.style(str(total_subtitles), bold=True),
                                                 's' if total_subtitles > 1 else ''))
