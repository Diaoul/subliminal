"""Mock provider, for testing purposes."""

from __future__ import annotations

import logging
from importlib import import_module
from itertools import count
from typing import TYPE_CHECKING, Any, ClassVar

from babelfish import LANGUAGES, Language  # type: ignore[import-untyped]
from guessit import guessit  # type: ignore[import-untyped]

from subliminal.exceptions import DiscardingError, NotInitializedProviderError
from subliminal.matches import guess_matches
from subliminal.subtitle import Subtitle
from subliminal.video import Episode, Movie, Video

from . import Provider

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Set

logger = logging.getLogger(__name__)


class MockSubtitle(Subtitle):
    """Mock Subtitle."""

    _ids: ClassVar = count(0)

    #: Provider name, modify in subclasses
    provider_name: ClassVar[str] = 'mock'

    #: Fake content, will be copied to 'content' with :meth:`MockProvider.download_subtitle`
    fake_content: bytes

    #: Video name to match to be listed by :meth:`MockProvider.list_subtitles`
    video_name: str

    #: A set of matches to add to the set when :meth:`get_matches` is called
    matches: set[str]

    #: Guesses used as argument to compute the matches with :func:`guess_matches`
    parameters: dict[str, Any]

    #: Release name to be parsed with guessit and added to the :attr:`parameters`
    release_name: str

    def __init__(
        self,
        language: Language,
        *,
        subtitle_id: str = '',
        fake_content: bytes = b'',
        video_name: str = '',
        matches: Set[str] | None = None,
        parameters: Mapping[str, Any] | None = None,
        release_name: str = '',
        **kwargs: Any,
    ) -> None:
        # generate unique id for mock subtitle
        next_id: int = next(self._ids)
        if not subtitle_id:
            subtitle_id = f'S{next_id:05d}'
        super().__init__(
            language,
            subtitle_id,
            **kwargs,
        )
        self.fake_content = fake_content
        self.video_name = video_name
        self.matches = set(matches) if matches is not None else set()
        self.parameters = dict(parameters) if parameters is not None else {}
        self.release_name = release_name

    def get_matches(self, video: Video) -> set[str]:
        """Get the matches against the `video`."""
        # Use the parameters as guesses
        matches = guess_matches(video, self.parameters)

        # Parse the release_name and guess more matches
        if self.release_name:
            video_type = 'episode' if isinstance(video, Episode) else 'movie'
            matches |= guess_matches(video, guessit(self.release_name, {'type': video_type}))

        # Force add more matches
        return matches | self.matches


class MockProvider(Provider):
    """Mock Provider."""

    languages: ClassVar[Set[Language]] = {Language(lang) for lang in LANGUAGES}
    subtitle_class: ClassVar = MockSubtitle
    internal_subtitle_pool: ClassVar[list[MockSubtitle]] = []

    video_types: ClassVar = (Episode, Movie)

    logged_in: bool
    subtitle_pool: list[MockSubtitle]
    is_broken: bool

    def __init__(self, subtitle_pool: Sequence[MockSubtitle] | None = None, **kwargs: Any) -> None:
        self.logged_in = False
        self.subtitle_pool = list(self.internal_subtitle_pool)
        if subtitle_pool is not None:  # pragma: no cover
            self.subtitle_pool.extend(list(subtitle_pool))
        self.is_broken = False

    def initialize(self) -> None:
        """Initialize the provider."""
        logger.info('Mock provider %s was initialized', self.__class__.__name__)
        self.logged_in = True

    def terminate(self) -> None:
        """Terminate the provider."""
        if not self.logged_in:  # pragma: no cover
            logger.info('Mock provider %s was not terminated', self.__class__.__name__)
            raise NotInitializedProviderError

        logger.info('Mock provider %s was terminated', self.__class__.__name__)
        self.logged_in = False

    def query(
        self,
        languages: Set[Language],
        video: Video | None = None,
        matches: Set[str] | None = None,
    ) -> list[MockSubtitle]:  # pragma: no cover
        """Query the provider for subtitles."""
        if self.is_broken:
            msg = f'Mock provider {self.__class__.__name__} query raised an error'
            raise DiscardingError(msg)

        subtitles = []
        for lang in languages:
            subtitle = self.subtitle_class(language=lang, video=video, matches=matches)
            subtitles.append(subtitle)
        logger.info(
            'Mock provider %s query for video %r and languages %s: %d',
            self.__class__.__name__,
            video.name if video else None,
            languages,
            len(subtitles),
        )
        return subtitles

    def list_subtitles(self, video: Video, languages: Set[Language]) -> list[MockSubtitle]:
        """List all the subtitles for the video."""
        if self.is_broken:
            msg = f'Mock provider {self.__class__.__name__} list_subtitles raised an error'
            raise DiscardingError(msg)

        subtitles = [
            subtitle
            for subtitle in self.subtitle_pool
            if subtitle.language in languages and video.name.endswith(subtitle.video_name)
        ]
        logger.info(
            'Mock provider %s list subtitles for video %r and languages %s: %d',
            self.__class__.__name__,
            video.name,
            languages,
            len(subtitles),
        )
        return subtitles

    def download_subtitle(self, subtitle: MockSubtitle) -> None:
        """Download the content of the subtitle."""
        if self.is_broken:
            msg = f'Mock provider {self.__class__.__name__} download_subtitle raised an error'
            raise DiscardingError(msg)

        logger.info(
            'Mock provider %s download subtitle %s',
            self.__class__.__name__,
            subtitle,
        )
        subtitle.set_content(subtitle.fake_content)


def mock_subtitle_provider(
    name: str,
    subtitles_info: Sequence[Mapping[str, Any]],
    languages: Set[Language] | None = None,
    video_types: tuple[type[Episode] | type[Movie], ...] = (Episode, Movie),
) -> str:
    """Mock a subtitle provider, providing subtitles."""
    languages = set(languages) if languages else {Language(lang) for lang in LANGUAGES}

    name_lower = name.lower()
    subtitle_class_name = f'{name}Subtitle'
    provider_class_name = f'{name}Provider'

    # MockSubtitle subclass
    MyMockSubtitle = type(subtitle_class_name, (MockSubtitle,), {'provider_name': name_lower})

    subtitle_pool = [MyMockSubtitle(**kw) for kw in subtitles_info]

    MyMockProvider = type(
        provider_class_name,
        (MockProvider,),
        {
            'subtitle_class': MyMockSubtitle,
            'internal_subtitle_pool': subtitle_pool,
            'languages': languages,
            'video_types': video_types,
        },
    )

    mod = import_module('subliminal.providers.mock')
    setattr(mod, provider_class_name, MyMockProvider)

    return f'{name_lower} = subliminal.providers.mock:{provider_class_name}'
