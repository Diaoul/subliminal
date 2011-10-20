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


import guessit
from utils import splitKeyword
import os.path


EXTENSIONS = ['.srt', '.sub', '.txt']
KEYWORD_SEPARATORS = ['.', '_', ' ', '/', '-']


class Subtitle(object):
    """Subtitle class"""

    def __init__(self, path, plugin=None, language=None, link=None, release=None, confidence=1, keywords=None):
        self.path = path
        self.plugin = plugin
        self.language = language
        self.link = link
        self.release = release
        self.confidence = confidence
        self.keywords = keywords

    def __eq__(self, other):
        return self.path == other.path and self.plugin == other.plugin and self.language == other.language

    @property
    def exists(self):
        if self._path:
            return os.path.exists(self._path)
        return False

    def __repr__(self):
        return repr({'path': self.path, 'plugin': self.plugin, 'language': self.language, 'link': self.link, 'release': self.release, 'keywords': self.keywords, 'confidence': self.confidence})

    @classmethod
    def fromRelease(cls, release):
        """Create a Subtitle object guessing all informations from the given subtitle release filename"""
        guess = guessit.guess_file_info(release, 'autodetect')
        keywords = set()
        for k in ['releaseGroup', 'screenSize', 'videoCodec', 'format', 'container']:
            if k in guess:
                keywords = keywords | splitKeyword(guess[k], KEYWORD_SEPARATORS)
        return Subtitle(release=release, keywords=keywords)


def get_subtitle_path(video_path, language, multi):
    subtitle_path = os.path.splitext(os.path.basename(video_path))[0]
    if multi and language:
        return subtitle_path + '.%s.%s' % (language, EXTENSIONS[0])
    return subtitle_path + '.%s' % EXTENSIONS[0]



