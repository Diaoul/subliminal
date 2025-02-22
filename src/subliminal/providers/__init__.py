"""
Providers list and download subtitles for a :class:`~subliminal.video.Video` object.

A Provider is a ContextManager with ``__enter__`` and ``__exit__`` methods and
two public methods: :meth:`~subliminal.providers.Provider.list_subtitles` and
:meth:`~subliminal.providers.Provider.download_subtitle`.
"""

from __future__ import annotations

import logging
import ssl
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar
from xmlrpc.client import SafeTransport

# Do not put babelfish in a TYPE_CHECKING block for intersphinx to work properly
from babelfish import Language  # type: ignore[import-untyped]  # noqa: TC002
from bs4 import BeautifulSoup, FeatureNotFound
from requests import adapters
from urllib3 import poolmanager  # type: ignore[import-untyped]

from subliminal import __short_version__
from subliminal.subtitle import Subtitle
from subliminal.video import Episode, Movie, Video

if TYPE_CHECKING:
    import os
    from collections.abc import Sequence, Set
    from http.client import HTTPSConnection
    from types import TracebackType
    from typing import Self


logger = logging.getLogger(__name__)


class SecLevelOneTLSAdapter(adapters.HTTPAdapter):
    """:class:`~requests.adapters.HTTPAdapter` with security level set to 1."""

    def init_poolmanager(self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any) -> None:  # noqa: FBT001, FBT002
        """Create and initialize the urllib3 PoolManager."""
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLS,
            ssl_context=ctx,
        )


class TimeoutSafeTransport(SafeTransport):
    """Timeout support for :class:`!xmlrpc.client.SafeTransport`."""

    timeout: float | None

    def __init__(
        self,
        *args: Any,
        timeout: float | None = None,
        user_agent: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.timeout = timeout
        if user_agent is not None:  # pragma: no branch
            self.user_agent = user_agent

    def make_connection(self, host: Any) -> HTTPSConnection:
        """Make connection to host.

        :param host: the connection host.
        :type host: ``xmlrpc.client._HostType``
        :return: the HTTPS connection.
        :rtype: :library/http.client:class:`~http.client.HTTPSConnection`

        """
        c = SafeTransport.make_connection(self, host)
        c.timeout = self.timeout

        return c


class ParserBeautifulSoup(BeautifulSoup):
    """A :class:`~bs4.BeautifulSoup` that picks the first parser available in `parsers`.

    :param (str | bytes) markup: markup for the :class:`~bs4.BeautifulSoup`.
    :param list[str] parsers: parser names, in order of preference.

    """

    def __init__(self, markup: str | bytes, parsers: Sequence[str], **kwargs: Any) -> None:
        # reject features
        if set(parsers).intersection({'fast', 'permissive', 'strict', 'xml', 'html', 'html5'}):
            msg = 'Features not allowed, only parser names'
            raise ValueError(msg)

        # reject some kwargs
        if 'features' in kwargs:
            msg = 'Cannot use features kwarg'
            raise ValueError(msg)
        if 'builder' in kwargs:
            msg = 'Cannot use builder kwarg'
            raise ValueError(msg)

        # pick the first parser available
        for parser in parsers:
            try:
                super().__init__(markup, parser, **kwargs)
            except FeatureNotFound:
                pass
            else:
                return

        raise FeatureNotFound


S = TypeVar('S', bound=Subtitle)


class Provider(Generic[S]):
    """Base class for providers.

    Each Provider returns subtitles from a specialized subclass of :class:`~subliminal.subtitle.Subtitle`.

    If any configuration is possible for the provider, like credentials, it must take place during instantiation.

    :raises: :class:`~subliminal.exceptions.ConfigurationError` if there is a configuration error

    """

    #: Supported set of :class:`~babelfish.language.Language`
    languages: ClassVar[Set[Language]] = frozenset()

    #: Supported video types
    video_types: ClassVar[tuple[type[Video], ...]] = (Episode, Movie)

    #: Required hash, if any
    required_hash: ClassVar[str | None] = None

    #: Subtitle class to use
    subtitle_class: ClassVar[type[S] | None] = None  # type: ignore[misc]

    #: User Agent to use
    user_agent: str = f'Subliminal/{__short_version__}'

    @staticmethod
    def hash_video(video_path: str | os.PathLike) -> str | None:
        """Hash the video to be used by the provider."""
        return None

    def __enter__(self) -> Self:
        self.initialize()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.terminate()

    def initialize(self) -> None:
        """Initialize the provider.

        Must be called when starting to work with the provider. This is the place for network initialization
        or login operations.

        .. note::
            This is called automatically when entering the `with` statement

        """
        raise NotImplementedError

    def terminate(self) -> None:
        """Terminate the provider.

        Must be called when done with the provider. This is the place for network shutdown or logout operations.

        .. note::
            This is called automatically when exiting the `with` statement

        """
        raise NotImplementedError

    @classmethod
    def check(cls, video: Video) -> bool:
        """Check if the `video` can be processed.

        The `video` is considered invalid if not an instance of :attr:`video_types` or if the :attr:`required_hash` is
        not present in :attr:`~subliminal.video.Video.hashes` attribute of the `video`.

        :param video: the video to check.
        :type video: :class:`~subliminal.video.Video`
        :return: `True` if the `video` is valid, `False` otherwise.
        :rtype: bool

        """
        if not cls.check_types(video):
            return False
        return cls.required_hash is None or cls.required_hash in video.hashes

    @classmethod
    def check_types(cls, video: Video) -> bool:
        """Check if the `video` type is supported by the provider.

        The `video` is considered invalid if not an instance of :attr:`video_types`.

        :param video: the video to check.
        :type video: :class:`~subliminal.video.Video`
        :return: `True` if the `video` is valid, `False` otherwise.
        :rtype: bool

        """
        return isinstance(video, cls.video_types)

    @classmethod
    def check_languages(cls, languages: Set[Language]) -> Set[Language]:
        """Check if the `languages` are supported by the provider.

        A subset of the supported languages is returned.

        :param languages: the languages to check.
        :type languages: set of :class:`~babelfish.language.Language`
        :return: subset of the supported languages.
        :rtype: set of :class:`~babelfish.language.Language`

        """
        return cls.languages & languages

    def query(self, *args: Any, **kwargs: Any) -> list[S]:
        """Query the provider for subtitles.

        Arguments should match as much as possible the actual parameters for querying the provider

        :return: found subtitles.
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderError`

        """
        raise NotImplementedError

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[S]:
        """List subtitles for the `video` with the given `languages`.

        This will call the :meth:`query` method internally. The parameters passed to the :meth:`query` method may
        vary depending on the amount of information available in the `video`.

        :param video: video to list subtitles for.
        :type video: :class:`~subliminal.video.Video`
        :param languages: languages to search for.
        :type languages: set of :class:`~babelfish.language.Language`
        :return: found subtitles.
        :rtype: list of :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderError`

        """
        raise NotImplementedError

    def download_subtitle(self, subtitle: S) -> None:
        """Download `subtitle`'s :attr:`~subliminal.subtitle.Subtitle.content`.

        :param subtitle: subtitle to download.
        :type subtitle: :class:`~subliminal.subtitle.Subtitle`
        :raise: :class:`~subliminal.exceptions.ProviderError`

        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} [{self.video_types!r}]>'
