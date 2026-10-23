"""Asynchronous pools for providers and refiners."""

from __future__ import annotations

import asyncio
import inspect
import logging
import operator
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Protocol, TypeVar, cast, runtime_checkable

import aiohttp
from babelfish import Language  # type: ignore[import-untyped]

from .archives import ARCHIVE_ERRORS
from .exceptions import DiscardingError
from .extensions import (
    RegistrableExtensionManager,
    get_default_providers,
    get_default_refiners,
    provider_manager,
    refiner_manager,
)
from .matches import fps_matches
from .providers import AsyncProvider, Provider
from .refiners import AsyncRefiner, Refiner
from .score import compute_score as default_compute_score
from .subtitle import filter_and_sort_categories
from .utils import handle_exception
from .video import Video

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Mapping, Sequence, Set
    from datetime import timedelta
    from types import TracebackType
    from typing import Self, TypeAlias

    from subliminal.score import ComputeScore
    from subliminal.subtitle import Subtitle

logger = logging.getLogger(__name__)


#: Default maximum number of providers queried at the same time
DEFAULT_MAX_CONCURRENCY = 10

#: Default timeout, in seconds, for a single provider operation
DEFAULT_TIMEOUT = 20.0


class ResultStatus(Enum):
    """The status of the result of a query to a provider."""

    OK = auto()
    UNSUPPORTED_VIDEO = auto()
    UNSUPPORTED_LANGUAGES = auto()
    UNSUPPORTED_ARCHIVE = auto()
    FAILURE = auto()
    OUTAGE = auto()


@dataclass
class Result:
    """Result of a query to a provider."""

    provider: str
    status: ResultStatus
    video: Video

    def ok(self) -> bool:
        """Check if the result is valid and triggered no error."""
        return self.status == ResultStatus.OK

    def unsupported(self) -> bool:
        """Check if the video or language was unsupported by the provider."""
        return self.status in [
            ResultStatus.UNSUPPORTED_VIDEO,
            ResultStatus.UNSUPPORTED_LANGUAGES,
            ResultStatus.UNSUPPORTED_ARCHIVE,
        ]

    def failure(self) -> bool:
        """Check if provider failed to return a result because of an error."""
        return self.status == ResultStatus.FAILURE

    def outage(self) -> bool:
        """Check if the query triggered an error that requires discarding the provider."""
        return self.status == ResultStatus.OUTAGE


@dataclass
class ProviderResult(Result):
    """Result of asking a provider to list subtitles for the video."""

    languages: set[Language] = field(default_factory=set)
    subtitles: list[Subtitle] = field(default_factory=list)


@dataclass
class RefinerResult(Result):
    """Result of asking a refiner to refine the video."""

    priority: int = 0
    update: dict[str, Any] = field(default_factory=dict)


