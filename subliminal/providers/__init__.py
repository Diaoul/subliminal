# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import babelfish
from ..video import Episode, Movie


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

    def __exit__(self, *args):
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
        """Download the `subtitle`

        :param subtitle: subtitle to download
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :return: the subtitle text
        :rtype: string
        :raise: :class:`~subliminal.exceptions.ProviderNotAvailable` if the provider is unavailable
        :raise: :class:`~subliminal.exceptions.InvalidSubtitle` if the downloaded subtitle is invalid
        :raise: :class:`~subliminal.exceptions.ProviderError` if something unexpected occured

        """
        raise NotImplementedError

    def __repr__(self):
        return '<%s [%r]>' % (self.__class__.__name__, self.video_types)
