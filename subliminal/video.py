# -*- coding: utf-8 -*-
from __future__ import division
from datetime import datetime, timedelta
import hashlib
import logging
import os
import struct

from babelfish import Error as BabelfishError, Language
from enzyme import Error as EnzymeError, MKV
from guessit import guess_episode_info, guess_file_info, guess_movie_info

logger = logging.getLogger(__name__)

#: Video extensions
VIDEO_EXTENSIONS = ('.3g2', '.3gp', '.3gp2', '.3gpp', '.60d', '.ajp', '.asf', '.asx', '.avchd', '.avi', '.bik',
                    '.bix', '.box', '.cam', '.dat', '.divx', '.dmf', '.dv', '.dvr-ms', '.evo', '.flc', '.fli',
                    '.flic', '.flv', '.flx', '.gvi', '.gvp', '.h264', '.m1v', '.m2p', '.m2ts', '.m2v', '.m4e',
                    '.m4v', '.mjp', '.mjpeg', '.mjpg', '.mkv', '.moov', '.mov', '.movhd', '.movie', '.movx', '.mp4',
                    '.mpe', '.mpeg', '.mpg', '.mpv', '.mpv2', '.mxf', '.nsv', '.nut', '.ogg', '.ogm', '.omf', '.ps',
                    '.qt', '.ram', '.rm', '.rmvb', '.swf', '.ts', '.vfw', '.vid', '.video', '.viv', '.vivo', '.vob',
                    '.vro', '.wm', '.wmv', '.wmx', '.wrap', '.wvx', '.wx', '.x264', '.xvid')

#: Subtitle extensions
SUBTITLE_EXTENSIONS = ('.srt', '.sub', '.smi', '.txt', '.ssa', '.ass', '.mpl')


class Video(object):
    """Base class for videos.

    Represent a video, existing or not. Attributes have an associated score based on equations defined in
    :mod:`~subliminal.score`.

    :param str name: name or path of the video.
    :param str format: format of the video (HDTV, WEB-DL, BluRay, ...).
    :param str release_group: release group of the video.
    :param str resolution: resolution of the video stream (480p, 720p, 1080p or 1080i).
    :param str video_codec: codec of the video stream.
    :param str audio_codec: codec of the main audio stream.
    :param int imdb_id: IMDb id of the video.
    :param dict hashes: hashes of the video file by provider names.
    :param int size: size of the video file in bytes.
    :param set subtitle_languages: existing subtitle languages

    """
    #: Score by match property
    scores = {}

    def __init__(self, name, format=None, release_group=None, resolution=None, video_codec=None, audio_codec=None,
                 imdb_id=None, hashes=None, size=None, subtitle_languages=None):
        #: Name or path of the video
        self.name = name

        #: Format of the video (HDTV, WEB-DL, BluRay, ...)
        self.format = format

        #: Release group of the video
        self.release_group = release_group

        #: Resolution of the video stream (480p, 720p, 1080p or 1080i)
        self.resolution = resolution

        #: Codec of the video stream
        self.video_codec = video_codec

        #: Codec of the main audio stream
        self.audio_codec = audio_codec

        #: IMDb id of the video
        self.imdb_id = imdb_id

        #: Hashes of the video file by provider names
        self.hashes = hashes or {}

        #: Size of the video file in bytes
        self.size = size

        #: Existing subtitle languages
        self.subtitle_languages = subtitle_languages or set()

    @property
    def exists(self):
        """Test whether the video exists."""
        return os.path.exists(self.name)

    @property
    def age(self):
        """Age of the video."""
        if self.exists:
            return datetime.utcnow() - datetime.utcfromtimestamp(os.path.getmtime(self.name))

        return timedelta()

    @classmethod
    def fromguess(cls, name, guess):
        """Create an :class:`Episode` or a :class:`Movie` with the given `name` based on the `guess`.

        :param str name: name of the video.
        :param dict guess: guessed data, like a :class:`~guessit.guess.Guess` instance.
        :raise: :class:`ValueError` if the `type` of the `guess` is invalid

        """
        if guess['type'] == 'episode':
            return Episode.fromguess(name, guess)

        if guess['type'] == 'movie':
            return Movie.fromguess(name, guess)

        raise ValueError('The guess must be an episode or a movie guess')

    @classmethod
    def fromname(cls, name):
        """Shortcut for :meth:`fromguess` with a `guess` guessed from the `name`.

        :param str name: name of the video.

        """
        return cls.fromguess(name, guess_file_info(name))

    def __repr__(self):
        return '<%s [%r]>' % (self.__class__.__name__, self.name)

    def __hash__(self):
        return hash(self.name)


