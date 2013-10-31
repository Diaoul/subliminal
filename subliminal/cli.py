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
from subliminal import (__version__, PROVIDERS_ENTRY_POINT, cache_region, Video, Episode, Movie, scan_videos,
    download_best_subtitles)


DEFAULT_CACHE_FILE = os.path.join('~', '.config', 'subliminal.cache.dbm')


def subliminal_parser():
    parser = argparse.ArgumentParser(description='Subtitles, faster than your thoughts')
    parser.add_argument('-l', '--languages', nargs='+', required=True, metavar='LANGUAGE', help='wanted languages as alpha2 code (ISO-639-1)')
    parser.add_argument('-p', '--providers', nargs='+', metavar='PROVIDER', help='providers to use from %s (default: all)' % ', '.join(ep.name for ep in pkg_resources.iter_entry_points(PROVIDERS_ENTRY_POINT)))
    parser.add_argument('-m', '--min-score', type=int, help='minimum score for subtitles. 0-%d for episodes, 0-%d for movies' % (Episode.scores['hash'], Movie.scores['hash']))
    parser.add_argument('-s', '--single', action='store_true', help='download without language code in subtitle\'s filename i.e. .srt only')
    parser.add_argument('-f', '--force', action='store_true', help='overwrite existing subtitles')
    parser.add_argument('-c', '--cache-file', default=DEFAULT_CACHE_FILE, help='cache file (default: %(default)s)')
    parser.add_argument('-a', '--age', help='download subtitles for videos newer than AGE e.g. 12h, 1w2d')
    parser.add_argument('--hearing-impaired', action='store_true', help='download hearing impaired subtitles')
    group_verbosity = parser.add_mutually_exclusive_group()
    group_verbosity.add_argument('-q', '--quiet', action='store_true', help='disable output')
    group_verbosity.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('paths', nargs='+', metavar='PATH', help='path to video file or folder')
    return parser


def subliminal():
    parser = subliminal_parser()
    args = parser.parse_args()

    # parse paths
    try:
        args.paths = [os.path.abspath(os.path.expanduser(p.decode('utf-8'))) for p in args.paths]
    except UnicodeDecodeError:
        parser.error('argument paths: encodings is not utf-8: %r' % args.paths)

    # parse languages
    try:
        args.languages = {babelfish.Language.fromalpha2(l) for l in args.languages}
    except babelfish.Error:
        parser.error('argument -l/--languages: codes are not ISO-639-1: %r' % args.languages)

    # parse age
    if args.age is not None:
        match = re.match(r'^(?:(?P<weeks>\d+?)w)?(?:(?P<days>\d+?)d)?(?:(?P<hours>\d+?)h)?$', args.age)
        if not match:
            parser.error('argument -a/--age: invalid age: %r' % args.age)
        args.age = datetime.timedelta(**{k: int(v) for k, v in match.groupdict(0).items()})

    # parse cache-file
    args.cache_file = os.path.abspath(os.path.expanduser(args.cache_file))
    if not os.path.exists(os.path.split(args.cache_file)[0]):
        if not args.quiet:
            sys.stderr.write('Directory %r for cache file does not exist\n' % os.path.split(args.cache_file)[0])
        exit(1)

    # setup verbosity
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif not args.quiet:
        logging.basicConfig(level=logging.WARN)

    # configure cache
    cache_region.configure('dogpile.cache.dbm', arguments={'filename': args.cache_file})

    # scan videos
    videos = scan_videos([p for p in args.paths if os.path.exists(p)], subtitles=not args.force, age=args.age)

    # guess videos
    videos.extend([Video.fromguess(os.path.split(p)[1], guessit.guess_file_info(p, 'autodetect')) for p in args.paths
                   if not os.path.exists(p)])

    # download best subtitles
    subtitles = download_best_subtitles(videos, args.languages, providers=args.providers, provider_configs=None,
                                        single=args.single, min_score=args.min_score,
                                        hearing_impaired=args.hearing_impaired)

    # output result
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
