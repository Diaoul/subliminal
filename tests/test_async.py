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
from subliminal import Pool
import os
import time
import unittest


cache_dir = u'/tmp/sublicache'
if not os.path.exists(cache_dir):
    os.mkdir(cache_dir)
existing_video = u'/something/The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4'


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
            results = p.list_subtitles(existing_video, languages=['en', 'fr'], cache_dir=cache_dir, max_depth=3)
        self.assertTrue(len(results) > 0)

    def test_download_subtitles(self):
        with Pool(4) as p:
            results = p.download_subtitles(existing_video, languages=['en', 'fr'], cache_dir=cache_dir, max_depth=3)
        self.assertTrue(len(results) > 0)


if __name__ == '__main__':
    unittest.main()
