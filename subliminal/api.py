# -*- coding: utf-8 -*-
from collections import defaultdict
import io
import logging
import operator
import os.path
from pkg_resources import EntryPoint
import socket

from babelfish import Language
import requests
from stevedore import ExtensionManager

from .subtitle import compute_score, get_subtitle_path

logger = logging.getLogger(__name__)


class ProviderManager(ExtensionManager):
    """Manager for providers based on :class:`~stevedore.extension.ExtensionManager`.

    It allows loading of internal providers without setup and registering/unregistering additional providers.

    Loading is done in this order:

    * Entry point providers
    * Internal providers
    * Registered providers

    """
    internal_providers = [
      'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
      'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
      'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
      'subscenter = subliminal.providers.subscenter:SubsCenterProvider',
      'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
      'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
    ]

    def __init__(self):
        #: Registered providers with entry point syntax
        self.registered_providers = []

        super(ProviderManager, self).__init__('subliminal.providers')

    def _find_entry_points(self, namespace):
        # default entry points
        eps = super(ProviderManager, self)._find_entry_points(namespace)

        # internal entry points
        for iep in self.internal_providers:
            ep = EntryPoint.parse(iep)
            if ep.name not in [e.name for e in eps]:
                eps.append(ep)

        # registered entry points
        for rep in self.registered_providers:
            ep = EntryPoint.parse(rep)
            if ep.name not in [e.name for e in eps]:
                eps.append(ep)

        return eps

    def register(self, entry_point):
        """Register a provider

        :param str entry_point: provider to register (entry point syntax)
        :raise: ValueError if already registered

        """
        if entry_point in self.registered_providers:
            raise ValueError('Entry point already registered')

        ep = EntryPoint.parse(entry_point)
        if ep.name in self.names():
            raise ValueError('A provider with the same name already exist')

        ext = self._load_one_plugin(ep, False, (), {}, False)
        self.extensions.append(ext)
        if self._extensions_by_name is not None:
            self._extensions_by_name[ext.name] = ext
        self.registered_providers.insert(0, entry_point)

    def unregister(self, entry_point):
        """Unregister a provider

        :param str entry_point: provider to unregister (entry point syntax)

        """
        if entry_point not in self.registered_providers:
            raise ValueError('Entry point not registered')

        ep = EntryPoint.parse(entry_point)
        self.registered_providers.remove(entry_point)
        if self._extensions_by_name is not None:
            del self._extensions_by_name[ep.name]
        for i, ext in enumerate(self.extensions):
            if ext.name == ep.name:
                del self.extensions[i]
                break

provider_manager = ProviderManager()


