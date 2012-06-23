#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from subliminal.subtitles import EmbeddedSubtitle, ExternalSubtitle
from subliminal.videos import scan
from subliminal.language import Language
import StringIO
import os
import requests
import tarfile
import unittest


test_dir = 'test_videos_files'


def setUpModule():
    if not os.path.exists(test_dir):
        r = requests.get('https://github.com/downloads/Diaoul/subliminal/test_videos_files.tar.gz')
        with tarfile.open(fileobj=StringIO.StringIO(r.content), mode='r:gz') as f:
            f.extractall(test_dir)


class ScanTestCase(unittest.TestCase):
    def test_basic(self):
        results = scan(test_dir)
        self.assertTrue(len(results) == 1)
        self.assertTrue(isinstance(results[0], tuple))
        self.assertTrue(len(results[0]) == 2)

    def test_embedded_subtitles(self):
        results = [s for s in scan(test_dir)[0][1] if isinstance(s, EmbeddedSubtitle)]
        self.assertTrue(len(results) == 8)
        for l in ('fre', 'eng', 'ita', 'spa', 'hun', 'ger', 'jpn', 'und'):
            self.assertTrue(any([s.language == Language(l) for s in results]))

    def test_external_subtitles(self):
        results = [s for s in scan(test_dir)[0][1] if isinstance(s, ExternalSubtitle)]
        self.assertTrue(len(results) == 3)
        for l in ('fre', 'eng', 'und'):
            self.assertTrue(any([s.language == Language(l) for s in results]))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(ScanTestCase))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
