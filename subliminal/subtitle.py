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


EXTENSIONS = ['.srt', '.sub', '.txt']
KEYWORDS_SEPARATORS = ['.', '_', ' ', '/', '-']


class Subtitle(object):
    """Subtitle class

    Attributes:
        video_path -- path to the video file
        path       -- path to the subtitle file
        plugin     -- plugin used
        language   -- language of the subtitle
        link       -- download link
        release    -- release group identified by guessit
        keywords   -- identified by guessit
        confidence -- confidence that the subtitle matches the video
    """
    

    def __init__(self, video_path=None, path=None, plugin=None, language=None, link=None, release=None, keywords=None, confidence=0):
        self.video_path = video_path
        self.path = path
        self.plugin = plugin
        self.language = language
        self.link = link
        self.release = release
        self.keywords = keywords
        self.confidence = confidence

    def __repr__(self):
        return repr({'video_path': self.video_path, 'path': self.path, 'plugin': self.plugin,
            'language': self.language, 'link': self.link, 'release': self.release, 'keywords': self.keywords})

    @classmethod
    def factory(cls, release):
        #TODO: Work with lowercase
        """Create a Subtitle object guessing all informations from the given subtitle release filename"""
        guess = guessit.guess_file_info(release, 'autodetect')
        keywords = set()
        for k in ['releaseGroup', 'screenSize', 'videoCodec', 'format', 'container']:
            if k in guess:
                keywords = keywords | splitKeyword(guess[k])
        return Subtitle(release=release, keywords=keywords)


def splitKeyword(keyword):
    split = set()
    for sep in KEYWORDS_SEPARATORS:
        split = split | set(keyword.split(sep))
    return split
