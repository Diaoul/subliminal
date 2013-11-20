# -*- coding: utf-8 -*-
import inspect
from dogpile.cache import make_region  # @UnresolvedImport
from dogpile.cache.backends.file import AbstractFileLock  # @UnresolvedImport
from dogpile.cache.compat import string_type  # @UnresolvedImport
from dogpile.core.readwrite_lock import ReadWriteMutex  # @UnresolvedImport


#: Subliminal's cache version
CACHE_VERSION = 1


def subliminal_key_generator(namespace, fn, to_str=string_type):
    """Add a :data:`CACHE_VERSION` to dogpile.cache's default function_key_generator"""
    if namespace is None:
        namespace = '%d:%s:%s' % (CACHE_VERSION, fn.__module__, fn.__name__)
    else:
        namespace = '%d:%s:%s|%s' % (CACHE_VERSION, fn.__module__, fn.__name__, namespace)

    args = inspect.getargspec(fn)
    has_self = args[0] and args[0][0] in ('self', 'cls')

    def generate_key(*args, **kw):
        if kw:
            raise ValueError('Keyword arguments not supported')
        if has_self:
            args = args[1:]
        return namespace + '|' + ' '.join(map(to_str, args))
    return generate_key


class MutexLock(AbstractFileLock):
    """:class:`MutexLock` is a thread-based rw lock based on :class:`dogpile.core.ReadWriteMutex`"""
    def __init__(self, filename):
        self.mutex = ReadWriteMutex()

    def acquire_read_lock(self, wait):
        ret = self.mutex.acquire_read_lock(wait)
        return wait or ret

    def acquire_write_lock(self, wait):
        ret = self.mutex.acquire_write_lock(wait)
        return wait or ret

    def release_read_lock(self):
        return self.mutex.release_read_lock()

    def release_write_lock(self):
        return self.mutex.release_write_lock()


#: The dogpile.cache region (long-lived)
region = make_region(function_key_generator=subliminal_key_generator)

#: The dogpile.cache region for :meth:`~subliminal.providers.Provider.query` (short-lived)
query_region = make_region(function_key_generator=subliminal_key_generator)
