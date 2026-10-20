"""
Refiners enrich a :class:`~subliminal.video.Video` object by adding information to it.

A refiner is a simple function:

.. py:function:: refine(video, **kwargs)

    :param video: the video to refine.
    :type video: :class:`~subliminal.video.Video`
    :param kwargs: additional parameters for refiners.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from subliminal.video import Episode, Movie

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Self

    from subliminal.video import Video


class AsyncRefiner:
    """Asynchronous refiner."""

    #: Supported video types
    video_types: ClassVar[tuple[type[Video], ...]] = (Episode, Movie)

    #: Stage of the refiner, lower is called first
    stage: ClassVar[int] = 5

    #: Priority of the refiner (inside its stage), higher value takes precedence
    priority: int = 0

    @classmethod
    def check(cls, video: Video) -> bool:
        """Check if the `video` can be processed.

        The `video` is considered invalid if not an instance of :attr:`video_types`.

        :param video: the video to check.
        :type video: :class:`~subliminal.video.Video`
        :return: `True` if the `video` is valid, `False` otherwise.
        :rtype: bool

        """
        return cls.check_types(video)

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
        """Initialize the refiner.

        Must be called when starting to work with the refiner. This is the place for network initialization
        or login operations.

        .. note::
            This is called automatically when entering the `with` statement

        """
        raise NotImplementedError

    async def terminate(self) -> None:
        """Terminate the refiner.

        Must be called when done with the refiner. This is the place for network shutdown or logout operations.

        .. note::
            This is called automatically when exiting the `with` statement
        """
        raise NotImplementedError

    async def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
        """Refine the video."""
        raise NotImplementedError
