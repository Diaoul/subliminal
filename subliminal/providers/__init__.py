# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import babelfish
import pkg_resources
import logging
from ..exceptions import ProviderNotAvailable, InvalidSubtitle
from ..video import Episode, Movie


logger = logging.getLogger(__name__)

#: Entry point for the providers
PROVIDER_ENTRY_POINT = 'subliminal.providers'

#: Available provider names
PROVIDERS = {entry_point.name.decode('utf-8') for entry_point in pkg_resources.iter_entry_points(PROVIDER_ENTRY_POINT)}


class Provider(object):
    """Base class for providers

    If any configuration is possible for the provider, like credentials, it must take place during instantiation

    :param \*\*kwargs: configuration
    :raise: :class:`~subliminal.exceptions.ProviderConfigurationError` if there is a configuration error

    """
    #: Supported BabelFish languages
    languages = set()

    #: Supported video types
    video_types = (Episode, Movie)

    #: Required hash, if any
    required_hash = None

    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        self.terminate()

    def initialize(self):
        """Initialize the provider

        Must be called when starting to work with the provider. This is the place for network initialization
        or login operations.

        .. note:
            This is called automatically if you use the :keyword:`with` statement


        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable

        """
        pass

    def terminate(self):
        """Terminate the provider

        Must be called when done with the provider. This is the place for network shutdown or logout operations.

        .. note:
            This is called automatically if you use the :keyword:`with` statement

        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        """
        pass

    @classmethod
    def check(cls, video):
        """Check if the `video` can be processed

        The video is considered invalid if not an instance of :attr:`video_types` or if the :attr:`required_hash` is
        not present in :attr:`~subliminal.video.Video`'s `hashes` attribute.

        :param video: the video to check
        :type video: :class:`~subliminal.video.Video`
        :return: `True` if the `video` and `languages` are valid, `False` otherwise
        :rtype: bool

        """
        if not isinstance(video, cls.video_types):
            return False
        if cls.required_hash is not None and cls.required_hash not in video.hashes:
            return False
        return True

    def query(self, languages, *args, **kwargs):
        """Query the provider for subtitles

        This method arguments match as much as possible the actual parameters for querying the provider

        :param languages: languages to search for
        :type languages: set of :class:`babelfish.Language`
        :param \*args: other required arguments
        :param \*\*kwargs: other optional arguments
        :return: the subtitles
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        :raise: :class:`~subliminal.exceptions.ProviderError` if something unexpected occured

        """
        raise NotImplementedError

    def list_subtitles(self, video, languages):
        """List subtitles for the `video` with the given `languages`

        This is a proxy for the :meth:`query` method. The parameters passed to the :meth:`query` method may
        vary depending on the amount of information available in the `video`

        :param video: video to list subtitles for
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to search for
        :type languages: set of :class:`babelfish.Language`
        :return: the subtitles
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        :raise: :class:`~subliminal.exceptions.ProviderError` if something unexpected occured

        """
        raise NotImplementedError

    def download_subtitle(self, subtitle):
        """Download the `subtitle` an fill its :attr:`~subliminal.subtitle.Subtitle.content` attribute with
        subtitle's text

        :param subtitle: subtitle to download
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        :raise: :class:`~subliminal.exceptions.InvalidSubtitle` if the downloaded subtitle is invalid
        :raise: :class:`~subliminal.exceptions.ProviderError` if something unexpected occured

        """
        raise NotImplementedError

    def __repr__(self):
        return '<%s [%r]>' % (self.__class__.__name__, self.video_types)


def get_provider(name):
    """Get a :class:`Provider` class by its name from the :data:`PROVIDER_ENTRY_POINT` entry point

    :param string name: name of the provider
    :return: the matching :class:`Provider`
    :rtype: :class:`Provider` class
    :raise: ValueError if the :class:`Provider` is not found

    """
    for entry_point in pkg_resources.iter_entry_points(PROVIDER_ENTRY_POINT):
        if entry_point.name.decode('utf-8') == name:
            return entry_point.load()
    raise ValueError('Provider %r not found' % name)


class ProviderManager(object):
    """A :class:`ProviderManager` makes the :class:`Provider` API available for a set of :class:`Provider`

    The :class:`ProviderManager` supports the ``with`` statement to :meth:`terminate` the providers

    :param providers: providers to use, if not all
    :type providers: list of string or None
    :param provider_configs: configuration for providers
    :type provider_configs: dict of provider name => provider constructor kwargs or None

    """
    def __init__(self, providers=None, provider_configs=None):
        self.provider_configs = provider_configs or {}
        self.providers = {provider_name: get_provider(provider_name) for provider_name in (providers or PROVIDERS)}
        self.initialized_providers = {}
        self.discarded_providers = set()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):  # @ReservedAssignment
        self.terminate()

    def get_initialized_provider(self, name):
        """Get a :class:`Provider` by name, initializing it if necessary

        :param string name: name of the provider
        :return: the initialized provider
        :rtype: :class:`Provider`

        """
        if name in self.initialized_providers:
            return self.initialized_providers[name]
        provider = self.providers[name](**self.provider_configs.get(name, {}))
        provider.initialize()
        self.initialized_providers[name] = provider
        return provider

    def list_subtitles(self, video, languages):
        """List subtitles for `video` with the given `languages`

        :param video: video to list subtitles for
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages of subtitles to search for
        :type languages: set of :class:`babelfish.Language`
        :return: found subtitles
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`

        """
        subtitles = []
        for provider_name, provider_class in self.providers.items():
            if not provider_class.check(video):
                logger.info('Skipping provider %r: not a valid video', provider_name)
                continue
            provider_languages = provider_class.languages & languages - video.subtitle_languages
            if not provider_languages:
                logger.info('Skipping provider %r: no language to search for', provider_name)
                continue
            if provider_name in self.discarded_providers:
                logger.debug('Skipping discarded provider %r', provider_name)
                continue
            try:
                provider = self.get_initialized_provider(provider_name)
                logger.info('Listing subtitles with provider %r and languages %r', provider_name, provider_languages)
                provider_subtitles = provider.list_subtitles(video, provider_languages)
                logger.info('Found %d subtitles', len(provider_subtitles))
                subtitles.extend(provider_subtitles)
            except ProviderNotAvailable:
                logger.warning('Provider %r is not available, discarding it', provider_name)
                self.discarded_providers.add(provider_name)
            except:
                logger.exception('Unexpected error in provider %r', provider_name)
        return subtitles

    def download_subtitle(self, subtitle):
        """Download a subtitle

        :param subtitle: subtitle to download
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :return: ``True`` if the subtitle has been successfully downloaded, ``False`` otherwise
        :rtype: bool

        """
        if subtitle.provider_name in self.discarded_providers:
            logger.debug('Discarded provider %r', subtitle.provider_name)
            return False
        try:
            provider = self.get_initialized_provider(subtitle.provider_name)
            provider.download_subtitle(subtitle)
            return True
        except ProviderNotAvailable:
            logger.warning('Provider %r is not available, discarding it', subtitle.provider_name)
            self.discarded_providers.add(subtitle.provider_name)
        except InvalidSubtitle:
            logger.warning('Invalid subtitle')
        except:
            logger.exception('Unexpected error in provider %r', subtitle.provider_name)
        return False

    def terminate(self):
        """Terminate all the initialized providers"""
        for (provider_name, provider) in self.initialized_providers.items():
            try:
                provider.terminate()
            except ProviderNotAvailable:
                logger.warning('Provider %r is not available, unable to terminate', provider_name)
            except:
                logger.exception('Unexpected error in provider %r', provider_name)
