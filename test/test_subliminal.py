#!/usr/bin/env python
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

import unittest
import logging
import os
import subliminal


logging.basicConfig(level=logging.DEBUG, format='%(name)-24s %(levelname)-8s %(message)s')
test_folder = u'/your/path/here/videos/'
test_file = u'/your/path/here/videos/the.big.bang.theory.s04e01.hdtv.xvid-fqm.avi'
cache_dir = u'/tmp/sublicache'
if not os.path.exists(cache_dir):
    os.mkdir(cache_dir)


class ListSubtitlesFileTestCase(unittest.TestCase):
    def runTest(self):
        subli = subliminal.Subliminal(cache_dir=cache_dir, workers=4, multi=False, force=True, max_depth=3, autostart=False, files_mode=-1)
        subli.languages = ['en', 'fr', 'es', 'pt']
        subli.plugins = subliminal.PLUGINS
        subli.startWorkers()
        results = subli.listSubtitles(test_file)
        subli.stopWorkers()
        print results
        assert len(results) > 0


class DownloadSubtitlesFileTestCase(unittest.TestCase):
    def runTest(self):
        subli = subliminal.Subliminal(cache_dir=cache_dir, workers=4, multi=True, force=True, max_depth=3, autostart=False, files_mode=755)
        subli.languages = ['en', 'fr', 'es', 'pt']
        subli.plugins = ['OpenSubtitles']
        subli.startWorkers()
        results = subli.downloadSubtitles(test_file)
        subli.stopWorkers()
        print results
        assert len(results) > 0


if __name__ == "__main__":
    unittest.main()