def _check_no_running_loop(*, raises: bool = True) -> bool:
    """Check if no event loop is running.

    :param bool raises: if True, raises an error if an event loop is already running.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # no running loop, this is what we want
        pass
    else:  # pragma: no cover
        msg = 'Already inside an event loop, await the associated coroutine instead'
        if raises:  # pragma: no branch
            raise RuntimeError(msg)
        logger.warning(msg)
        return False

    return True


def handle_async_exception(e: BaseException, msg: str) -> None:
    """Log `e` with a sensible message, adding :mod:`aiohttp` errors to :func:`handle_exception`."""
    if isinstance(e, asyncio.TimeoutError):
        logger.error('Request timed out. %s', msg)
    elif isinstance(e, aiohttp.ClientResponseError):
        logger.error('HTTP error %r. %s', e.status, msg, exc_info=e.status not in range(500, 600))
    elif isinstance(e, aiohttp.ServerTimeoutError):
        logger.error('Request timed out. %s', msg)
    elif isinstance(e, aiohttp.ClientConnectionError):
        logger.error('Connection error %r. %s', e, msg)
    elif isinstance(e, Exception):
        # fall back on the synchronous handler, it knows about requests and xmlrpc errors
        handle_exception(e, msg)
    else:  # pragma: no cover
        logger.exception('Unexpected error. %s', msg)


@runtime_checkable
class GenericAsyncProvider(Protocol):
    """Structural type for providers that have been ported to :mod:`aiohttp`."""

    async def initialize(self) -> None:
        """Initialize the provider (login, session setup, ...)."""
        ...

    async def terminate(self) -> None:
        """Terminate the provider (logout, cleanup, ...)."""
        ...


@runtime_checkable
class GenericProvider(Protocol):
    """Structural type for synchronous generic providers."""

    def initialize(self) -> None:
        """Initialize the provider (login, session setup, ...)."""
        ...

    def terminate(self) -> None:
        """Terminate the provider (logout, cleanup, ...)."""
        ...


AnyGenericProvider: TypeAlias = GenericProvider | GenericAsyncProvider


def is_async_provider(provider: Provider | AsyncProvider) -> bool:
    """Return `True` if the provider exposes a coroutine-based API."""
    return inspect.iscoroutinefunction(provider.list_subtitles)


def is_async_refiner(refiner: Refiner | AsyncRefiner) -> bool:
    """Return `True` if the refiner exposes a coroutine-based API."""
    return inspect.iscoroutinefunction(refiner.refine)


class ProxyRefiner(Refiner):
    """Proxy class to create a synchronous Refiner from a refine function."""

    stage: ClassVar[int] = 5
    priority: int = 0

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        **kwargs: Any,
    ) -> None:
        self.session = session if session is not None else aiohttp.ClientSession()
        self.configs = dict(kwargs)

    @classmethod
    def check(cls, video: Video) -> bool:
        """Check if the `video` type is supported by the provider."""
        return True

    def initialize(self) -> None:
        """Initialize the provider (login, session setup, ...)."""

    def terminate(self) -> None:
        """Terminate the provider (logout, cleanup, ...)."""

    def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
        """Refine the video and return a dict."""
        raise NotImplementedError


def create_refiner_factory(name: str, refine: Callable) -> type[Refiner]:
    """Create a Refiner class from a refine function."""
    class_name = f'{name.title()}Refiner'

    def refine_method(cls: ProxyRefiner, *args: Any, **kwargs: Any) -> dict[str, Any]:
        refine(*args, **kwargs)
        return {}

    return type(class_name, (ProxyRefiner,), {'refine': refine_method})


def parse_timeout(timeout: float | None) -> float | None:  # pragma: no cover
    """Parse the timeout value.

    Non-positive value are converted to None.
    """
    if timeout is None:
        return None
    if timeout <= 0:
        return None
    return timeout


T = TypeVar('T', bound=AnyGenericProvider)


class AsyncPool(Generic[T]):
    """An asynchronous pool of providers.

    Providers are lazily initialized, queried concurrently, and automatically discarded on failure.
    The pool is an asynchronous context manager and must be used as such (or terminated explicitly),
    otherwise the underlying :class:`aiohttp.ClientSession` is left open::

    :param list[str] providers: name of providers to use, if not all.
    :param dict[str, Any] provider_configs: provider configuration as keyword arguments per provider name to pass
        when instantiating the :class:`~subliminal.providers.Provider`.
    :param int max_concurrency: maximum number of provider operations running at the same time.
    :param (float | None) timeout: timeout in seconds for a single provider operation, None to disable.
    :param session: an existing :class:`aiohttp.ClientSession` to use. If `None`, the pool creates
        and owns one. A session passed in is never closed by the pool.
    """

    providers_generic_name: ClassVar[str] = 'provider'

    #: Name of providers to use
    _providers: list[str]

    #: Provider configuration
    _provider_configs: dict[str, Any]

    #: Initialized providers
    _initialized_providers: dict[str, T]

    #: Maximum number of concurrent async operations
    max_concurrency: int

    #: Maximum number of threads for running synchronous functions
    max_workers: int

    #: Timeout in seconds for a single provider operation, None to disable
    timeout: float | None

    _session: aiohttp.ClientSession | None
    _owns_session: bool
    _semaphore: asyncio.Semaphore | None
    _locks: dict[str, asyncio.Lock]

    def __init__(
        self,
        providers: Sequence[str] | None = None,
        provider_configs: Mapping[str, Any] | None = None,
        *,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        max_workers: int | None = None,
        timeout: float | None = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._providers = list(providers) if providers is not None else self._get_default_providers()
        self._provider_configs = dict(provider_configs) if provider_configs is not None else {}
        self._initialized_providers = {}
        self.max_concurrency = max(1, max_concurrency)
        self.max_workers = max(1, max_workers or len(self._providers))
        self.timeout = parse_timeout(timeout)

        self._session = session
        self._owns_session = session is None
        self._semaphore = None
        # one lock per provider name, so two coroutines cannot initialize the same provider twice
        self._locks = {}

    # ------------------------------------------------------------------
    # context manager and lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.terminate()

    async def initialize(self) -> None:
        """Initialize the provider.

        Create the shared session and the concurrency limiter.

        Called automatically when entering the ``async with`` block. It is a no-op when
        called twice, and must run inside the event loop that will drive the pool.

        """
        # Set the semaphore (number of concurrent coroutine)
        if self._semaphore is None:  # pragma: no branch
            self._semaphore = asyncio.Semaphore(self.max_concurrency)

        # Create the session
        if self._session is None:  # pragma: no branch
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                connector=aiohttp.TCPConnector(limit=self.max_concurrency, limit_per_host=4),
            )

        # Set the number of threads
        try:
            loop = asyncio.get_running_loop()
            loop.set_default_executor(ThreadPoolExecutor(max_workers=self.max_workers))
        except RuntimeError:  # pragma: no cover
            # no running loop, this is not normal, but pass
            logger.warning('No running asyncio loop')

    @property
    def session(self) -> aiohttp.ClientSession:
        """The shared :class:`aiohttp.ClientSession`."""
        if self._session is None:  # pragma: no cover
            msg = 'The pool is not initialized, use `async with pool:` or `await pool.initialize()`'
            raise RuntimeError(msg)
        return self._session

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """The shared :class:`asyncio.Semaphore`."""
        if self._semaphore is None:  # pragma: no cover
            msg = 'The pool is not initialized, use `async with pool:` or `await pool.initialize()`'
            raise RuntimeError(msg)
        return self._semaphore

    async def terminate(self) -> None:
        """Terminate all the :attr:`initialized_providers` and close the session if owned."""
        logger.debug('Terminating initialized %ss', self.providers_generic_name)
        await asyncio.gather(
            *(self._terminate_provider(name) for name in list(self._initialized_providers)),
            return_exceptions=True,
        )

        if self._owns_session and self._session is not None:  # pragma: no branch
            await self._session.close()
            self._session = None

    async def _terminate_provider(self, name: str) -> None:
        """Terminate a single initialized provider, ignoring errors."""
        provider = self._initialized_providers.pop(name, None)
        if provider is None:  # pragma: no cover
            return

        try:
            logger.info('Terminating %s %s', self.providers_generic_name, name)
            await self._call(provider.terminate)
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:  # noqa: BLE001  # pragma: no cover
            handle_async_exception(e, f'{self.providers_generic_name.title()} {name} improperly terminated')

    # ------------------------------------------------------------------
    # provider access
    # ------------------------------------------------------------------

    @staticmethod
    def _get_default_providers() -> list[str]:
        """Return a list of the default providers to use if no provider is given at initialization."""
        raise NotImplementedError

    @staticmethod
    def _get_provider_manager() -> RegistrableExtensionManager:
        """Return a list of the default providers to use if no provider is given at initialization."""
        raise NotImplementedError

    async def get_provider(self, name: str) -> T:
        """Return the initialized provider `name`, initializing it on first use.

        :raise KeyError: if `name` is not part of :attr:`providers`.
        """
        if name not in self._providers:
            raise KeyError(name)

        if name in self._initialized_providers:
            return self._initialized_providers[name]

        lock = self._locks.setdefault(name, asyncio.Lock())
        async with lock:
            # another coroutine may have initialized it while waiting for the lock
            if name in self._initialized_providers:  # pragma: no cover
                return self._initialized_providers[name]

            logger.info('Initializing %s %s', self.providers_generic_name, name)
            provider = self._instantiate_provider(name)
            await self._call(provider.initialize)
            self._initialized_providers[name] = provider

        return self._initialized_providers[name]

    def _get_plugin(self, name: str) -> type[T]:
        """Get the plugin class of the provider `name`.

        The class is not instantiated.
        """
        return cast('type[T]', self._get_provider_manager()[name].plugin)

    def _instantiate_provider(self, name: str) -> T:
        """Instantiate the provider `name`, injecting the shared session when it accepts one."""
        plugin = self._get_plugin(name)
        kwargs = dict(self._provider_configs.get(name, {}))

        parameters = inspect.signature(plugin).parameters
        if 'session' in parameters and 'session' not in kwargs:
            kwargs['session'] = self.session

        return plugin(**kwargs)  # type: ignore[no-any-return]

    async def _call(
        self,
        func: Callable[..., Any] | Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Await `func` if it is a coroutine function, otherwise run it in a worker thread.

        This is the bridge that lets ported and not-yet-ported providers coexist. Note that
        a blocking call offloaded to a thread cannot be cancelled: a timeout releases the
        awaiting coroutine, but the thread keeps running until the underlying socket times out.
        """
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return await asyncio.to_thread(func, *args, **kwargs)

    def __iter__(self) -> Any:
        return iter(self._initialized_providers)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} [{list(self._providers)!r}]>'


