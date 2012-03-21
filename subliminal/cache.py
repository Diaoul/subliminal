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

global_cache = defaultdict(dict)
global_cache_lock = threading.RLock()
global_cache_dir = ''

def default_cache_location():
    return os.path.join(global_cache_dir, 'subliminal.cache')


def clear_cache():
    logger.info('Cache: clearing memory cache')
    global global_cache
    global_cache = defaultdict(dict)

def destroy_cache():
    with global_cache_lock:
        save(default_cache_location())

def init_cache(cache_dir='', service_name='unspecified'):
    logger.debug('Initializing cache for service %s, dir = "%s"' % (service_name, cache_dir))
    with global_cache_lock:
        if global_cache:
            # already loaded
            return

        global global_cache_dir
        if cache_dir:
            global_cache_dir = cache_dir

        load(default_cache_location())

        atexit.register(destroy_cache)


def load(filename):
    logger.debug('Cache: loading cache from %s' % filename)
    global global_cache
    with global_cache_lock:
        try:
            global_cache = pickle.load(open(filename, 'rb'))
        except IOError:
            logger.warning('Cache: Cache file doesn\'t exist')
        except EOFError:
            logger.error('Cache: cache file is corrupted... Removing it.')
            os.remove(filename)

def save(filename):
    logger.debug('Cache: saving cache to %s' % filename)
    with global_cache_lock:
        pickle.dump(global_cache, open(filename, 'wb'))


def cache_for(func, args, result):
    # no need to lock here, dict ops are atomic
    func_key = str(func.im_class), func.__name__
    global_cache[func_key][args] = result

def cached_value(func, args):
    """raises KeyError if not found"""
    # no need to lock here, dict ops are atomic
    func_key = str(func.im_class), func.__name__
    return global_cache[func_key][args]



def cachedmethod(function):
    """Decorator to make a method use the cache.

    WARNING: this can NOT be used with static functions, it has to be used on
    methods of some class."""

    @wraps(function)
    def cached(*args):
        # we need to remove the first element of args for the key, as it is the
        # instance pointer and we don't want the cache to know which instance
        # called it, it is shared among all instances of the same class
        func_key = str(args[0].__class__), function.__name__
        func_cache = global_cache[func_key]
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
