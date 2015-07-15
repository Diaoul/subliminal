# -*- coding: utf-8 -*-
import datetime

from dogpile.cache import make_region


#: Subliminal's cache version
CACHE_VERSION = 1

#: Expiration time for show caching
SHOW_EXPIRATION_TIME = datetime.timedelta(weeks=3).total_seconds()

#: Expiration time for episode caching
EPISODE_EXPIRATION_TIME = datetime.timedelta(days=3).total_seconds()


region = make_region()
