# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import collections
import io
import logging
import operator
import babelfish
import pkg_resources
from .exceptions import ProviderNotAvailable, InvalidSubtitle
from .subtitle import get_subtitle_path


logger = logging.getLogger(__name__)

#: Entry point for the providers
PROVIDERS_ENTRY_POINT = 'subliminal.providers'


def list_subtitles(videos, languages, providers=None, provider_configs=None):
    """List subtitles for `videos` with the given `languages` using the specified `providers`

    :param videos: videos to list subtitles for
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages of subtitles to search for
    :type languages: set of :class:`babelfish.Language`
    :param providers: providers to use for the search, if not all
    :type providers: list of string or None
    :param provider_configs: configuration for providers
    :type provider_configs: dict of provider name => provider constructor kwargs
    :return: found subtitles
    :rtype: dict of :class:`~subliminal.video.Video` => [:class:`~subliminal.subtitle.Subtitle`]

    """
    provider_configs = provider_configs or {}
    subtitles = collections.defaultdict(list)
    # filter videos
    videos = [v for v in videos if v.subtitle_languages & languages < languages]
    if not videos:
        logger.info('No video to download subtitles for with languages %r', languages)
        return subtitles
    subtitle_languages = set.intersection(*[v.subtitle_languages for v in videos])
    for provider_entry_point in pkg_resources.iter_entry_points(PROVIDERS_ENTRY_POINT):
        # filter and initialize provider
        if providers is not None and provider_entry_point.name not in providers:
            logger.debug('Skipping provider %r: not in the list', provider_entry_point.name)
            continue
        Provider = provider_entry_point.load()
        provider_languages = Provider.languages & languages - subtitle_languages
        if not provider_languages:
            logger.info('Skipping provider %r: no language to search for', provider_entry_point.name)
            continue
        provider_videos = [v for v in videos if Provider.check(v)]
        if not provider_videos:
            logger.info('Skipping provider %r: no video to search for', provider_entry_point.name)
            continue

        # list subtitles with the provider
        try:
            with Provider(**provider_configs.get(provider_entry_point.name, {})) as provider:
                for provider_video in provider_videos:
                    provider_video_languages = provider_languages - provider_video.subtitle_languages
                    if not provider_video_languages:
                        logger.debug('Skipping provider %r: no language to search for for video %r',
                                     provider_entry_point.name, provider_video)
                        continue
                    logger.info('Listing subtitles with provider %r for video %r with languages %r',
                                provider_entry_point.name, provider_video, provider_video_languages)
                    try:
                        provider_subtitles = provider.list_subtitles(provider_video, provider_video_languages)
                    except ProviderNotAvailable:
                        logger.warning('Provider %r is not available, discarding it', provider_entry_point.name)
                        break
                    except:
                        logger.exception('Unexpected error in provider %r', provider_entry_point.name)
                        continue
                    logger.info('Found %d subtitles', len(provider_subtitles))
                    subtitles[provider_video].extend(provider_subtitles)
        except ProviderNotAvailable:
            logger.warning('Provider %r is not available, discarding it', provider_entry_point.name)
    return subtitles


def download_subtitles(subtitles, provider_configs=None, single=False):
    """Download subtitles

    :param subtitles: subtitles to download
    :type subtitles: dict of :class:`~subliminal.video.Video` => [:class:`~subliminal.subtitle.Subtitle`]
    :param provider_configs: configuration for providers
    :type provider_configs: dict of provider name => provider constructor kwargs
    :param bool single: download with .srt extension if `True`, add language identifier otherwise

    """
    provider_configs = provider_configs or {}
    discarded_providers = set()
    providers_by_name = {ep.name: ep.load() for ep in pkg_resources.iter_entry_points(PROVIDERS_ENTRY_POINT)}
    initialized_providers = {}
    try:
        for video, video_subtitles in subtitles.items():
            languages = {subtitle.language for subtitle in video_subtitles}
            downloaded_languages = set()
            for subtitle in video_subtitles:
                # filter
                if subtitle.language in downloaded_languages:
                    continue
                if subtitle.provider_name in discarded_providers:
                    logger.debug('Skipping subtitle from discarded provider %r', subtitle.provider_name)
                    continue

                # initialize provider
                if subtitle.provider_name in initialized_providers:
                    provider = initialized_providers[subtitle.provider_name]
                else:
                    provider = providers_by_name[subtitle.provider_name](**provider_configs.get(subtitle.provider_name, {}))
                    try:
                        provider.initialize()
                    except ProviderNotAvailable:
                        logger.warning('Provider %r is not available, discarding it', subtitle.provider_name)
                        discarded_providers.add(subtitle.provider_name)
                        continue
                    initialized_providers[subtitle.provider_name] = provider

                # download subtitles
                subtitle_path = get_subtitle_path(video.name, None if single else subtitle.language)
                logger.info('Downloading subtitle %r into %r', subtitle, subtitle_path)
                try:
                    subtitle_text = provider.download_subtitle(subtitle)
                except ProviderNotAvailable:
                    logger.warning('Provider %r is not available, discarding it', subtitle.provider_name)
                    discarded_providers.add(subtitle.provider_name)
                    continue
                except InvalidSubtitle:
                    logger.info('Invalid subtitle, skipping it')
                    continue
                except:
                    logger.exception('Unexpected error in provider %r', subtitle.provider_name)
                    continue
                with io.open(subtitle_path, 'w', encoding='utf-8') as f:
                    f.write(subtitle_text)
                downloaded_languages.add(subtitle.language)
                if single or downloaded_languages == languages:
                    break
    finally:  # terminate providers
        for (provider_name, provider) in initialized_providers.items():
            try:
                provider.terminate()
            except ProviderNotAvailable:
                logger.warning('Provider %r is not available, unable to terminate', provider_name)
            except:
                logger.exception('Unexpected error in provider %r', provider_name)