class AsyncProviderPool(AsyncPool[Provider | AsyncProvider]):
    """An asynchronous pool of providers with the same API as a single :class:`~subliminal.providers.Provider`.

    Providers are lazily initialized, queried concurrently, and automatically discarded on failure.
    The pool is an asynchronous context manager and must be used as such (or terminated explicitly),
    otherwise the underlying :class:`aiohttp.ClientSession` is left open::

        async with AsyncProviderPool(providers=['opensubtitlescom']) as pool:
            subtitles = await pool.list_subtitles(video, {Language('eng')})
            await pool.download_best_subtitles(subtitles, video, {Language('eng')})

    :param list[str] providers: name of providers to use, if not all.
    :param dict[str, Any] provider_configs: provider configuration as keyword arguments per provider name to pass
        when instantiating the :class:`~subliminal.providers.Provider`.
    :param int max_concurrency: maximum number of provider operations running at the same time.
    :param (float | None) timeout: timeout in seconds for a single provider operation, None to disable.
    :param session: an existing :class:`aiohttp.ClientSession` to use. If `None`, the pool creates
        and owns one. A session passed in is never closed by the pool.
    """

    providers_generic_name: ClassVar[str] = 'provider'

    #: Providers that had an error that makes them unusable - they're discarded once the error is reported.
    discarded_providers: set[str]

    #: Providers that had an error, discarded or not. A superset of :attr:`discarded_providers`
    failed_providers: set[str]

    def __init__(
        self,
        providers: Sequence[str] | None = None,
        provider_configs: Mapping[str, Any] | None = None,
        *,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        timeout: float | None = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        super().__init__(providers, provider_configs, max_concurrency=max_concurrency, timeout=timeout, session=session)
        self.discarded_providers = set()
        self.failed_providers = set()

    @staticmethod
    def _get_default_providers() -> list[str]:
        """Return a list of the default providers to use if no provider is given at initialization."""
        return get_default_providers()

    @staticmethod
    def _get_provider_manager() -> RegistrableExtensionManager:
        """Return a list of the default providers to use if no provider is given at initialization."""
        return provider_manager

    def _discard_provider(self, name: str) -> None:
        """Stop using a provider, and record its error.

        A discarded provider is always a failed provider - that's why one function writes the two sets.
        """
        self.failed_providers.add(name)
        self.discarded_providers.add(name)

    @property
    def providers(self) -> list[str]:
        """Name of providers to use."""
        return self._providers

    @property
    def provider_configs(self) -> dict[str, Any]:
        """Provider configuration."""
        return self._provider_configs

    @property
    def initialized_providers(self) -> dict[str, Provider | AsyncProvider]:
        """Initialized providers."""
        return self._initialized_providers

    # ------------------------------------------------------------------
    # listing subtitles
    # ------------------------------------------------------------------

    async def list_subtitles_provider(
        self,
        provider: str,
        video: Video,
        languages: Set[Language],
    ) -> ProviderResult:
        """List subtitles with a single provider.

        The video and languages are checked against the provider.

        :return: ProviderResult.
        """
        # make sure the type is correct
        languages = set(languages)

        plugin = self._get_plugin(provider)

        # check video validity
        if not plugin.check(video):
            logger.info('Skipping provider %r: not a valid provider for this video type', provider)
            return ProviderResult(provider, status=ResultStatus.UNSUPPORTED_VIDEO, video=video, languages=languages)

        # check supported languages
        provider_languages = plugin.check_languages(languages)
        if not provider_languages:
            logger.info('Skipping provider %r: not a valid provider for the query languages', provider)
            return ProviderResult(provider, status=ResultStatus.UNSUPPORTED_LANGUAGES, video=video, languages=languages)

        logger.info('Listing subtitles with provider %r and languages %r', provider, provider_languages)

        async with self.semaphore:
            try:
                instance = await self.get_provider(provider)
                coro = self._call(instance.list_subtitles, video, provider_languages)
                subtitles = await asyncio.wait_for(coro, timeout=self.timeout)
            except asyncio.CancelledError:
                # the caller is shutting down, never swallow this
                raise
            except (DiscardingError, asyncio.TimeoutError) as e:
                handle_async_exception(e, f'Provider {provider}')
                # discard this provider: it is misconfigured, rate limited or too slow
                return ProviderResult(provider, status=ResultStatus.OUTAGE, video=video, languages=languages)
            except Exception as e:  # noqa: BLE001
                handle_async_exception(e, f'Provider {provider}')
                # keep the provider, the error may be specific to this video
                return ProviderResult(provider, status=ResultStatus.FAILURE, video=video, languages=languages)

        return ProviderResult(
            provider, status=ResultStatus.OK, video=video, languages=languages, subtitles=list(subtitles)
        )

    async def list_subtitles(self, video: Video, languages: Set[Language]) -> list[Subtitle]:
        """List subtitles, querying all the providers concurrently.

        :return: found subtitles, in :attr:`providers` order.
        """
        names = [name for name in self.providers if name not in self.discarded_providers]
        for name in set(self.providers) & self.discarded_providers:
            logger.debug('Skipping discarded provider %r', name)

        if not names:
            return []

        results = await asyncio.gather(*(self.list_subtitles_provider(name, video, languages) for name in names))
        logger.debug('Results of list_subtitles: %r', results)

        subtitles: list[Subtitle] = []
        for provider_result in results:
            name = provider_result.provider
            if provider_result.outage():
                logger.info('Discarding provider %s', name)
                self._discard_provider(name)
                continue
            if provider_result.failure():
                logger.info('Provider failed with a non-discarding error: %s', name)
                self.failed_providers.add(name)

            # add the subtitles
            subtitles.extend(provider_result.subtitles)

        return subtitles

    async def list_subtitles_videos(
        self,
        videos: Sequence[Video],
        languages: Set[Language],
    ) -> dict[Video, list[Subtitle]]:
        """List subtitles for several videos, one video at a time.

        Videos are handled sequentially on purpose: providers are queried concurrently within
        a video already, and going wider mostly buys rate-limit errors. Use
        :attr:`max_concurrency` to tune the actual parallelism.
        """
        listed_subtitles: dict[Video, list[Subtitle]] = defaultdict(list)
        for video in videos:
            logger.info('Listing subtitles for %r', video)
            subtitles = await self.list_subtitles(video, languages - video.subtitle_languages)
            listed_subtitles[video] = subtitles
            logger.info('Found %d subtitle(s)', len(subtitles))

        return listed_subtitles

    # ------------------------------------------------------------------
    # downloading subtitles
    # ------------------------------------------------------------------

    async def download_subtitle(self, subtitle: Subtitle) -> bool:
        """Download the subtitle content.

        :return: `True` if the subtitle has been successfully downloaded, `False` otherwise.
        """
        if subtitle.provider_name in self.discarded_providers:
            logger.warning('Provider %r is discarded', subtitle.provider_name)
            return False

        logger.info('Downloading subtitle %r', subtitle)

        async with self.semaphore:
            try:
                instance = await self.get_provider(subtitle.provider_name)
                coro = self._call(instance.download_subtitle, subtitle)
                await asyncio.wait_for(coro, timeout=self.timeout)
            except asyncio.CancelledError:
                raise
            except ARCHIVE_ERRORS:  # type: ignore[misc]  # ty: ignore[invalid-exception-caught]
                logger.exception('Bad archive for subtitle %r', subtitle)
            except DiscardingError as e:
                handle_async_exception(e, f'Discarding provider {subtitle.provider_name}')
                self._discard_provider(subtitle.provider_name)
            except Exception as e:  # noqa: BLE001
                handle_async_exception(e, f'Failed to download subtitle with provider {subtitle.provider_name}')
                self.failed_providers.add(subtitle.provider_name)

        # check subtitle validity
        if not subtitle.is_valid():
            logger.error('Invalid subtitle')
            return False

        return True

    async def download_best_subtitles(
        self,
        subtitles: Sequence[Subtitle],
        video: Video,
        languages: Set[Language],
        *,
        min_score: int = 0,
        subtitle_categories: str = '',
        skip_wrong_fps: bool = False,
        only_one: bool = False,
        compute_score: ComputeScore | None = None,
        ignore_subtitles: Sequence[str] | None = None,
    ) -> list[Subtitle]:
        """Download the best matching subtitles.

        Downloads stay sequential: the point of the fallback loop is to try the next best
        candidate only when the previous one failed, and to stop as soon as every language
        is covered. Downloading eagerly would waste provider quota.
        """
        compute_score = compute_score or default_compute_score
        ignore_subtitles = ignore_subtitles or []

        # ignore subtitles
        subtitles = [s for s in subtitles if s.id not in ignore_subtitles]

        # skip subtitles that do not match the FPS of the video (if defined)
        if skip_wrong_fps and video.frame_rate is not None and video.frame_rate > 0:
            subtitles = [s for s in subtitles if fps_matches(video, fps=s.fps, strict=False)]

        # filter and sort by subtitle categories
        subtitles = filter_and_sort_categories(subtitles, subtitle_categories=subtitle_categories)

        # sort subtitles by score
        scored_subtitles = sorted(
            [(s, compute_score(s, video)) for s in subtitles],
            key=operator.itemgetter(1),
            reverse=True,
        )

        downloaded_subtitles: list[Subtitle] = []
        for subtitle, score in scored_subtitles:
            # check score
            if score < min_score:
                logger.info('Score %d is below min_score (%d)', score, min_score)
                break

            # check downloaded languages
            if subtitle.language in {s.language for s in downloaded_subtitles}:
                logger.debug('Skipping subtitle: %r already downloaded', subtitle.language)
                continue

            # download
            if await self.download_subtitle(subtitle):  # pragma: no branch
                downloaded_subtitles.append(subtitle)

            # stop when all languages are downloaded
            if {s.language for s in downloaded_subtitles} == languages:
                logger.debug('All languages downloaded')
                break

            # stop if only one subtitle is requested
            if only_one and len(downloaded_subtitles) > 0:
                logger.debug('Only one subtitle downloaded')
                break

        return downloaded_subtitles


class AsyncRefinerPool(AsyncPool[Refiner | AsyncRefiner]):
    """An asynchronous pool of refiners.

    Refiners are lazily initialized, queried concurrently, and automatically discarded on failure.
    The pool is an asynchronous context manager and must be used as such (or terminated explicitly),
    otherwise the underlying :class:`aiohttp.ClientSession` is left open::

        async with AsyncRefinerPool(refiners=['hash']) as pool:
            await pool.refine(video)

    :param list[str] refiners: name of refiners to use, if not all.
    :param dict[str, Any] refiner_configs: refiner configuration as keyword arguments per refiner name to pass
        when instantiating the :class:`~subliminal.refiners.Refiner`.
    :param int max_concurrency: maximum number of refiner operations running at the same time.
    :param (float | None) timeout: timeout in seconds for a single refiner operation, None to disable.
    :param session: an existing :class:`aiohttp.ClientSession` to use. If `None`, the pool creates
        and owns one. A session passed in is never closed by the pool.
    """

    providers_generic_name: ClassVar[str] = 'refiner'

    #: Refiners that had an error that makes them unusable - they're discarded once the error is reported.
    discarded_refiners: set[str]

    #: Refiners that had an error, discarded or not. A superset of :attr:`discarded_refiners`
    failed_refiners: set[str]

    #: Videos that didn't pass the check and should be ignored
    ignored_videos: set[Video]

    def __init__(
        self,
        refiners: Sequence[str] | None = None,
        refiner_configs: Mapping[str, Any] | None = None,
        check_kwargs: Mapping[str, Any] | None = None,
        *,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        timeout: float | None = DEFAULT_TIMEOUT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        super().__init__(refiners, refiner_configs, max_concurrency=max_concurrency, timeout=timeout, session=session)
        self.check_kwargs = dict(check_kwargs) if check_kwargs is not None else {}
        self.discarded_refiners = set()
        self.failed_refiners = set()
        self.ignored_videos = set()

    @staticmethod
    def _get_default_providers() -> list[str]:
        """Return a list of the default refiners to use if no refiner is given at initialization."""
        return get_default_refiners()

    @staticmethod
    def _get_provider_manager() -> RegistrableExtensionManager:
        """Return a list of the default providers to use if no provider is given at initialization."""
        return refiner_manager

    def _discard_refiner(self, name: str) -> None:
        """Stop using a refiner, and record its error.

        A discarded refiner is always a failed refiner - that's why one function writes the two sets.
        """
        self.failed_refiners.add(name)
        self.discarded_refiners.add(name)

    def _get_plugin(self, name: str) -> type[Refiner | AsyncRefiner]:
        """Get the plugin class of the provider `name`.

        The class is not instantiated.
        Convert to a Refiner class if the plugin is a function.
        """
        plugin = self._get_provider_manager()[name].plugin
        if inspect.isclass(plugin):
            return cast('type[Refiner | AsyncRefiner]', plugin)

        return create_refiner_factory(name, plugin)

    @property
    def refiners(self) -> list[str]:
        """Name of refiners to use."""
        return self._providers

    @property
    def refiner_configs(self) -> dict[str, Any]:
        """Refiner configuration."""
        return self._provider_configs

    @property
    def initialized_refiners(self) -> dict[str, Refiner | AsyncRefiner]:
        """Initialized refiners."""
        return self._initialized_providers

    # ------------------------------------------------------------------
    # refining video
    # ------------------------------------------------------------------

    async def refine_provider(
        self,
        refiner: str,
        video: Video,
        **kwargs: Any,
    ) -> RefinerResult:
        """List subtitles with a single provider.

        The video and languages are checked against the provider.

        :return: RefinerResult.
        """
        plugin = self._get_plugin(refiner)

        # check video validity
        if not plugin.check(video):
            logger.info('Skipping refiner %r: not a valid refiner for this video type', refiner)
            return RefinerResult(refiner, status=ResultStatus.UNSUPPORTED_VIDEO, video=video)

        logger.info('Refining video with refiner %r', refiner)

        async with self.semaphore:
            priority = 0
            try:
                instance = await self.get_provider(refiner)
                priority = instance.priority
                coro = self._call(instance.refine, video, **kwargs)
                update = await asyncio.wait_for(coro, timeout=self.timeout)
            except asyncio.CancelledError:
                # the caller is shutting down, never swallow this
                raise
            except (DiscardingError, asyncio.TimeoutError) as e:
                handle_async_exception(e, f'Refiner {refiner}')
                # discard this refiner: it is misconfigured, rate limited or too slow
                return RefinerResult(refiner, status=ResultStatus.OUTAGE, video=video, priority=priority)
            except Exception as e:  # noqa: BLE001
                handle_async_exception(e, f'Refiner {refiner}')
                # keep the refiner, the error may be specific to this video
                return RefinerResult(refiner, status=ResultStatus.FAILURE, video=video, priority=priority)

        return RefinerResult(refiner, status=ResultStatus.OK, video=video, priority=priority, update=update)

    async def refine_by_stage(
        self,
        stage: int,
        refiners: Sequence[str],
        video: Video,
        **kwargs: Any,
    ) -> bool:
        """Refine video at a specified stage, querying all the providers concurrently, then check the video.

        :return: True if the video pass the check
        """
        if not refiners:
            return check_video(video, **self.check_kwargs)

        logger.info('Refining video with refiners at stage %i', stage)

        results = await asyncio.gather(*(self.refine_provider(refiner, video, **kwargs) for refiner in refiners))
        logger.debug('Results of refining at stage %i: %r', stage, results)

        updates: list[tuple[int, dict[str, Any]]] = []
        for refiner_result in results:
            if refiner_result.outage():
                logger.info('Discarding refiner %s', refiner_result.provider)
                self._discard_refiner(refiner_result.provider)
                continue
            if refiner_result.failure():
                self.failed_refiners.add(refiner_result.provider)

            # add the priority and update
            updates.append((refiner_result.priority, refiner_result.update))

        # Sort by priority, higher priority overrides lower priority keys
        sorted_updates = sorted(updates, key=operator.itemgetter(0))
        merged_update = {k: v for _, d in sorted_updates for k, v in d.items()}
        video.update(merged_update)

        # Check the video after updating
        return check_video(video, **self.check_kwargs)

    async def refine(self, video: Video, **kwargs: Any) -> Video | None:
        """Refine video, querying all the providers concurrently.

        :return: :class:`~subliminal.video.Video` if it passed the check or None
        :rtype: :class:`~subliminal.video.Video` or None
        """
        names = [name for name in self.refiners if name not in self.discarded_refiners]
        for name in set(self.refiners) & self.discarded_refiners:
            logger.debug('Skipping discarded refiners %r', name)

        if not names:
            # No refiners for this stage, but there can be refiners at later stages. Pass the video
            return video

        # Get refiner stages
        refiner_stages = {name: self._get_plugin(name).stage for name in names}
        stages = sorted(set(refiner_stages.values()))
        logger.debug('Found refining stages: %r', stages)

        # Refine video by stage
        for refiner_stage in stages:
            refiners = [name for name, stage in refiner_stages.items() if stage == refiner_stage]
            ok = await self.refine_by_stage(refiner_stage, refiners, video, **kwargs)
            if not ok:
                # Check video returned False, no need to refine more, do not pass the video
                logger.info('After stage %i refining, ignoring video: %r', refiner_stage, video)
                return None
        return video

    async def refine_videos(self, videos: Set[Video], **kwargs: Any) -> set[Video]:
        """Refine several videos, one video at a time.

        Videos are handled sequentially on purpose: providers are queried concurrently within
        a video already, and going wider mostly buys rate-limit errors. Use
        :attr:`max_concurrency` to tune the actual parallelism.

        :return: videos that passed the checks
        :rtype: set of :class:`~subliminal.video.Video`
        """
        final_videos = set()
        for video in videos:
            logger.info('Refine video %r', video)
            video_or_none = await self.refine(video, **kwargs)
            if video_or_none is not None:
                final_videos.add(video_or_none)

        return final_videos


def check_video(
    video: Video,
    *,
    languages: Set[Language] | None = None,
    age: timedelta | None = None,
    undefined: bool = False,
) -> bool:
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


async def async_refine(
    videos: Video | Set[Video],
    *,
    refiners: Sequence[str] | None = None,
    refiner_configs: Mapping[str, Any] | None = None,
    check_kwargs: Mapping[str, Any] | None = None,
    pool_class: type[AsyncRefinerPool] = AsyncRefinerPool,
    **kwargs: Any,
) -> set[Video]:
    """Refine one or several videos using :ref:`refiners`.

    .. note::

        Exceptions raised in refiners are silently passed and logged.

    :param videos: the videos to refine.
    :type videos: set of :class:`~subliminal.video.Video`
    :param Sequence refiners: refiners to select. None defaults to all refiners.
    :param dict refiner_configs: refiner configuration as keyword arguments per refiner name to pass when
        calling the refine method
    :param dict check_kwargs: arguments to pass to the check_video function
    :param pool_class: class to use as refiner pool.
    :type pool_class: :class:`AsyncRefinerPool` or similar
    :param kwargs: additional parameters for the `refine` method.
    :return: the videos that are not ignored.
    :rtype: set of :class:`~subliminal.video.Video`
    """
    # make sure videos is a list
    if isinstance(videos, Video):
        videos = {videos}
    # return immediately if no videos
    if not videos:
        return set()

    # refine videos
    async with pool_class(refiners=refiners, refiner_configs=refiner_configs, check_kwargs=check_kwargs) as pool:
        return await pool.refine_videos(videos, **kwargs)


def refine(*args: Any, **kwargs: Any) -> set[Video]:
    """Refine videos using :ref:`refiners`."""
    _check_no_running_loop()
    return asyncio.run(async_refine(*args, **kwargs))


async def async_list_subtitles(
    videos: Set[Video],
    languages: Set[Language],
    *,
    pool_class: type[AsyncProviderPool] = AsyncProviderPool,
    **kwargs: Any,
) -> dict[Video, list[Subtitle]]:
    """List subtitles.

    The `videos` must pass the `languages` check of :func:`check_video`.

    :param videos: videos to list subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to search for.
    :type languages: set of :class:`~babelfish.language.Language`
    :param pool_class: class to use as provider pool.
    :type pool_class: :class:`AsyncProviderPool` or similar
    :param kwargs: additional parameters for the provided `pool_class` constructor.
    :return: found subtitles per video.
    :rtype: dict of :class:`~subliminal.video.Video` to list of :class:`~subliminal.subtitle.Subtitle`

    """
    listed_subtitles: dict[Video, list[Subtitle]] = defaultdict(list)

    # check videos
    checked_videos = []
    for video in videos:
        if not check_video(video, languages=languages):
            logger.info('Skipping video %r', video)
            continue
        checked_videos.append(video)

    # return immediately if no video passed the checks
    if not checked_videos:
        return listed_subtitles

    # list subtitles
    async with pool_class(**kwargs) as pool:
        return await pool.list_subtitles_videos(checked_videos, languages)


def list_subtitles(*args: Any, **kwargs: Any) -> dict[Video, list[Subtitle]]:
    """Synchronous wrapper around :func:`async_list_subtitles`."""
    _check_no_running_loop()
    return asyncio.run(async_list_subtitles(*args, **kwargs))


async def async_download_subtitles(
    subtitles: Sequence[Subtitle],
    *,
    pool_class: type[AsyncProviderPool] = AsyncProviderPool,
    **kwargs: Any,
) -> None:
    """Download :attr:`~subliminal.subtitle.Subtitle.content` of `subtitles`.

    :param subtitles: subtitles to download.
    :type subtitles: list of :class:`~subliminal.subtitle.Subtitle`
    :param pool_class: class to use as provider pool.
    :type pool_class: :class:`AsyncProviderPool` or similar
    :param kwargs: additional parameters for the provided `pool_class` constructor.

    """
    async with pool_class(**kwargs) as pool:
        for subtitle in subtitles:
            logger.info('Downloading subtitle %r', subtitle)
            await pool.download_subtitle(subtitle)


def download_subtitles(*args: Any, **kwargs: Any) -> None:
    """Synchronous wrapper around :func:`async_download_subtitles`."""
    _check_no_running_loop()
    return asyncio.run(async_download_subtitles(*args, **kwargs))


async def async_download_best_subtitles(
    videos: Set[Video],
    languages: Set[Language],
    *,
    pool_class: type[AsyncProviderPool] = AsyncProviderPool,
    min_score: int = 0,
    subtitle_categories: str = '',
    skip_wrong_fps: bool = False,
    only_one: bool = False,
    compute_score: ComputeScore | None = None,
    ignore_subtitles: Sequence[str] | None = None,
    **kwargs: Any,
) -> dict[Video, list[Subtitle]]:
    """List and download the best matching subtitles.

    The `videos` must pass the `languages` and `undefined` (`only_one`) checks of :func:`check_video`.

    :param videos: videos to download subtitles for.
    :type videos: set of :class:`~subliminal.video.Video`
    :param languages: languages to download.
    :type languages: set of :class:`~babelfish.language.Language`
    :param pool_class: class to use as async provider pool.
    :type pool_class: :class:`AsyncProviderPool` or similar
    :param int min_score: minimum score for a subtitle to be downloaded.
    :param str subtitle_categories: ordered list of categories to download, omitted categories are filtered out.
        Empty string corresponds to no filtering or sorting.
    :param bool skip_wrong_fps: skip subtitles with an FPS that do not match the video (False).
    :param bool only_one: download only one subtitle, not one per language.
    :param compute_score: function that takes `subtitle` and `video` as positional arguments and returns the score.
    :param ignore_subtitles: list of subtitle ids to ignore, if any.
    :param kwargs: additional parameters for the provided `pool_class` constructor.
    :return: downloaded subtitles per video.
    :rtype: dict of :class:`~subliminal.video.Video` to list of :class:`~subliminal.subtitle.Subtitle`

    """
    downloaded_subtitles: dict[Video, list[Subtitle]] = defaultdict(list)

    # check videos
    checked_videos = []
    for video in videos:
        if not check_video(video, languages=languages, undefined=only_one):
            logger.info('Skipping video %r', video)
            continue
        checked_videos.append(video)

    # return immediately if no video passed the checks
    if not checked_videos:
        return downloaded_subtitles

    # download best subtitles
    async with pool_class(**kwargs) as pool:
        for video in checked_videos:
            logger.info('Downloading best subtitles for %r', video)
            subtitles = await pool.list_subtitles(video, languages - video.subtitle_languages)
            downloaded_subtitles[video] = await pool.download_best_subtitles(
                subtitles,
                video,
                languages,
                min_score=min_score,
                subtitle_categories=subtitle_categories,
                skip_wrong_fps=skip_wrong_fps,
                only_one=only_one,
                compute_score=compute_score,
                ignore_subtitles=ignore_subtitles,
            )
            logger.info('Downloaded %d subtitle(s)', len(downloaded_subtitles[video]))

    return downloaded_subtitles


def download_best_subtitles(*args: Any, **kwargs: Any) -> dict[Video, list[Subtitle]]:
    """Synchronous wrapper around :func:`async_download_best_subtitles`."""
    _check_no_running_loop()
    return asyncio.run(async_download_best_subtitles(*args, **kwargs))


def save_subtitles(
    video: Video,
    subtitles: Sequence[Subtitle],
    *,
    single: bool = False,
    directory: str | os.PathLike | None = None,
    encoding: str | None = None,
    subtitle_format: str | None = None,
    extension: str | None = None,
    category_suffix: bool = False,
    language_format: str = 'alpha2',
) -> list[Subtitle]:
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
    :param str subtitle_format: format in which to save the subtitles, default is to keep original format.
    :param (str | None) extension: the subtitle extension, default is to match to the subtitle format.
    :param bool category_suffix: add a suffix with the subtitle category ('hi' or 'fo') if needed. Default to False.
    :param str language_format: format of the language suffix. Default to 'alpha2'.
    :return: the saved subtitles
    :rtype: list of :class:`~subliminal.subtitle.Subtitle`

    """
    saved_subtitles: list[Subtitle] = []
    for subtitle in subtitles:
        # check content
        if not subtitle.content:
            logger.error('Skipping subtitle %r: no content', subtitle)
            continue

        # check language
        if subtitle.language in {s.language for s in saved_subtitles}:
            logger.debug('Skipping subtitle %r: language already saved', subtitle)
            continue

        # convert subtitle to a new format
        if subtitle_format:
            # Use the video FPS if the FPS of the subtitle is not defined
            fps = video.frame_rate if subtitle.fps is None else None
            subtitle.convert(output_format=subtitle_format, output_encoding=encoding, fps=fps)

        # create subtitle path
        subtitle_path = subtitle.get_path(
            video,
            single=single,
            extension=extension,
            category_suffix=category_suffix,
            language_format=language_format,
        )
        if directory is not None:
            subtitle_path = os.path.join(directory, os.path.split(subtitle_path)[1])

        # save content as is or in the specified encoding
        logger.info('Saving %r to %r', subtitle, subtitle_path)
        if encoding is None:
            with open(subtitle_path, 'wb') as f:
                f.write(subtitle.content)
        else:
            with open(subtitle_path, 'w', encoding=encoding) as f:
                f.write(subtitle.text)
        saved_subtitles.append(subtitle)

        # check single
        if single:
            break

    return saved_subtitles
