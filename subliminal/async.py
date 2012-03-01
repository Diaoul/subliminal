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
from .core import (consume_task, LANGUAGE_INDEX, SERVICE_INDEX, SERVICE_CONFIDENCE,
    MATCHING_CONFIDENCE, SERVICES, create_list_tasks, create_download_tasks)
from .languages import list_languages
from .tasks import StopTask
import Queue
import logging
import threading


logger = logging.getLogger(__name__)


class Worker(threading.Thread):
    """Consume tasks and put the result in the queue"""
    def __init__(self, tasks, results):
        threading.Thread.__init__(self)
        self.tasks = tasks
        self.results = results
        self.services = {}

    def run(self):
        while 1:
            result = []
            try:
                task = self.tasks.get(block=True)
                if isinstance(task, StopTask):
                    break
                result = consume_task(task, self.services)
                self.results.put(result)
            except:
                logger.error(u'Exception raised in worker %s' % self.name, exc_info=True)
            finally:
                self.tasks.task_done()
        self.terminate()
        logger.debug(u'Thread %s terminated' % self.name)

    def terminate(self):
        """Terminate instantiated services"""
        for service_name, service in self.services.iteritems():
            try:
                service.terminate()
            except:
                logger.error(u'Exception raised when terminating service %s' % service_name, exc_info=True)


class Pool(object):
    """Pool of workers"""
    def __init__(self, size):
        self.tasks = Queue.Queue()
        self.results = Queue.Queue()
        self._workers = []
        for _ in range(size):
            self._workers.append(Worker(self.tasks, self.results))

    def __enter(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        self.join()

    def start(self):
        """Start workers"""
        for worker in self._workers:
            worker.start()

    def stop(self):
        """Stop workers"""
        for _ in self._workers:
            self.tasks.put(StopTask())

    def join(self):
        """Join the task queue"""
        self.tasks.join()

    def collect(self):
        """Collect available results

        :return: results of tasks
        :rtype: list of :class:`~subliminal.tasks.Task`

        """
        results = []
        while 1:
            try:
                result = self.results.get(block=False)
                results.append(result)
            except Queue.Empty:
                break
        return results

    def list_subtitles(self, entries, languages=None, services=None, cache_dir=None, max_depth=3, force=True, multi=False):
        #TODO: continue this
        services = services or SERVICES
        languages = set(languages or list_languages(1))
        if isinstance(entries, basestring):
            entries = [entries]
        if any([not isinstance(e, unicode) for e in entries]):
            logger.warning(u'Not all entries are unicode')
        services = {}
        tasks = create_list_tasks(entries, languages, services, force, multi, cache_dir, max_depth)
        for task in tasks:
            self.tasks.put(task)

    def download_subtitles(self, entries, languages=None, services=None, cache_dir=None, max_depth=3, force=True, multi=False, order=None):
        #TODO: continue this
        languages = set(languages or list_languages(1))
        if isinstance(entries, basestring):
            entries = [entries]
        order = order or [LANGUAGE_INDEX, SERVICE_INDEX, SERVICE_CONFIDENCE, MATCHING_CONFIDENCE]
        self.list_subtitles(entries, languages, services, cache_dir, max_depth, force, multi)
        self.join()
        list_results = self.collect()
        services = {}
        tasks = create_download_tasks(list_results, multi)
        for task in tasks:
            self.tasks.put(task)
