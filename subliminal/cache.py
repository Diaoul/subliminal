# -*- coding: utf-8 -*-
# Copyright 2012 Antoine Bertin <diaoulael@gmail.com>
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
from dogpile.cache import make_region
from dogpile.cache.util import function_key_generator


# Fix for https://bitbucket.org/zzzeek/dogpile.cache/issue/12
def my_key_generator(namespace, fn):
    def generate_key(*args):
        key = function_key_generator(namespace, fn)(*args)
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        print key
        return key
    return generate_key

region = make_region(function_key_generator=my_key_generator)
