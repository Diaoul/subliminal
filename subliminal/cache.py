# -*- coding: utf-8 -*-
import inspect
import dogpile.cache


#: Subliminal's cache version
CACHE_VERSION = 1


def subliminal_key_generator(namespace, fn, to_str=dogpile.cache.compat.string_type):
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


#: The dogpile.cache region
region = dogpile.cache.make_region(function_key_generator=subliminal_key_generator)