class Episode(Video):
    """Episode :class:`Video`.

    Scores are defined by a set of equations, see :func:`~subliminal.score.solve_episode_equations`

    :param str series: series of the episode.
    :param int season: season number of the episode.
    :param int episode: episode number of the episode.
    :param str title: title of the episode.
    :param int year: year of series.
    :param int tvdb_id: TVDB id of the episode

    """
    #: Score by match property
    scores = {'hash': 137, 'imdb_id': 110, 'tvdb_id': 88, 'series': 44, 'year': 44, 'title': 22, 'season': 11,
              'episode': 11, 'release_group': 11, 'format': 6, 'video_codec': 4, 'resolution': 4, 'audio_codec': 2,
              'hearing_impaired': 1}

    def __init__(self, name, series, season, episode, format=None, release_group=None, resolution=None,
                 video_codec=None, audio_codec=None, imdb_id=None, hashes=None, size=None, subtitle_languages=None,
                 title=None, year=None, tvdb_id=None):
        super(Episode, self).__init__(name, format, release_group, resolution, video_codec, audio_codec, imdb_id,
                                      hashes, size, subtitle_languages)
        #: Series of the episode
        self.series = series

        #: Season number of the episode
        self.season = season

        #: Episode number of the episode
        self.episode = episode

        #: Title of the episode
        self.title = title

        #: Year of series
        self.year = year

        #: TVDB id of the episode
        self.tvdb_id = tvdb_id

    @classmethod
    def fromguess(cls, name, guess):
        if guess['type'] != 'episode':
            raise ValueError('The guess must be an episode guess')

        if 'series' not in guess or 'season' not in guess or 'episodeNumber' not in guess:
            raise ValueError('Insufficient data to process the guess')

        return cls(name, guess['series'], guess['season'], guess['episodeNumber'], format=guess.get('format'),
                   release_group=guess.get('releaseGroup'), resolution=guess.get('screenSize'),
                   video_codec=guess.get('videoCodec'), audio_codec=guess.get('audioCodec'),
                   title=guess.get('title'), year=guess.get('year'))

    @classmethod
    def fromname(cls, name):
        return cls.fromguess(name, guess_episode_info(name))

    def __repr__(self):
        if self.year is None:
            return '<%s [%r, %dx%d]>' % (self.__class__.__name__, self.series, self.season, self.episode)

        return '<%s [%r, %d, %dx%d]>' % (self.__class__.__name__, self.series, self.year, self.season, self.episode)


class Movie(Video):
    """Movie :class:`Video`.

    Scores are defined by a set of equations, see :func:`~subliminal.score.solve_movie_equations`

    :param str title: title of the movie.
    :param int year: year of the movie

    """
    #: Score by match property
    scores = {'hash': 62, 'imdb_id': 62, 'title': 23, 'year': 12, 'release_group': 11, 'format': 6, 'video_codec': 4,
              'resolution': 4, 'audio_codec': 2, 'hearing_impaired': 1}

    def __init__(self, name, title, format=None, release_group=None, resolution=None, video_codec=None,
                 audio_codec=None, imdb_id=None, hashes=None, size=None, subtitle_languages=None, year=None):
        super(Movie, self).__init__(name, format, release_group, resolution, video_codec, audio_codec, imdb_id, hashes,
                                    size, subtitle_languages)
        #: Title of the movie
        self.title = title

        #: Year of the movie
        self.year = year

    @classmethod
    def fromguess(cls, name, guess):
        if guess['type'] != 'movie':
            raise ValueError('The guess must be a movie guess')

        if 'title' not in guess:
            raise ValueError('Insufficient data to process the guess')

        return cls(name, guess['title'], format=guess.get('format'), release_group=guess.get('releaseGroup'),
                   resolution=guess.get('screenSize'), video_codec=guess.get('videoCodec'),
                   audio_codec=guess.get('audioCodec'), year=guess.get('year'))

    @classmethod
    def fromname(cls, name):
        return cls.fromguess(name, guess_movie_info(name))

    def __repr__(self):
        if self.year is None:
            return '<%s [%r]>' % (self.__class__.__name__, self.title)

        return '<%s [%r, %d]>' % (self.__class__.__name__, self.title, self.year)


