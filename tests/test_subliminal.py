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
from subliminal import Pool, list_subtitles, download_subtitles
import os
import time
import unittest
import requests
import tarfile
import StringIO


test_dir = 'test_subliminal_files'
cache_dir = 'test_subliminal_cache'
test_video = 'The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4'


def setUpModule():
    if not os.path.exists(test_dir):
        r = requests.get('https://github.com/downloads/Diaoul/subliminal/test_subliminal_files.tar.gz')
        with tarfile.open(fileobj=StringIO.StringIO(r.content), mode='r:gz') as f:
            f.extractall(test_dir)
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)


class ApiTestCase(unittest.TestCase):
    def test_list_subtitles(self):
        results = list_subtitles(test_video, languages=['en', 'fr'], cache_dir=cache_dir)
        self.assertTrue(len(results) > 0)

    def test_download_subtitles(self):
        results = download_subtitles(test_video, languages=['en', 'fr'], cache_dir=cache_dir)
        self.assertTrue(len(results) == 1)
        for video, subtitles in results.iteritems():
            self.assertTrue(video.release == test_video)
            self.assertTrue(len(subtitles) == 1)
            for subtitle in subtitles:
                self.assertTrue(subtitle.path == os.path.splitext(os.path.basename(test_video))[0] + '.srt')
                self.assertTrue(os.path.exists(subtitle.path))
                os.remove(subtitle.path)

    def test_download_subtitles_noforce(self):
        results_first = download_subtitles(test_dir, languages=['en', 'fr'], cache_dir=cache_dir, force=False, services=['thesubdb'])
        results = download_subtitles(test_dir, languages=['en', 'fr'], cache_dir=cache_dir, force=False, services=['thesubdb'])
        self.assertTrue(len(results) == 0)
        for _, subtitles in results_first.iteritems():
            for subtitle in subtitles:
                os.remove(subtitle.path)

    def test_download_subtitles_multi(self):
        results = download_subtitles(test_video, languages=['en', 'fr'], cache_dir=cache_dir, multi=True)
        self.assertTrue(len(results) == 1)
        for video, subtitles in results.iteritems():
            self.assertTrue(video.release == test_video)
            self.assertTrue(len(subtitles) == 2)
            for subtitle in subtitles:
                self.assertTrue(os.path.exists(subtitle.path))
                os.remove(subtitle.path)

    def test_download_subtitles_multi_noforce(self):
        results_first = download_subtitles(test_dir, languages=['en', 'fr'], cache_dir=cache_dir, multi=True, force=False, services=['thesubdb'])
        results = download_subtitles(test_dir, languages=['en', 'fr'], cache_dir=cache_dir, multi=True, force=False, services=['thesubdb'])
        self.assertTrue(len(results) == 0)
        for _, subtitles in results_first.iteritems():
            for subtitle in subtitles:
                os.remove(subtitle.path)

    def test_download_subtitles_languages(self):
        results = download_subtitles('Dexter/Season 04/S04E08 - Road Kill - 720p BluRay.mkv', languages=['en'],
                                     cache_dir=cache_dir, multi=True, force=False, services=['subtitulos', 'tvsubtitles'])
        self.assertTrue(len(results) == 1)
        for _, subtitles in results.iteritems():
            self.assertTrue(len(subtitles) == 1)
            for subtitle in subtitles:
                os.remove(subtitle.path)


class AsyncTestCase(unittest.TestCase):
    def test_pool(self):
        p = Pool(4)
        self.assertTrue(len(p.workers) == 4)
        for w in p.workers:
            self.assertTrue(w.isAlive() == False)
        p.start()
        for w in p.workers:
            self.assertTrue(w.isAlive() == True)
        p.stop()
        p.join()
        time.sleep(0.2)  # so terminate is finished on Worker and proper Thread methods finished
        for w in p.workers:
            self.assertTrue(w.isAlive() == False)

    def test_list_subtitles(self):
        with Pool(4) as p:
            results = p.list_subtitles(test_video, languages=['en', 'fr'], cache_dir=cache_dir)
        self.assertTrue(len(results) > 0)

    def test_download_subtitles(self):
        with Pool(4) as p:
            results = p.download_subtitles(test_video, languages=['en', 'fr'], cache_dir=cache_dir)
        self.assertTrue(len(results) == 1)
        for video, subtitles in results.iteritems():
            self.assertTrue(video.release == test_video)
            self.assertTrue(len(subtitles) == 1)
            for subtitle in subtitles:
                self.assertTrue(subtitle.path == os.path.splitext(os.path.basename(test_video))[0] + '.srt')
                self.assertTrue(os.path.exists(subtitle.path))
                os.remove(subtitle.path)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(ApiTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(AsyncTestCase))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