class ProviderPool(object):
    """A pool of providers with the same API as a single :class:`~subliminal.providers.Provider`.

    It has a few extra features:

        * Lazy loads providers when needed and supports the :keyword:`with` statement to :meth:`terminate`
          the providers on exit.
        * Automatically discard providers on failure.

    :param list providers: name of providers to use, if not all.
    :param dict provider_configs: provider configuration as keyword arguments per provider name to pass when
        instanciating the :class:`~subliminal.providers.Provider`.

    """
    def __init__(self, providers=None, provider_configs=None):
        #: Name of providers to use
        self.providers = providers or provider_manager.names()

        #: Provider configuration
        self.provider_configs = provider_configs or {}

        #: Initialized providers
        self.initialized_providers = {}

        #: Discarded providers
        self.discarded_providers = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.terminate()

    def __getitem__(self, name):
        if name not in self.providers:
            raise KeyError
        if name not in self.initialized_providers:
            logger.info('Initializing provider %s', name)
            provider = provider_manager[name].plugin(**self.provider_configs.get(name, {}))
            provider.initialize()
            self.initialized_providers[name] = provider

        return self.initialized_providers[name]

    def __delitem__(self, name):
        if name not in self.initialized_providers:
            raise KeyError(name)

        try:
            logger.info('Terminating provider %s', name)
            self.initialized_providers[name].terminate()
        except (requests.Timeout, socket.timeout):
            logger.error('Provider %r timed out, improperly terminated', name)
        except:
            logger.exception('Provider %r terminated unexpectedly', name)

        del self.initialized_providers[name]

    def __iter__(self):
        return iter(self.initialized_providers)

    def list_subtitles(self, video, languages):
        """List subtitles.

        :param video: video to list subtitles for.
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to search for.
        :type languages: set of :class:`~babelfish.language.Language`
        :return: found subtitles.
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`

        """
        subtitles = []

        for name in self.providers:
            # check discarded providers
            if name in self.discarded_providers:
                logger.debug('Skipping discarded provider %r', name)
                continue

            # check video validity
            if not provider_manager[name].plugin.check(video):
                logger.info('Skipping provider %r: not a valid video', name)
                continue

            # check supported languages
            provider_languages = provider_manager[name].plugin.languages & languages
            if not provider_languages:
                logger.info('Skipping provider %r: no language to search for', name)
                continue

            # list subtitles
            logger.info('Listing subtitles with provider %r and languages %r', name, provider_languages)
            try:
                provider_subtitles = self[name].list_subtitles(video, provider_languages)
            except (requests.Timeout, socket.timeout):
                logger.error('Provider %r timed out, discarding it', name)
                self.discarded_providers.add(name)
                continue
            except:
                logger.exception('Unexpected error in provider %r, discarding it', name)
                self.discarded_providers.add(name)
                continue
            subtitles.extend(provider_subtitles)

        return subtitles

    def download_subtitle(self, subtitle):
        """Download `subtitle`'s :attr:`~subliminal.subtitle.Subtitle.content`.

        :param subtitle: subtitle to download.
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :return: `True` if the subtitle has been successfully downloaded, `False` otherwise.
        :rtype: bool

        """
        # check discarded providers
        if subtitle.provider_name in self.discarded_providers:
            logger.warning('Provider %r is discarded', subtitle.provider_name)
            return False

        logger.info('Downloading subtitle %r', subtitle)
        try:
            self[subtitle.provider_name].download_subtitle(subtitle)
        except (requests.Timeout, socket.timeout):
            logger.error('Provider %r timed out, discarding it', subtitle.provider_name)
            self.discarded_providers.add(subtitle.provider_name)
            return False
        except:
            logger.exception('Unexpected error in provider %r, discarding it', subtitle.provider_name)
            self.discarded_providers.add(subtitle.provider_name)
            return False

        # check subtitle validity
        if not subtitle.is_valid():
            logger.error('Invalid subtitle')
            return False

        return True

    def download_best_subtitles(self, subtitles, video, languages, min_score=0, hearing_impaired=False, only_one=False,
                                scores=None):
        """Download the best matching subtitles.

        :param subtitles: the subtitles to use.
        :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`
        :param video: video to download subtitles for.
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to download.
        :type languages: set of :class:`~babelfish.language.Language`
        :param int min_score: minimum score for a subtitle to be downloaded.
        :param bool hearing_impaired: hearing impaired preference.
        :param bool only_one: download only one subtitle, not one per language.
        :param dict scores: scores to use, if `None`, the :attr:`~subliminal.video.Video.scores` from the video are
            used.
        :return: downloaded subtitles.
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`

        """
        # sort subtitles by score
        scored_subtitles = sorted([(s, compute_score(s.get_matches(video, hearing_impaired=hearing_impaired), video,
                                                     scores=scores))
                                  for s in subtitles], key=operator.itemgetter(1), reverse=True)

        # download best subtitles, falling back on the next on error
        downloaded_subtitles = []
        for subtitle, score in scored_subtitles:
            # check score
            if score < min_score:
                logger.info('Score %d is below min_score (%d)', score, min_score)
                break

            # check downloaded languages
            if subtitle.language in set(s.language for s in downloaded_subtitles):
                logger.debug('Skipping subtitle: %r already downloaded', subtitle.language)
                continue

            # download
            logger.info('Downloading subtitle %r with score %d', subtitle, score)
            if self.download_subtitle(subtitle):
                downloaded_subtitles.append(subtitle)

            # stop when all languages are downloaded
            if set(s.language for s in downloaded_subtitles) == languages:
                logger.debug('All languages downloaded')
                break

            # stop if only one subtitle is requested
            if only_one:
                logger.debug('Only one subtitle downloaded')
                break

        return downloaded_subtitles

    def terminate(self):
        """Terminate all the :attr:`initialized_providers`."""
        logger.debug('Terminating initialized providers')
        for name in list(self.initialized_providers):
            del self[name]


def check_video(video, languages=None, age=None, undefined=False):
    """Perform some checks on the `video`.

    All the checks are optional. Return `False` if any of this check fails:

        * `languages` already exist in `video`'s :attr:`~subliminal.video.Video.subtitle_languages`.
        * `video` is older than `age`.
        * `video` has an `undefined` language in :attr:`~subliminal.video.Video.subtitle_languages`.

    :param video: video to check.
    :type video: :class:`~subliminal.video.Video`
    :param languages: desired languages.
    :type languages: set of :class:`~babelfish.language.Language`
    :param datetime.timedelta age: maximum age of the video.
    :param bool undefined: fail on existing undefined language.
    :return: `True` if the video passes the checks, `False` otherwise.
    :rtype: bool

    """
    # language test
    if languages and not (languages - video.subtitle_languages):
        logger.debug('All languages %r exist', languages)
        return False

    # age test
    if age and video.age > age:
        logger.debug('Video is older than %r', age)
        return False

    # undefined test
    if undefined and Language('und') in video.subtitle_languages:
        logger.debug('Undefined language found')
        return False

    return True


