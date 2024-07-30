"""Hash and sanitize functions."""

from __future__ import annotations

import functools
import logging
import os
import platform
import re
import socket
from datetime import datetime, timedelta, timezone
from types import GeneratorType
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterable, TypeVar, cast, overload
from xmlrpc.client import ProtocolError

import requests
from requests.exceptions import SSLError

from .exceptions import ServiceUnavailable

if TYPE_CHECKING:
    from collections.abc import Sequence, Set
    from typing import TypeGuard

T = TypeVar('T')
R = TypeVar('R')

logger = logging.getLogger(__name__)


class none_passthrough(Generic[T, R]):
    """Decorator to pass-through None input values."""

    def __init__(self, func: Callable[[T], R]) -> None:
        self.func = func
        functools.update_wrapper(self, func)

    @overload
    def __call__(self, arg: T, *args: Any, **kwargs: Any) -> R: ...

    @overload
    def __call__(self, arg: None, *args: Any, **kwargs: Any) -> None: ...

    def __call__(self, arg: T | None, *args: Any, **kwargs: Any) -> R | None:  # noqa: D102
        if arg is None:
            return None
        return self.func(arg, *args, **kwargs)


@none_passthrough
def sanitize(string: str, ignore_characters: Set[str] | None = None) -> str:
    """Sanitize a string to strip special characters.

    :param str string: the string to sanitize.
    :param set ignore_characters: characters to ignore.
    :return: the sanitized string.
    :rtype: str

    """
    ignore_characters = set(ignore_characters) if ignore_characters is not None else set()

    # replace some characters with one space
    characters = {'-', ':', '(', ')', '.', ','} - ignore_characters
    if characters:
        string = re.sub(r'[{}]'.format(re.escape(''.join(characters))), ' ', string)

    # remove some characters
    characters = {"'"} - ignore_characters
    if characters:
        string = re.sub(r'[{}]'.format(re.escape(''.join(characters))), '', string)

    # replace multiple spaces with one
    string = re.sub(r'\s+', ' ', string)

    # strip and lower case
    return string.strip().lower()


@none_passthrough
def sanitize_release_group(string: str) -> str:
    """Sanitize a `release_group` string to remove content in square brackets.

    :param str string: the release group to sanitize.
    :return: the sanitized release group.
    :rtype: str

    """
    # remove content in square brackets
    string = re.sub(r'\[\w+\]', '', string)

    # strip and upper case
    return string.strip().upper()


@none_passthrough
def sanitize_id(id_: str | int) -> int:
    """Sanitize the IMDB (or other) id and transform it to a string (without leading 'tt' or zeroes)."""
    id_ = str(id_).lower().lstrip('t')
    return int(id_)


@none_passthrough
def decorate_imdb_id(imdb_id: str | int, *, ndigits: int = 7) -> str:
    """Convert the IMDB id to add the leading 'tt' and the leading zeroes."""
    return 'tt' + str(int(imdb_id)).rjust(ndigits, '0')


def timestamp(date: datetime) -> float:
    """Get the timestamp of the `date` (with timezone).

    :param datetime.datetime date: the utc date.
    :return: the timestamp of the date.
    :rtype: float

    """
    return (date - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()


def matches_title(
    actual: str | None,
    title: str | None,
    alternative_titles: Sequence[str],
) -> bool:
    """Whether `actual` matches the `title` or `alternative_titles`.

    :param str actual: the actual title to check
    :param str title: the expected title
    :param list alternative_titles: the expected alternative_titles
    :return: whether the actual title matches the title or alternative_titles.
    :rtype: bool

    """
    if actual is None or title is None:
        return False
    actual = sanitize(actual)
    title = sanitize(title)
    if actual == title:
        return True

    if alternative_titles is not None:
        alternative_titles_set = {sanitize(t) for t in alternative_titles if t}
        if actual in alternative_titles_set:
            return True

    return False


def handle_exception(e: Exception, msg: str) -> None:
    """Handle exception, logging the proper error message followed by `msg`.

    Exception traceback is only logged for specific cases.

    :param Exception e: The exception to handle.
    :param str msg: The message to log.
    """
    if isinstance(e, (requests.Timeout, socket.timeout)):
        logger.error('Request timed out. %s', msg)
    elif isinstance(e, (ServiceUnavailable, ProtocolError)):
        # OpenSubtitles raises xmlrpclib.ProtocolError when unavailable
        logger.error('Service unavailable. %s', msg)
    elif isinstance(e, requests.exceptions.HTTPError):
        logger.error(
            'HTTP error %r. %s', e.response.status_code, msg, exc_info=e.response.status_code not in range(500, 600)
        )
    elif isinstance(e, SSLError):
        logger.error('SSL error %r. %s', e.args[0], msg, exc_info=e.args[0] != 'The read operation timed out')
    else:
        logger.exception('Unexpected error. %s', msg)


def is_iterable(obj: Any) -> TypeGuard[Iterable]:
    """Check that the object is iterable (but not a string)."""
    return (isinstance(obj, Iterable) and not isinstance(obj, (str, bytes))) or isinstance(obj, GeneratorType)


def ensure_list(value: T | Sequence[T] | None) -> list[T]:
    """Ensure to return a list of values.

    From ``rebulk.loose.ensure_list``.
    """
    if value is None:
        return []
    if not is_iterable(value):
        return [cast(T, value)]
    return list(value)


def modification_date(filepath: os.PathLike | str) -> float:
    """Get the modification date of the file."""
    # Use the more cross-platform modification time.
    return os.path.getmtime(filepath)


def creation_date(filepath: os.PathLike | str) -> float:
    """Get the creation date of the file.

    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    # Use creation time (although it may not be correct)
    if platform.system() == 'Windows':
        return os.path.getctime(filepath)
    stat = os.stat(filepath)
    try:
        return stat.st_birthtime  # type: ignore[no-any-return,attr-defined]
    except AttributeError:
        # We're probably on Linux. No easy way to get creation dates here,
        # so we'll settle for when its content was last modified.
        return stat.st_mtime


def get_age(
    filepath: os.PathLike | str,
    *,
    reference_date: datetime | None = None,
    use_ctime: bool = False,
) -> timedelta:
    """Get the age of the file from modification time (and creation time, optionally).

    :param str filepath: the path of the file.
    :param (datetime | None) reference_date: the datetime object to use as reference to calculate age.
        Defaults to `datetime.now(timeinfo.utc)`.
    :param bool use_ctime: if True, use the latest of modification and creation time to calculate age,
        instead of using only the modification time.

    """
    if not os.path.exists(filepath):
        return timedelta()

    file_date = modification_date(filepath)
    if use_ctime:
        file_date = max(file_date, creation_date(filepath))
    reference_date = reference_date if reference_date is not None else datetime.now(timezone.utc)
    return reference_date - datetime.fromtimestamp(file_date, timezone.utc)
