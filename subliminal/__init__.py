# -*- coding: utf-8 -*-
__title__ = 'subliminal'
__version__ = '2.0.dev0'
__short_version__ = '.'.join(__version__.split('.')[:2])
__author__ = 'Antoine Bertin'
__license__ = 'MIT'
__copyright__ = 'Copyright 2016, Antoine Bertin'

import logging

from .core import (AsyncProviderPool, ProviderPool, check_video, download_best_subtitles, download_subtitles,
                   list_subtitles, provider_manager, refiner_manager, save_subtitles)
from .cache import region
from .exceptions import Error, ProviderError
from .providers import Provider
from .score import compute_score
from .subtitle import Subtitle
from .video import SUBTITLE_EXTENSIONS, VIDEO_EXTENSIONS, Episode, Movie, Video, scan_video, scan_videos

logging.getLogger(__name__).addHandler(logging.NullHandler())
