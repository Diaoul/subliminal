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

from itertools import groupby
import PluginWorker
import Queue
import locale
import logging
import mimetypes
import os
import plugins
import sys
import traceback
import locale
import encodingKludge as ek


SUPPORTED_FORMATS = 'video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/mp4'
logger = logging.getLogger('subliminal')
SYS_ENCODING = None
try:
    locale.setlocale(locale.LC_ALL, "")
    SYS_ENCODING = locale.getpreferredencoding()
except (locale.Error, IOError):
    pass
# for OSes that are poorly configured I'll just force UTF-8
if not SYS_ENCODING or SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
    SYS_ENCODING = 'UTF-8'


class Subliminal(object):
    """Main Subliminal class"""

    def __init__(self, cache_dir=False, workers=4, multi=False, force=False, max_depth=3, autostart=False, plugins_config=None, files_mode=-1):
        # set default values
        self.multi = multi
        self.force = force
        self.max_depth = max_depth
        self.cache_dir = None
        self.taskQueue = Queue.Queue()
        self.resultQueue = Queue.Queue()
        self._languages = None
        self._plugins = self.listAPIPlugins()
        self.workers = workers
        self.plugins_config = plugins_config
        self.files_mode = files_mode
        if autostart:
            self.startWorkers()
        # handle cache directory preferences
        try:
            if cache_dir:  # custom configuration file
                self.cache_dir = cache_dir
                if not ek.ek(os.path.isdir, self.cache_dir):  # custom file doesn't exist, create it
                    ek.ek(os.mkdir, self.cache_dir)
                    logger.debug(u'Creating cache directory: %s' % self.cache_dir)
        except:
            self.cache_dir = None
            logger.error(u'Failed to use the cache directory, continue without it')

    @staticmethod
    def listExistingPlugins():
        """List all possible plugins"""
        return map(lambda x: x.__name__, plugins.PluginBase.PluginBase.__subclasses__())

    @staticmethod
    def listAPIPlugins():
        """List plugins that use API"""
        return filter(Subliminal.isAPIBasedPlugin, Subliminal.listExistingPlugins())

    def get_languages(self):
        """Getter for languages"""
        return self._languages

    def set_languages(self, value):
        """Setter for languages"""
        logger.debug(u'Setting languages to %r' % value)
        self._languages = filter(self.isValidLanguage, value)

    @staticmethod
    def isValidLanguage(language):
        """Check if a language is valid"""
        if len(language) != 2:
            logger.error(u'Language %s is not valid' % language)
            return False
        return True

    def get_plugins(self):
        """Getter for plugins"""
        return self._plugins

    def set_plugins(self, value):
        """Setter for plugins"""
        logger.debug(u'Setting plugins to %r' % value)
        self._plugins = filter(self.isValidPlugin, value)

    @staticmethod
    def isValidPlugin(pluginName):
        """Check if a plugin is valid (exists)"""
        if pluginName not in Subliminal.listExistingPlugins():
            logger.error(u'Plugin %s does not exist' % pluginName)
            return False
        return True

    @staticmethod
    def isAPIBasedPlugin(pluginName):
        """Check if a plugin is API-based"""
        if not getattr(plugins, pluginName).api_based:
            return False
        return True

    # getters/setters for the property _languages and _plugins
    languages = property(get_languages, set_languages)
    plugins = property(get_plugins, set_plugins)

    def listSubtitles(self, entries):
        """
        Searches subtitles within the active plugins and returns all found matching subtitles.
        entries can be:
            - filepaths
            - folderpaths (N.B. internal recursive search function will be used)
            - filenames
        """
        search_results = []
        if isinstance(entries, basestring):
            entries = [ek.fixStupidEncodings(entries)]
        elif not isinstance(entries, list):
            raise TypeError('Entries should be a list or a string')
        for e in entries:
            search_results.extend(self._recursiveSearch(e))
        taskCount = 0
        for (l, f) in search_results:
            taskCount += self.searchSubtitlesThreaded(f, l)
        subtitles = []
        for i in range(taskCount):
            subtitles.extend(self.resultQueue.get(timeout=10))
        return subtitles

    @staticmethod
    def arrangeSubtitles(subtitles):
        """Arrange subtitles in a handy dict by filename, language and plugin"""
        arrangedSubtitles = {}
        for (filename, subsByFilename) in groupby(sorted(subtitles, key=lambda x: x["filename"]), lambda x: x["filename"]):
            arrangedSubtitles[filename] = {}
            for (language, subsByFilenameByLanguage) in groupby(sorted(subsByFilename, key=lambda x: x["lang"]), lambda x: x["lang"]):
                arrangedSubtitles[filename][language] = {}
                for (plugin, subsByFilenameByLanguageByPlugin) in groupby(sorted(subsByFilenameByLanguage, key=lambda x: x["plugin"]), lambda x: x["plugin"]):
                    arrangedSubtitles[filename][language][plugin] = sorted(list(subsByFilenameByLanguageByPlugin))
        return arrangedSubtitles

    def sortSubtitlesRaw(self, subtitles):
        """Sort subtitles using user defined languages and plugins"""
        return sorted(subtitles, cmp=self._cmpSubtitles)

    def _cmpSubtitles(self, x, y):
        """
        Compares 2 subtitles elements x and y. Returns -1 if x < y, 0 if =, 1 if >
        Use filename, languages and plugin comparison
        """
        filenames = sorted([x['filename'], y['filename']])
        if x['filename'] != y['filename'] and filenames.index(x['filename']) < filenames(y['filename']):
            return - 1
        if x['filename'] != y['filename'] and filenames.index(x['filename']) > filenames(y['filename']):
            return 1
        if self._languages and self._languages.index(x['lang']) < self._languages.index(y['lang']):
            return - 1
        if self._languages and self._languages.index(x['lang']) > self._languages.index(y['lang']):
            return 1
        if self._plugins.index(x['plugin']) < self._plugins.index(y['plugin']):
            return - 1
        if self._plugins.index(x['plugin']) > self._plugins.index(y['plugin']):
            return 1
        return 0

    def searchSubtitlesThreaded(self, filenames, languages):
        """
        Makes workers search for subtitles in different languages for multiple filenames and puts the result in the result queue.
        Aslo split the work in multiple tasks
        When the function returns, all the results may not be available yet!
        """
        logger.info(u"Searching subtitles for %s with languages %s" % (filenames, languages))
        tasks = []
        for pluginName in self._plugins:
            try:
                plugin = getattr(plugins, pluginName)(self.getConfigDict())
            except:
                logger.debug(traceback.print_exc())
                continue
            # split tasks if the plugin can't handle multi-thing queries
            tasks.extend(plugin.splitTask({'task': 'list', 'plugin': pluginName, 'languages': languages, 'filenames': filenames, 'config': self.getConfigDict()}))
        for t in tasks:
            self.taskQueue.put(t)
        return len(tasks)

    def downloadSubtitlesThreaded(self, subtitles):
        """
        Makes workers download subtitles and puts the result in the result queue.
        When the function returns, all the results may not be available yet!
        """
        # 1 task per file if not multi, 1 task per file and per language if multi
        taskCount = 0
        for (filename, subsByFilename) in groupby(sorted(subtitles, key=lambda x: x["filename"]), lambda x: x["filename"]):
            if not self.multi:
                self.taskQueue.put({'task': 'download', 'subtitle': sorted(list(subsByFilename), cmp=self._cmpSubtitles), 'config': self.getConfigDict()})
                taskCount += 1
                continue
            for (language, subsByFilenameByLanguage) in groupby(sorted(subsByFilename, key=lambda x: x["lang"]), lambda x: x["lang"]):
                self.taskQueue.put({'task': 'download', 'subtitle': sorted(list(subsByFilenameByLanguage), cmp=self._cmpSubtitles), 'config': self.getConfigDict()})
                taskCount += 1
        return taskCount

    def downloadSubtitles(self, entries):
        """Download subtitles recursivly in entries"""
        subtitles = self.listSubtitles(entries)
        taskCount = self.downloadSubtitlesThreaded(subtitles)
        paths = []
        for i in range(taskCount):
            paths.append(self.resultQueue.get(timeout=10))
        return paths

    def _recursiveSearch(self, entry, depth=0):
        """
        Searches files in the entry
        This will output a list of tuples (filename, languages)
        """
        if depth > self.max_depth and self.max_depth != 0:  # we do not want to search the whole file system except if max_depth = 0
            return []
        if ek.ek(os.path.isfile, entry):  # a file? scan it
            if depth != 0:  # only check for valid format if recursing, trust the user
                mimetypes.add_type("video/x-matroska", ".mkv")
                mimetype = mimetypes.guess_type(entry)[0]
                if mimetype not in SUPPORTED_FORMATS:
                    return []
            basepath = ek.fixStupidEncodings(ek.ek(os.path.splitext, entry)[0])
            # check for .xx.srt if needed
            if self.multi and self.languages:
                if self.force:
                    return [(self.languages, [ek.ek(os.path.normpath, entry)])]
                needed_languages = self.languages[:]
                for l in self.languages:
                    if ek.ek(os.path.exists, basepath + '.%s.srt' % l):
                        logger.info(u"Skipping language %s for file %s as it already exists. Use the --force option to force the download" % (l, entry))
                        needed_languages.remove(l)
                if needed_languages:
                    return [(needed_languages, [ek.ek(os.path.normpath, entry)])]
                return []
            # single subtitle download: .srt
            if self.force or not ek.ek(os.path.exists, basepath + '.srt'):
                return [(self.languages, [ek.ek(os.path.normpath, entry)])]
        if ek.ek(os.path.isdir, entry):  # a dir? recurse
            #TODO if hidden folder, don't keep going (how to handle windows/mac/linux ?)
            files = []
            for e in ek.ek(os.listdir, entry):
                files.extend(self._recursiveSearch(ek.ek(os.path.join, entry, e), depth + 1))
            files.sort()
            grouped_files = []
            for languages, group in groupby(files, lambda t: t[0]):
                filenames = []
                for t in group:
                    filenames.extend(t[1])
                grouped_files.append((languages, filenames))
            return grouped_files
        return []  # anything else, nothing.

    def startWorkers(self):
        """Create a pool of workers and start them"""
        self.pool = []
        for i in range(self.workers):
            worker = PluginWorker.PluginWorker(self.taskQueue, self.resultQueue)
            worker.start()
            self.pool.append(worker)
            logger.debug(u"Worker %s added to the pool" % worker.name)

    def sendStopSignal(self):
        """Send a stop signal the pool of workers (poison pill)"""
        logger.debug(u"Sending %d poison pills into the task queue" % self.workers)
        for i in range(self.workers):
            self.taskQueue.put(None)

    def stopWorkers(self):
        """Stop workers using a stop signal and wait for them to terminate properly"""
        self.sendStopSignal()
        for worker in self.pool:
            worker.join()

    def getConfigDict(self):
        """Produce a dict with configuration items. Used by plugins to read configuration"""
        config = {}
        config['multi'] = self.multi
        config['cache_dir'] = self.cache_dir
        if self.plugins_config and 'subtitlesource_key' in self.plugins_config:
            config['subtitlesource_key'] = self.plugins_config['subtitlesource_key']
        config['force'] = self.force
        config['files_mode'] = self.files_mode
        return config
