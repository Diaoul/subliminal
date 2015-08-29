# -*- coding: utf-8 -*-
__title__ = 'subliminal'
__version__ = '1.1.0.dev0'
__author__ = 'Antoine Bertin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015, Antoine Bertin'

import logging

from .api import (ProviderPool, check_video, provider_manager, download_best_subtitles, download_subtitles,
                  list_subtitles, save_subtitles)
from .cache import region
from .exceptions import Error, ProviderError
from .providers import Provider
from .subtitle import Subtitle, compute_score
from .video import SUBTITLE_EXTENSIONS, VIDEO_EXTENSIONS, Episode, Movie, Video, scan_video, scan_videos

logging.getLogger(__name__).addHandler(logging.NullHandler())
