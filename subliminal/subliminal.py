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

import threading
from itertools import groupby
from classes import DownloadTask, ListTask, PoisonPillTask, LanguageError, PluginError
import Queue
import logging
import mimetypes
import os
import plugins
import traceback


# be nice
try:
    from logging import NullHandler
except ImportError:

    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
logger = logging.getLogger('subliminal')
logger.addHandler(NullHandler())

# const
FORMATS = ['video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/mp4']
LANGUAGES = ['aa', 'ab', 'ae', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi',
    'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv', 'dz', 'ee',
    'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv',
    'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ia', 'id', 'ie', 'ig', 'ii', 'ik', 'io', 'is', 'it', 'iu',
    'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb',
    'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my', 'na',
    'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps',
    'pt', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq',
    'sr', 'ss', 'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw',
    'ty', 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zu']  # ISO 639-1
PLUGINS = ['Addic7ed', 'BierDopje', 'OpenSubtitles', 'SubsWiki', 'Subtitulos', 'TheSubDB']
API_PLUGINS = filter(lambda p: getattr(plugins, p).api_based, PLUGINS)


class Subliminal(object):
    """Main Subliminal class"""

    def __init__(self, cache_dir=False, workers=4, multi=False, force=False, max_depth=3, autostart=False, files_mode=-1):
        # set default values
        self.multi = multi
        self.force = force
        self.max_depth = max_depth
        self.cache_dir = None
        self.taskQueue = Queue.Queue()
        self.resultQueue = Queue.Queue()
        self._languages = None
        self._plugins = API_PLUGINS
        self.workers = workers
        self.files_mode = files_mode
        if autostart:
            self.startWorkers()
        # handle cache directory preferences
        try:
            if cache_dir:  # custom configuration file
                self.cache_dir = cache_dir
                if not os.path.isdir(self.cache_dir):  # custom file doesn't exist, create it
                    os.mkdir(self.cache_dir)
                    logger.debug(u'Creating cache directory: %s' % self.cache_dir)
        except:
            self.cache_dir = None
            logger.error(u'Failed to use the cache directory, continue without it')

    def get_languages(self):
        """Getter for languages"""
        return self._languages

    def set_languages(self, languages):
        """Setter for languages"""
        logger.debug(u'Setting languages to %r' % languages)
        for l in languages:
            if l not in LANGUAGES:
                raise LanguageError(l)
        self._languages = languages

    def get_plugins(self):
        """Getter for plugins"""
        return self._plugins

    def set_plugins(self, plugins):
        """Setter for plugins"""
        logger.debug(u'Setting plugins to %r' % plugins)
        for p in plugins:
            if p not in PLUGINS:
                raise PluginError(p)
        self._plugins = plugins

    # getters/setters for the property _languages and _plugins
    languages = property(get_languages, set_languages)
    plugins = property(get_plugins, set_plugins)

    def listSubtitles(self, entries):
        """
        Search subtitles within the plugins and return all found subtitles in a list of Subtitle object.
        No need to worry about workers.

        Attributes:
            entries -- unicode filepath or folderpath of video file or a list of that"""
        # valid argument
        if isinstance(entries, unicode):
            entries = [entries]
        # find files and languages
        search_results = []
        for e in entries:
            search_results.extend(self._recursiveSearch(e))
        # find subtitles
        task_count = 0
        for (filepath, languages) in search_results:
            logger.debug(u'Listing subtitles for %s with languages %r in plugins %r' % (filepath, languages, self._plugins))
            for plugin in self._plugins:
                self.taskQueue.put(ListTask(filepath, languages, plugin, self.getConfigDict()))
                task_count += 1
        subtitles = []
        for _ in range(task_count):
            subtitles.extend(self.resultQueue.get(timeout=4))
        return subtitles

    def downloadSubtitles(self, entries):
        """
        Download subtitles using the plugins preferences and languages. Also use internal algorithm to find
        the best match inside a plugin.
        No need to worry about workers.

        Attributes:
            entries -- unicode filepath or folderpath of video file or a list of that"""
        subtitles = self.listSubtitles(entries)
        task_count = 0
        for (_, subsBySource) in groupby(sorted(subtitles, key=lambda x: x.source), lambda x: x.source):
            if not self.multi:
                self.taskQueue.put(DownloadTask(sorted(list(subsBySource), cmp=self._cmpSubtitles)))
                task_count += 1
                continue
            for (__, subsBySourceByLanguage) in groupby(sorted(subsBySource, key=lambda x: x.language), lambda x: x.language):
                self.taskQueue.put(DownloadTask(sorted(list(subsBySourceByLanguage), cmp=self._cmpSubtitles)))
                task_count += 1
        paths = []
        for _ in range(task_count):
            paths.append(self.resultQueue.get(timeout=10))
        return paths

    def _cmpSubtitles(self, x, y):
        """Compares 2 subtitles elements x and y using source, languages and plugin"""
        sources = sorted([x.source, y.source])
        if x.source != y.source and sources.index(x.source) < sources(y.source):
            return - 1
        if x.source != y.source and sources.index(x.source) > sources(y.source):
            return 1
        if self._languages and self._languages.index(x.language) < self._languages.index(y.language):
            return - 1
        if self._languages and self._languages.index(x.language) > self._languages.index(y.language):
            return 1
        if self._plugins.index(x.plugin) < self._plugins.index(y.plugin):
            return - 1
        if self._plugins.index(x.plugin) > self._plugins.index(y.plugin):
            return 1
        return 0

    def _recursiveSearch(self, entry, depth=0):
        """Search files in the entry and return them as a list of tuples (filename, languages)"""
        if depth > self.max_depth and self.max_depth != 0:  # we do not want to search the whole file system except if max_depth = 0
            return []
        if os.path.isfile(entry):  # a file? scan it
            if depth != 0:  # trust the user: only check for valid format if recursing
                mimetypes.add_type("video/x-matroska", ".mkv")
                mimetype = mimetypes.guess_type(entry)[0]
                if mimetype not in FORMATS:
                    return []
            basepath = os.path.splitext(entry)[0]
            # check for .xx.srt if needed
            if self.multi and self.languages:
                if self.force:
                    return [(os.path.normpath(entry), self.languages)]
                needed_languages = self.languages[:]
                for l in self.languages:
                    if os.path.exists(basepath + '.%s.srt' % l):
                        logger.info(u'Skipping language %s for file %s as it already exists. Use the --force option to force the download' % (l, entry))
                        needed_languages.remove(l)
                if needed_languages:
                    return [(os.path.normpath(entry), needed_languages)]
                return []
            # single subtitle download: .srt
            if self.force or not os.path.exists(basepath + '.srt'):
                return [(os.path.normpath(entry), self.languages)]
        if os.path.isdir(entry):  # a dir? recurse
            files = []
            for e in os.listdir(entry):
                files.extend(self._recursiveSearch(os.path.join(entry, e), depth + 1))
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
        for _ in range(self.workers):
            worker = PluginWorker(self.taskQueue, self.resultQueue)
            worker.start()
            self.pool.append(worker)
            logger.debug(u"Worker %s added to the pool" % worker.name)

    def sendStopSignal(self):
        """Send a stop signal the pool of workers (poison pill)"""
        logger.debug(u"Sending %d poison pills into the task queue" % self.workers)
        for _ in range(self.workers):
            self.taskQueue.put(PoisonPillTask())

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
        config['files_mode'] = self.files_mode
        return config


class PluginWorker(threading.Thread):
    """Threaded plugin worker"""
    def __init__(self, taskQueue, resultQueue):
        threading.Thread.__init__(self)
        self.taskQueue = taskQueue
        self.resultQueue = resultQueue
        self.logger = logging.getLogger('subliminal.worker')

    def run(self):
        while True:
            task = self.taskQueue.get()
            if isinstance(task, PoisonPillTask):
                self.logger.debug(u'Poison pill received, terminating thread %s' % self.name)
                self.taskQueue.task_done()
                break
            result = []
            try:
                if isinstance(task, ListTask):
                    plugin = getattr(plugins, task.plugin)(task.config)
                    result = plugin.list(task.filepath, task.languages)
                elif isinstance(task, DownloadTask):
                    for subtitle in task.subtitles:
                        plugin = getattr(plugins, subtitle.plugin)()
                        try:
                            result = plugin.download(subtitle)
                            break
                        except:
                            self.logger.error(u'Could not download subtitle %r, skipping' % subtitle)
                            continue
            except:
                self.logger.error(u'Exception raised in worker %s' % self.name)
                self.logger.debug(traceback.print_exc())
            finally:
                self.resultQueue.put(result)
                self.taskQueue.task_done()
        self.logger.debug(u'Thread %s terminated' % self.name)


