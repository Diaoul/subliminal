# -*- coding: utf-8 -*-
# Copyright 2012 Nicolas Wack <wackou@gmail.com>
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
#

import os.path
from collections import defaultdict
import threading
from functools import wraps
import atexit
import logging
try:
    import cPickle as pickle
except ImportError:
    import pickle

logger = logging.getLogger(__name__)

global_cache = {}
global_cache_lock = threading.RLock()


def clear_cache():
    logger.info('Cache: clearing memory cache')
    global global_cache
    global_cache = {}


def destroy_cache():
    with global_cache_lock:
        for cache_dir, service_name in global_cache:
            save(cache_dir, service_name)


def init_cache(cache_dir='', service_name='unspecified'):
    logger.debug('Initializing cache for service %s, dir = "%s"' % (service_name, cache_dir))
    with global_cache_lock:
        if (cache_dir, service_name) in global_cache:
            # already loaded
            return

        # register only once, when loading the first cache
        if not global_cache:
            atexit.register(destroy_cache)

        load(cache_dir, service_name)


def cache_location(cache_dir, service_name):
    return os.path.join(cache_dir, 'subliminal_%s.cache' % service_name)


def load(cache_dir, service_name):
    filename = cache_location(cache_dir, service_name)
    logger.debug('Cache: loading cache from %s' % filename)
    global_cache[(cache_dir, service_name)] = defaultdict(dict)
    with global_cache_lock:
        try:
            global_cache[(cache_dir, service_name)] = pickle.load(open(filename, 'rb'))
        except IOError:
            logger.warning('Cache: Cache file "%s" doesn\'t exist' % filename)
        except EOFError:
            logger.error('Cache: cache file "%s" is corrupted... Removing it.' % filename)
            os.remove(filename)


def save(cache_dir, service_name):
    filename = cache_location(cache_dir, service_name)
    logger.debug('Cache: saving cache to %s' % filename)
    with global_cache_lock:
        pickle.dump(global_cache[(cache_dir, service_name)], open(filename, 'wb'))



def cache_key(service):
    return (service.config.cache_dir, service.__class__.__name__)

def cached_func_key(service, func):
    cls = service.__class__
    return ('%s.%s' % (cls.__module__, cls.__name__), func.__name__)

def cache_for(service, func, args, result):
    # no need to lock here, dict ops are atomic
    cache_id = cache_key(service)
    func_key = cached_func_key(service, func)
    global_cache[cache_id][func_key][args] = result

def cached_value(service, func, args):
    """raises KeyError if not found"""
    # no need to lock here, dict ops are atomic
    cache_id = cache_key(service)
    func_key = cached_func_key(service, func)
    return global_cache[cache_id][func_key][args]



def cachedmethod(function):
    """Decorator to make a method use the cache.

    WARNING: this can NOT be used with static functions, it has to be used on
    methods of some class."""

    @wraps(function)
    def cached(*args):
        # we need to remove the first element of args for the key, as it is the
        # instance pointer and we don't want the cache to know which instance
        # called it, it is shared among all instances of the same class
        cache_id = cache_key(args[0])
        func_key = cached_func_key(args[0], function)
        func_cache = global_cache[cache_id][func_key]
        key = args[1:]

        if key in func_cache:
            result = func_cache[key]
            logger.debug('Using cached value for %s(%s), returns: %s' % (func_key, key, result))
            return result

        result = function(*args)

        # note: another thread could have already cached a value in the
        # meantime, but that's ok as we prefer to keep the latest value in
        # the cache
        func_cache[key] = result

        return result

    return cached