def list_subtitles(videos, languages, **kwargs):
    """List subtitles.

    The `videos` must pass the `languages` check of :func:`check_video`.

    All other parameters are passed onwards to the :class:`ProviderPool` constructor.

    :param videos: videos to list subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to search for.
    :type languages: set of :class:`~babelfish.language.Language`
    :return: found subtitles per video.
    :rtype: dict of :class:`~subliminal.video.Video` to list of :class:`~subliminal.subtitle.Subtitle`

    """
    listed_subtitles = defaultdict(list)

    # check videos
    checked_videos = []
    for video in videos:
        if not check_video(video, languages=languages):
            logger.info('Skipping video %r', video)
            continue
        checked_videos.append(video)

    # return immediatly if no video passed the checks
    if not checked_videos:
        return listed_subtitles

    # list subtitles
    with ProviderPool(**kwargs) as pool:
        for video in checked_videos:
            logger.info('Listing subtitles for %r', video)
            subtitles = pool.list_subtitles(video, languages - video.subtitle_languages)
            listed_subtitles[video].extend(subtitles)
            logger.info('Found %d subtitle(s)', len(subtitles))

    return listed_subtitles


def download_subtitles(subtitles, **kwargs):
    """Download :attr:`~subliminal.subtitle.Subtitle.content` of `subtitles`.

    All other parameters are passed onwards to the :class:`ProviderPool` constructor.

    :param subtitles: subtitles to download.
    :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`

    """
    with ProviderPool(**kwargs) as pool:
        for subtitle in subtitles:
            logger.info('Downloading subtitle %r', subtitle)
            pool.download_subtitle(subtitle)


def download_best_subtitles(videos, languages, min_score=0, hearing_impaired=False, only_one=False, scores=None,
                            **kwargs):
    """List and download the best matching subtitles.

    The `videos` must pass the `languages` and `undefined` (`only_one`) checks of :func:`check_video`.

    All other parameters are passed onwards to the :class:`ProviderPool` constructor.

    :param videos: videos to download subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to download.
    :type languages: set of :class:`~babelfish.language.Language`
    :param int min_score: minimum score for a subtitle to be downloaded.
    :param bool hearing_impaired: hearing impaired preference.
    :param bool only_one: download only one subtitle, not one per language.
    :param dict scores: scores to use, if `None`, the :attr:`~subliminal.video.Video.scores` from the video are used.
    :return: downloaded subtitles per video.
    :rtype: dict of :class:`~subliminal.video.Video` to list of :class:`~subliminal.subtitle.Subtitle`

    """
    downloaded_subtitles = defaultdict(list)

    # check videos
    checked_videos = []
    for video in videos:
        if not check_video(video, languages=languages, undefined=only_one):
            logger.info('Skipping video %r', video)
            continue
        checked_videos.append(video)

    # return immediatly if no video passed the checks
    if not checked_videos:
        return downloaded_subtitles

    # download best subtitles
    with ProviderPool(**kwargs) as pool:
        for video in checked_videos:
            logger.info('Downloading best subtitles for %r', video)
            subtitles = pool.download_best_subtitles(pool.list_subtitles(video, languages - video.subtitle_languages),
                                                     video, languages, min_score=min_score,
                                                     hearing_impaired=hearing_impaired, only_one=only_one,
                                                     scores=scores)
            logger.info('Downloaded %d subtitle(s)', len(subtitles))
            downloaded_subtitles[video].extend(subtitles)

    return downloaded_subtitles


def save_subtitles(video, subtitles, single=False, directory=None, encoding=None):
    """Save subtitles on filesystem.

    Subtitles are saved in the order of the list. If a subtitle with a language has already been saved, other subtitles
    with the same language are silently ignored.

    The extension used is `.lang.srt` by default or `.srt` is `single` is `True`, with `lang` being the IETF code for
    the :attr:`~subliminal.subtitle.Subtitle.language` of the subtitle.

    :param video: video of the subtitles.
    :type video: :class:`~subliminal.video.Video`
    :param subtitles: subtitles to save.
    :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`
    :param bool single: save a single subtitle, default is to save one subtitle per language.
    :param str directory: path to directory where to save the subtitles, default is next to the video.
    :param str encoding: encoding in which to save the subtitles, default is to keep original encoding.
    :return: the saved subtitles
    :rtype: list of :class:`~subliminal.subtitle.Subtitle`

    """
    saved_subtitles = []
    for subtitle in subtitles:
        # check content
        if subtitle.content is None:
            logger.error('Skipping subtitle %r: no content', subtitle)
            continue

        # check language
        if subtitle.language in set(s.language for s in saved_subtitles):
            logger.debug('Skipping subtitle %r: language already saved', subtitle)
            continue

        # create subtitle path
        subtitle_path = get_subtitle_path(video.name, None if single else subtitle.language)
        if directory is not None:
            subtitle_path = os.path.join(directory, os.path.split(subtitle_path)[1])

        # save content as is or in the specified encoding
        logger.info('Saving %r to %r', subtitle, subtitle_path)
        if encoding is None:
            with io.open(subtitle_path, 'wb') as f:
                f.write(subtitle.content)
        else:
            with io.open(subtitle_path, 'w', encoding=encoding) as f:
                f.write(subtitle.text)
        saved_subtitles.append(subtitle)

        # check single
        if single:
            break

    return saved_subtitles