def search_external_subtitles(path):
    """Search for external subtitles from a video `path` and their associated language.

    :param str path: path to the video.
    :return: found subtitles with their languages.
    :rtype: dict

    """
    dirpath, filename = os.path.split(path)
    dirpath = dirpath or '.'
    fileroot, fileext = os.path.splitext(filename)
    subtitles = {}
    for p in os.listdir(dirpath):
        # keep only valid subtitle filenames
        if not p.startswith(fileroot) or not p.endswith(SUBTITLE_EXTENSIONS):
            continue

        # extract the potential language code
        language_code = p[len(fileroot):-len(os.path.splitext(p)[1])].replace(fileext, '').replace('_', '-')[1:]

        # default language is undefined
        language = Language('und')

        # attempt to parse
        if language_code:
            try:
                language = Language.fromietf(language_code)
            except ValueError:
                logger.error('Cannot parse language code %r', language_code)

        subtitles[p] = language

    logger.debug('Found subtitles %r', subtitles)

    return subtitles


def scan_video(path, subtitles=True, embedded_subtitles=True):
    """Scan a video and its subtitle languages from a video `path`.

    :param str path: existing path to the video.
    :param bool subtitles: scan for subtitles with the same name.
    :param bool embedded_subtitles: scan for embedded subtitles.
    :return: the scanned video.
    :rtype: :class:`Video`

    """
    # check for non-existing path
    if not os.path.exists(path):
        raise ValueError('Path does not exist')

    # check video extension
    if not path.endswith(VIDEO_EXTENSIONS):
        raise ValueError('%s is not a valid video extension' % os.path.splitext(path)[1])

    dirpath, filename = os.path.split(path)
    logger.info('Scanning video %r in %r', filename, dirpath)

    # guess
    video = Video.fromguess(path, guess_file_info(path))

    # size and hashes
    video.size = os.path.getsize(path)
    if video.size > 10485760:
        logger.debug('Size is %d', video.size)
        video.hashes['opensubtitles'] = hash_opensubtitles(path)
        video.hashes['thesubdb'] = hash_thesubdb(path)
        video.hashes['napiprojekt'] = hash_napiprojekt(path)
        logger.debug('Computed hashes %r', video.hashes)
    else:
        logger.warning('Size is lower than 10MB: hashes not computed')

    # external subtitles
    if subtitles:
        video.subtitle_languages |= set(search_external_subtitles(path).values())

    # video metadata with enzyme
    try:
        if filename.endswith('.mkv'):
            with open(path, 'rb') as f:
                mkv = MKV(f)

            # main video track
            if mkv.video_tracks:
                video_track = mkv.video_tracks[0]

                # resolution
                if video_track.height in (480, 720, 1080):
                    if video_track.interlaced:
                        video.resolution = '%di' % video_track.height
                    else:
                        video.resolution = '%dp' % video_track.height
                    logger.debug('Found resolution %s with enzyme', video.resolution)

                # video codec
                if video_track.codec_id == 'V_MPEG4/ISO/AVC':
                    video.video_codec = 'h264'
                    logger.debug('Found video_codec %s with enzyme', video.video_codec)
                elif video_track.codec_id == 'V_MPEG4/ISO/SP':
                    video.video_codec = 'DivX'
                    logger.debug('Found video_codec %s with enzyme', video.video_codec)
                elif video_track.codec_id == 'V_MPEG4/ISO/ASP':
                    video.video_codec = 'XviD'
                    logger.debug('Found video_codec %s with enzyme', video.video_codec)
            else:
                logger.warning('MKV has no video track')

            # main audio track
            if mkv.audio_tracks:
                audio_track = mkv.audio_tracks[0]
                # audio codec
                if audio_track.codec_id == 'A_AC3':
                    video.audio_codec = 'AC3'
                    logger.debug('Found audio_codec %s with enzyme', video.audio_codec)
                elif audio_track.codec_id == 'A_DTS':
                    video.audio_codec = 'DTS'
                    logger.debug('Found audio_codec %s with enzyme', video.audio_codec)
                elif audio_track.codec_id == 'A_AAC':
                    video.audio_codec = 'AAC'
                    logger.debug('Found audio_codec %s with enzyme', video.audio_codec)
            else:
                logger.warning('MKV has no audio track')

            # subtitle tracks
            if mkv.subtitle_tracks:
                if embedded_subtitles:
                    embedded_subtitle_languages = set()
                    for st in mkv.subtitle_tracks:
                        if st.language:
                            try:
                                embedded_subtitle_languages.add(Language.fromalpha3b(st.language))
                            except BabelfishError:
                                logger.error('Embedded subtitle track language %r is not a valid language', st.language)
                                embedded_subtitle_languages.add(Language('und'))
                        elif st.name:
                            try:
                                embedded_subtitle_languages.add(Language.fromname(st.name))
                            except BabelfishError:
                                logger.debug('Embedded subtitle track name %r is not a valid language', st.name)
                                embedded_subtitle_languages.add(Language('und'))
                        else:
                            embedded_subtitle_languages.add(Language('und'))
                    logger.debug('Found embedded subtitle %r with enzyme', embedded_subtitle_languages)
                    video.subtitle_languages |= embedded_subtitle_languages
            else:
                logger.debug('MKV has no subtitle track')

    except EnzymeError:
        logger.exception('Parsing video metadata with enzyme failed')

    return video


