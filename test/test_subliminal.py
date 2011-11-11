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


# Set up logging
logging.getLogger('subliminal').setLevel(logging.DEBUG)


# Set up testing stuff
test_folder = u'The Big Bang Theory/'
test_file = u'The Big Bang Theory/Season 05/S05E06 - The Rhinitis Revelation - HD TV.mkv'
cache_dir = u'/tmp/sublicache'
if not os.path.exists(cache_dir):
    os.mkdir(cache_dir)


class GlobalTestCase(unittest.TestCase):
    def setUp(self):
        self.subli = subliminal.Subliminal(cache_dir=cache_dir, workers=1, multi=True, force=True, max_depth=3)
        self.subli.languages = ['en', 'fr']
        self.subli.plugins = ['OpenSubtitles']
        self.subli.startWorkers()

    def tearDown(self):
        self.subli.stopWorkers()

    def test_list_file(self):
        results = self.subli.listSubtitles(test_file, False)
        self.assertTrue(len(results) > 0)

    def test_list_folder(self):
        results = self.subli.listSubtitles(test_folder, False)
        self.assertTrue(len(results) > 0)

    def test_download_file(self):
        results = self.subli.downloadSubtitles(test_file, False)
        self.assertTrue(len(results) > 0)

    def test_download_folder(self):
        results = self.subli.downloadSubtitles(test_folder, False)
        self.assertTrue(len(results) > 0)

'''
class ErrorTestCase(unittest.TestCase):
    def setUp(self):
        self.subli = subliminal.Subliminal(cache_dir=cache_dir, workers=4, multi=False, force=True, max_depth=3, filemode=-1)

    def test_language(self):
        with self.assertRaises(subliminal.exceptions.InvalidLanguageError):
            self.subli.languages = ['en', 'fr', 'zz', 'pt']

    def test_plugin(self):
        with self.assertRaises(subliminal.exceptions.PluginError):
            self.subli.plugins = ['WrongPlugin']

    def test_badstate(self):
        self.subli.startWorkers()
        with self.assertRaises(subliminal.exceptions.BadStateError):
            self.subli.workers = 5
        self.subli.stopWorkers()
'''
'''
class PriorityQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.subli = subliminal.Subliminal(cache_dir=cache_dir, workers=4, multi=False, force=True, max_depth=3, files_mode=-1)
        self.subli.languages = ['en', 'fr', 'es', 'pt']
        self.subli.plugins = subliminal.PLUGINS

    def test_bad_state_error(self):
        with self.assertRaises(subliminal.exceptions.BadStateError):
            self.subli.startWorkers()
            results = self.subli.listSubtitles(test_folder)
        self.subli.stopWorkers()

    def test_manual_list(self):
        self.subli.taskQueue.put((5, subliminal.tasks.ListTask(test_file, set(self.subli.languages), 'OpenSubtitles', self.subli.getConfigDict())))
        self.subli.startWorkers()
        # parallel stuff...
        self.subli.stopWorkers()
        result = self.subli.listResultQueue.get()
        self.assertTrue(len(result) > 0)
'''

def suite():
    suite = unittest.TestSuite()
    suite.addTest(GlobalTestCase('test_list_file'))
    #suite.addTest(GlobalTestCase('test_list_folder'))
    suite.addTest(GlobalTestCase('test_download_file'))
    #suite.addTest(GlobalTestCase('test_download_folder'))
    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

