# -*- coding: utf-8 -*-
__title__ = 'subliminal'
__version__ = '0.7.4'
__author__ = 'Antoine Bertin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2013 Antoine Bertin'

import logging
from .api import PROVIDERS_ENTRY_POINT, list_subtitles, download_subtitles, download_best_subtitles
from .cache import MutexLock, region as cache_region
from .exceptions import Error, ProviderError, ProviderConfigurationError, ProviderNotAvailable, InvalidSubtitle
from .subtitle import Subtitle
from .video import VIDEO_EXTENSIONS, SUBTITLE_EXTENSIONS, Video, Episode, Movie, scan_videos, scan_video


logging.getLogger(__name__).addHandler(logging.NullHandler())
