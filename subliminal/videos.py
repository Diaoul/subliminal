# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import struct
import os
import hashlib
import guessit
import subprocess
from utils import splitKeyword


EXTENSIONS = ['.mkv', '.avi', '.mpg'] #TODO: Complete..
MIMETYPES = ['video/mpeg', 'video/mp4', 'video/quicktime', 'video/x-ms-wmv', 'video/x-msvideo', 'video/x-flv', 'video/x-matroska', 'video/x-matroska-3d']
KEYWORD_SEPARATORS = ['.', '_', ' ', '/', '-']


class Video(object):
    """Base class for videos"""
    def __init__(self, release, keywords):
        self.release = release
        self.keywords = keywords
        self._path = None
        if os.path.exists(self.release):
            self.path = self.release

    @property
    def exists(self):
        if self.path:
            return os.path.exists(self.path)
        return False

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        if not os.path.exists(value):
            raise ValueError('Path does not exists')
        self._path = value
        self._computeHashes()

    def _computeHashes(self):
        self.hashes = {}
        self.hashes['OpenSubtitles'] = self._computeHashOpenSubtitles()
        self.hashes['TheSubDB'] = self._computeHashTheSubDB()

    def _computeHashOpenSubtitles(self):
        """Hash a file like OpenSubtitles"""
        longlongformat = 'q'  # long long
        bytesize = struct.calcsize(longlongformat)
        f = open(self.path, 'rb')
        filesize = os.path.getsize(self.path)
        hash = filesize
        if filesize < 65536 * 2:
            return []
        for _ in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF
        f.close()
        returnedhash = '%016x' % hash
        return returnedhash

    def _computeHashTheSubDB(self):
        """Hash a file like TheSubDB"""
        readsize = 64 * 1024
        with open(self.path, 'rb') as f:
            data = f.read(readsize)
            f.seek(-readsize, os.SEEK_END)
            data += f.read(readsize)
        return hashlib.md5(data).hexdigest()

    def mkvmerge(self, subtitles, out=None, mkvmerge_bin='mkvmerge', title=None):
        """Merge the video with subtitles"""
        if not out:
            out = self.path + '.merged.mkv'
        args = [mkvmerge_bin, '-o', out]
        if title:
            args += ['--title', title]
        for subtitle in subtitles:
            args += ['--language', '0:' + subtitle.language, subtitle.path]
        p = subprocess.Popen(args)
        p.wait()

    @classmethod
    def factory(cls, release):
        #TODO: Work with lowercase
        """Create a Video object guessing all informations from the given release/path"""
        guess = guessit.guess_file_info(release, 'autodetect')
        keywords = set()
        for k in ['releaseGroup', 'screenSize', 'videoCodec', 'format', 'container']:
            if k in guess:
                keywords = keywords | splitKeyword(guess[k], KEYWORD_SEPARATORS)
        if guess['type'] == 'episode' and 'series' in guess and 'season' in guess and 'episodeNumber' in guess:
            title = None
            if 'title' in guess:
                title = guess['title']
            return Episode(release, keywords, guess['series'], guess['season'], guess['episodeNumber'], title)
        if guess['type'] == 'movie' and 'title' in guess:
            year = None
            if 'year' in guess:
                year = guess['year']
            return Movie(release, keywords, guess['title'], year)
        return UnknownVideo(release, keywords, guess)


class Episode(Video):
    """Episode class"""
    def __init__(self, release, keywords, series, season, episode, title=None):
        super(Episode, self).__init__(release, keywords)
        self.series = series
        self.title = title
        self.season = season
        self.episode = episode


class Movie(Video):
    """Movie class"""
    def __init__(self, release, keywords, title, year=None):
        super(Movie, self).__init__(release, keywords)
        self.title = title
        self.year = year


class UnknownVideo(Video):
    """Unknown video"""
    def __init__(self, release, keywords, guess):
        super(UnknownVideo, self).__init__(release, keywords)
        self.guess = guess