def scan_videos(path, subtitles=True, embedded_subtitles=True):
    """Scan `path` for videos and their subtitles.

    :param str path: existing directory path to scan.
    :param bool subtitles: scan for subtitles with the same name.
    :param bool embedded_subtitles: scan for embedded subtitles.
    :return: the scanned videos.
    :rtype: list of :class:`Video`

    """
    # check for non-existing path
    if not os.path.exists(path):
        raise ValueError('Path does not exist')

    # check for non-directory path
    if not os.path.isdir(path):
        raise ValueError('Path is not a directory')

    # walk the path
    videos = []
    for dirpath, dirnames, filenames in os.walk(path):
        logger.debug('Walking directory %s', dirpath)

        # remove badly encoded and hidden dirnames
        for dirname in list(dirnames):
            if dirname.startswith('.'):
                logger.debug('Skipping hidden dirname %r in %r', dirname, dirpath)
                dirnames.remove(dirname)

        # scan for videos
        for filename in filenames:
            # filter on videos
            if not filename.endswith(VIDEO_EXTENSIONS):
                continue

            # skip hidden files
            if filename.startswith('.'):
                logger.debug('Skipping hidden filename %r in %r', filename, dirpath)
                continue

            # reconstruct the file path
            filepath = os.path.join(dirpath, filename)

            # skip links
            if os.path.islink(filepath):
                logger.debug('Skipping link %r in %r', filename, dirpath)
                continue

            # scan video
            try:
                video = scan_video(filepath, subtitles=subtitles, embedded_subtitles=embedded_subtitles)
            except ValueError:  # pragma: no cover
                logger.exception('Error scanning video')
                continue

            videos.append(video)

    return videos


def hash_opensubtitles(video_path):
    """Compute a hash using OpenSubtitles' algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    bytesize = struct.calcsize(b'<q')
    with open(video_path, 'rb') as f:
        filesize = os.path.getsize(video_path)
        filehash = filesize
        if filesize < 65536 * 2:
            return
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash &= 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash &= 0xFFFFFFFFFFFFFFFF
    returnedhash = '%016x' % filehash

    return returnedhash


def hash_thesubdb(video_path):
    """Compute a hash using TheSubDB's algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    readsize = 64 * 1024
    if os.path.getsize(video_path) < readsize:
        return
    with open(video_path, 'rb') as f:
        data = f.read(readsize)
        f.seek(-readsize, os.SEEK_END)
        data += f.read(readsize)

    return hashlib.md5(data).hexdigest()


def hash_napiprojekt(video_path):
    """Compute a hash using NapiProjekt's algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    readsize = 1024 * 1024 * 10
    with open(video_path, 'rb') as f:
        data = f.read(readsize)
    return hashlib.md5(data).hexdigest()