def download_best_subtitles(videos, languages, providers=None, provider_configs=None, single=False, min_score=0,
                            hearing_impaired=False):
    """Download the best subtitles for `videos` with the given `languages` using the specified `providers`

    :param videos: videos to download subtitles for
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages of subtitles to download
    :type languages: set of :class:`babelfish.Language`
    :param providers: providers to use for the search, if not all
    :type providers: list of string or None
    :param provider_configs: configuration for providers
    :type provider_configs: dict of provider name => provider constructor kwargs
    :param bool single: download with .srt extension if `True`, add language identifier otherwise
    :param int min_score: minimum score for subtitles to download
    :param bool hearing_impaired: download hearing impaired subtitles

    """
    provider_configs = provider_configs or {}
    discarded_providers = set()
    downloaded_subtitles = collections.defaultdict(list)
    # filter videos
    videos = [v for v in videos if v.subtitle_languages & languages < languages
              and (not single or babelfish.Language('und') not in v.subtitle_languages)]
    if not videos:
        logger.info('No video to download subtitles for with languages %r', languages)
        return downloaded_subtitles
    # filter and initialize providers
    subtitle_languages = set.intersection(*[v.subtitle_languages for v in videos])
    initialized_providers = {}
    for provider_entry_point in pkg_resources.iter_entry_points(PROVIDERS_ENTRY_POINT):
        if providers is not None and provider_entry_point.name not in providers:
            logger.debug('Skipping provider %r: not in the list', provider_entry_point.name)
            continue
        Provider = provider_entry_point.load()
        if not Provider.languages & languages - subtitle_languages:
            logger.info('Skipping provider %r: no language to search for', provider_entry_point.name)
            continue
        if not [v for v in videos if Provider.check(v)]:
            logger.info('Skipping provider %r: no video to search for', provider_entry_point.name)
            continue
        provider = Provider(**provider_configs.get(provider_entry_point.name, {}))
        try:
            provider.initialize()
        except ProviderNotAvailable:
            logger.warning('Provider %r is not available, discarding it', provider_entry_point.name)
            continue
        initialized_providers[provider_entry_point.name] = provider
    try:
        for video in videos:
            # search for subtitles
            subtitles = []
            for provider_name, provider in initialized_providers.items():
                if provider.check(video):
                    if provider_name in discarded_providers:
                        logger.debug('Skipping discarded provider %r', provider_name)
                        continue
                    provider_video_languages = provider.languages & languages - video.subtitle_languages
                    if not provider_video_languages:
                        logger.debug('Skipping provider %r: no language to search for for video %r', provider_name,
                                     video)
                        continue
                    logger.info('Listing subtitles with provider %r for video %r with languages %r',
                                provider_name, video, provider_video_languages)
                    try:
                        provider_subtitles = provider.list_subtitles(video, provider_video_languages)
                    except ProviderNotAvailable:
                        logger.warning('Provider %r is not available, discarding it', provider_name)
                        discarded_providers.add(provider_name)
                        continue
                    except:
                        logger.exception('Unexpected error in provider %r', provider_name)
                        continue
                    logger.info('Found %d subtitles', len(provider_subtitles))
                    subtitles.extend(provider_subtitles)

            # find the best subtitles and download them
            downloaded_languages = video.subtitle_languages.copy()
            for subtitle, score in sorted([(s, s.compute_score(video)) for s in subtitles],
                                          key=operator.itemgetter(1), reverse=True):
                # filter
                if subtitle.provider_name in discarded_providers:
                    logger.debug('Skipping subtitle from discarded provider %r', subtitle.provider_name)
                    continue
                if subtitle.hearing_impaired != hearing_impaired:
                    logger.debug('Skipping subtitle: hearing impaired != %r', hearing_impaired)
                    continue
                if score < min_score:
                    logger.debug('Skipping subtitle: score < %d', min_score)
                    continue
                if subtitle.language in downloaded_languages:
                    logger.debug('Skipping subtitle: %r already downloaded', subtitle.language)
                    continue

                # download
                provider = initialized_providers[subtitle.provider_name]
                subtitle_path = get_subtitle_path(video.name, None if single else subtitle.language)
                logger.info('Downloading subtitle %r with score %d into %r', subtitle, score, subtitle_path)
                try:
                    subtitle_text = provider.download_subtitle(subtitle)
                    downloaded_subtitles[video].append(subtitle)
                except ProviderNotAvailable:
                    logger.warning('Provider %r is not available, discarding it', subtitle.provider_name)
                    discarded_providers.add(subtitle.provider_name)
                    continue
                except InvalidSubtitle:
                    logger.info('Invalid subtitle, skipping it')
                    continue
                except:
                    logger.exception('Unexpected error in provider %r', subtitle.provider_name)
                    continue
                with io.open(subtitle_path, 'w', encoding='utf-8') as f:
                    f.write(subtitle_text)
                downloaded_languages.add(subtitle.language)
                if single or downloaded_languages >= languages:
                    logger.debug('All languages downloaded')
                    break
    finally:  # terminate providers
        for (provider_name, provider) in initialized_providers.items():
            try:
                provider.terminate()
            except ProviderNotAvailable:
                logger.warning('Provider %r is not available, unable to terminate', provider_name)
            except:
                logger.exception('Unexpected error in provider %r', provider_name)
    return downloaded_subtitles
