"""Subliminal."""

from __future__ import annotations

__title__: str = 'subliminal'
__version__: str = '2.2.1'
__short_version__: str = '.'.join(__version__.split('.')[:2])
__author__: str = 'Antoine Bertin'
__license__: str = 'MIT'
__copyright__: str = 'Copyright 2016, Antoine Bertin'

import logging

from .cache import region
from .core import (
    AsyncProviderPool,
    ProviderPool,
    check_video,
    download_best_subtitles,
    download_subtitles,
    list_subtitles,
    refine,
    save_subtitles,
    scan_video,
    scan_videos,
)
from .exceptions import Error, ProviderError
from .extensions import provider_manager, refiner_manager
from .providers import Provider
from .score import compute_score, get_scores
from .subtitle import SUBTITLE_EXTENSIONS, Subtitle
from .video import VIDEO_EXTENSIONS, Episode, Movie, Video

logging.getLogger(__name__).addHandler(logging.NullHandler())


__all__ = [
    'region',
    'AsyncProviderPool',
    'ProviderPool',
    'check_video',
    'download_best_subtitles',
    'download_subtitles',
    'list_subtitles',
    'refine',
    'save_subtitles',
    'scan_video',
    'scan_videos',
    'Error',
    'ProviderError',
    'provider_manager',
    'refiner_manager',
    'Provider',
    'compute_score',
    'get_scores',
    'SUBTITLE_EXTENSIONS',
    'Subtitle',
    'VIDEO_EXTENSIONS',
    'Episode',
    'Movie',
    'Video',
]
