# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import argparse
import datetime
import logging
import os
import re
import sys
import babelfish
import guessit
import pkg_resources
from subliminal import (__version__, PROVIDERS_ENTRY_POINT, cache_region, MutexLock, Video, Episode, Movie, scan_videos,
    download_best_subtitles)
try:
    import colorlog
except ImportError:
    colorlog = None


DEFAULT_CACHE_FILE = os.path.join('~', '.config', 'subliminal.cache.dbm')


def subliminal():
    parser = argparse.ArgumentParser(prog='subliminal', description='Subtitles, faster than your thoughts',
                                     epilog='Suggestions and bug reports are greatly appreciated: '
                                     'https://github.com/Diaoul/subliminal/issues', add_help=False)

    # required arguments
    required_arguments_group = parser.add_argument_group('required arguments')
    required_arguments_group.add_argument('paths', nargs='+', metavar='PATH', help='path to video file or folder')
    required_arguments_group.add_argument('-l', '--languages', nargs='+', required=True, metavar='LANGUAGE',
                                          help='wanted languages as IETF codes e.g. fr, pt-BR, sr-Cyrl ')

    # configuration
    configuration_group = parser.add_argument_group('configuration')
    configuration_group.add_argument('-s', '--single', action='store_true',
                                     help='download without language code in subtitle\'s filename i.e. .srt only')
    configuration_group.add_argument('-c', '--cache-file', default=DEFAULT_CACHE_FILE,
                                     help='cache file (default: %(default)s)')

    # filtering
    filtering_group = parser.add_argument_group('filtering')
    providers = [ep.name for ep in pkg_resources.iter_entry_points(PROVIDERS_ENTRY_POINT)]
    filtering_group.add_argument('-p', '--providers', nargs='+', metavar='PROVIDER',
                                 help='providers to use (%s)' % ', '.join(providers))
    filtering_group.add_argument('-m', '--min-score', type=int,
                                 help='minimum score for subtitles (0-%d for episodes, 0-%d for movies)'
                                 % (Episode.scores['hash'], Movie.scores['hash']))
    filtering_group.add_argument('-a', '--age', help='download subtitles for videos newer than AGE e.g. 12h, 1w2d')
    filtering_group.add_argument('-h', '--hearing-impaired', action='store_true',
                                 help='download hearing impaired subtitles')
    filtering_group.add_argument('-f', '--force', action='store_true',
                                 help='force subtitle download for videos with existing subtitles')

    # addic7ed
    addic7ed_group = parser.add_argument_group('addic7ed')
    addic7ed_group.add_argument('--addic7ed-username', metavar='USERNAME', help='username for addic7ed provider')
    addic7ed_group.add_argument('--addic7ed-password', metavar='PASSWORD', help='password for addic7ed provider')

    # output
    output_group = parser.add_argument_group('output')
    output_exclusive_group = output_group.add_mutually_exclusive_group()
    output_exclusive_group.add_argument('-q', '--quiet', action='store_true', help='disable output')
    output_exclusive_group.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    output_group.add_argument('--color', action='store_true', help='add color to console output (requires colorlog)')

    # troubleshooting
    troubleshooting_group = parser.add_argument_group('troubleshooting')
    troubleshooting_group.add_argument('--debug', action='store_true', help='debug output')
    troubleshooting_group.add_argument('--version', action='version', version=__version__)
    troubleshooting_group.add_argument('--help', action='help', help='show this help message and exit')

    # parse args
    args = parser.parse_args()

    # parse paths
    try:
        args.paths = [os.path.abspath(os.path.expanduser(p.decode('utf-8'))) for p in args.paths]
    except UnicodeDecodeError:
        parser.error('argument paths: encodings is not utf-8: %r' % args.paths)

    # parse languages
    try:
        args.languages = {babelfish.Language.fromietf(l) for l in args.languages}
    except babelfish.Error:
        parser.error('argument -l/--languages: codes are not IETF: %r' % args.languages)

    # parse age
    if args.age is not None:
        match = re.match(r'^(?:(?P<weeks>\d+?)w)?(?:(?P<days>\d+?)d)?(?:(?P<hours>\d+?)h)?$', args.age)
        if not match:
            parser.error('argument -a/--age: invalid age: %r' % args.age)
        args.age = datetime.timedelta(**{k: int(v) for k, v in match.groupdict(0).items()})

    # parse cache-file
    args.cache_file = os.path.abspath(os.path.expanduser(args.cache_file))
    if not os.path.exists(os.path.split(args.cache_file)[0]):
        parser.error('argument -c/--cache-file: directory %r for cache file does not exist'
                     % os.path.split(args.cache_file)[0])

    # parse provider configs
    provider_configs = {}
    if (args.addic7ed_username is not None and args.addic7ed_password is None
        or args.addic7ed_username is None and args.addic7ed_password is not None):
        parser.error('argument --addic7ed-username/--addic7ed-password: both arguments are required or none')
    if args.addic7ed_username is not None and args.addic7ed_password is not None:
        provider_configs['addic7ed'] = {'username': args.addic7ed_username, 'password': args.addic7ed_password}

    # parse color
    if args.color and colorlog is None:
        parser.error('argument --color: colorlog required')

    # setup output
    if args.debug:
        handler = logging.StreamHandler()
        if args.color:
            handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(levelname)-8s%(reset)s [%(blue)s%(name)s-%(funcName)s:%(lineno)d%(reset)s] %(message)s',
                                                           log_colors=dict(colorlog.default_log_colors.items() + [('DEBUG', 'cyan')])))
        else:
            handler.setFormatter(logging.Formatter('%(levelname)-8s [%(name)s-%(funcName)s:%(lineno)d] %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose:
        handler = logging.StreamHandler()
        if args.color:
            handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(levelname)-8s%(reset)s [%(blue)s%(name)s%(reset)s] %(message)s'))
        else:
            handler.setFormatter(logging.Formatter('%(levelname)-8s [%(name)s] %(message)s'))
        logging.getLogger('subliminal').addHandler(handler)
        logging.getLogger('subliminal').setLevel(logging.INFO)
    elif not args.quiet:
        handler = logging.StreamHandler()
        if args.color:
            handler.setFormatter(colorlog.ColoredFormatter('[%(log_color)s%(levelname)s%(reset)s] %(message)s'))
        else:
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logging.getLogger('subliminal.api').addHandler(handler)
        logging.getLogger('subliminal.api').setLevel(logging.INFO)

    # configure cache
    cache_region.configure('dogpile.cache.dbm', expiration_time=datetime.timedelta(days=30),  # @UndefinedVariable
                           arguments={'filename': args.cache_file, 'lock_factory': MutexLock})

    # scan videos
    videos = scan_videos([p for p in args.paths if os.path.exists(p)], subtitles=not args.force,
                         embedded_subtitles=not args.force, age=args.age)

    # guess videos
    videos.extend([Video.fromguess(os.path.split(p)[1], guessit.guess_file_info(p, 'autodetect')) for p in args.paths
                   if not os.path.exists(p)])

    # download best subtitles
    subtitles = download_best_subtitles(videos, args.languages, providers=args.providers,
                                        provider_configs=provider_configs, single=args.single,
                                        min_score=args.min_score, hearing_impaired=args.hearing_impaired)

    # result output
    if not subtitles:
        if not args.quiet:
            sys.stderr.write('No subtitles downloaded\n')
        exit(1)
    if not args.quiet:
        subtitles_count = sum([len(s) for s in subtitles.values()])
        if subtitles_count == 1:
            print('%d subtitle downloaded' % subtitles_count)
        else:
            print('%d subtitles downloaded' % subtitles_count)
