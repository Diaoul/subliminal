"""Hash and sanitize functions."""

from __future__ import annotations

import functools
import logging
import os
import platform
import re
import socket
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from types import GeneratorType
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar, cast, overload
from xmlrpc.client import ProtocolError

import requests
from requests.exceptions import SSLError

from .exceptions import ServiceUnavailable

if TYPE_CHECKING:
    from collections.abc import Sequence, Set
    from typing import TypedDict, TypeGuard

    S = TypeVar('S')

    class ExtendedLists(Generic[S], TypedDict):
        """Dict with item to select, extend-select and ignore."""

        select: Sequence[S]
        extend: Sequence[S]
        ignore: Sequence[S]

    class Parameter(TypedDict):
        """Parameter of a function."""

        name: str
        default: Any
        annotation: str | None
        desc: str | None


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
    if characters:  # pragma: no branch
        string = re.sub(r'[{}]'.format(re.escape(''.join(characters))), ' ', string)

    # remove some characters
    characters = {"'"} - ignore_characters
    if characters:  # pragma: no branch
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
    id_ = str(id_).lower().removeprefix('tt')
    return int(id_)


@none_passthrough
def decorate_imdb_id(imdb_id: str | int, *, ndigits: int = 7) -> str:
    """Convert the IMDB id to add the leading 'tt' and the leading zeroes."""
    return 'tt' + str(int(imdb_id)).rjust(ndigits, '0')


def timestamp(date: datetime) -> float:
    """Get the timestamp of the `date` (with timezone).

    :param :class:`datetime.datetime` date: the utc date.
    :return: the timestamp of the date.
    :rtype: float

    """
    return (date - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()


def matches_extended_title(
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
        return [cast('T', value)]
    return list(value)


def ensure_str(value: Any, *, sep: str = ' ') -> str:
    """Ensure to return a str."""
    if value is None:
        return ''
    # If a list of str, join them
    if is_iterable(value):
        return sep.join([str(v) for v in value])
    # Make sure the output is a string
    return str(value)


def modification_date(filepath: os.PathLike | str) -> float:
    """Get the modification date of the file."""
    # Use the more cross-platform modification time.
    return os.path.getmtime(filepath)


def creation_date(filepath: os.PathLike | str) -> float:
    """Get the creation date of the file.

    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See https://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    # Use creation time (although it may not be correct)
    if platform.system() == 'Windows':  # pragma: no cover
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
    :param (`datetime.datetime` | None) reference_date: the datetime object
        to use as reference to calculate age.
        Defaults to `datetime.now(timeinfo.utc)`.
    :param bool use_ctime: if True, use the latest of modification
        and creation time to calculate age, instead of using
        only the modification time.
    :return: the age of the file.
    :rtype: `datetime.timedelta`
    """
    if not os.path.exists(filepath):
        return timedelta()

    file_date = modification_date(filepath)
    if use_ctime:
        file_date = max(file_date, creation_date(filepath))
    reference_date = reference_date if reference_date is not None else datetime.now(timezone.utc)
    return reference_date - datetime.fromtimestamp(file_date, timezone.utc)


def merge_extend_and_ignore_unions(
    lists: ExtendedLists[str],
    default_lists: ExtendedLists[str],
    defaults: Sequence[str] | None = None,
    all_token: str | None = 'ALL',  # noqa: S107
) -> list[str]:
    """Merge lists of item to select and ignore.

    Ignore lists supersede the select lists.
    `lists['select']` and `lists['ignore']` supersede the corresponding lists
    in `default_lists`.

    :param dict[str, str] lists: dict with 'select', 'extend' and 'ignore'
        lists of string names.
    :param dict[str, str] default_lists: dict with 'select', 'extend' and
        'ignore' default lists of string names.
    :param (Sequence[str] | None) defaults: list of default items.
    :param str all_token: token used to represent all the items.
    :return: the list of selected and not ignored items.
    :rtype: list[str]
    """
    extend = lists['extend'] or []
    ignore = lists['ignore'] or []
    defaults = defaults or []

    # Ignore all
    if all_token is not None and all_token in ignore:
        return []

    # Nothing selected, start by the selected list using the default_lists
    if not lists['select']:
        item_set = set(get_extend_and_ignore_union(**default_lists, defaults=defaults, all_token=all_token))
    else:
        item_set = set(lists['select'])

    # Add the extend list
    item_set.update(set(extend))
    # Replace all_token
    if all_token in item_set:
        item_set -= {all_token}
        item_set.update(defaults)
    # Remove the ignore list
    item_set -= set(ignore)

    return list(item_set)


def get_extend_and_ignore_union(
    select: Sequence[str] | None = None,
    extend: Sequence[str] | None = None,
    ignore: Sequence[str] | None = None,
    defaults: Sequence[str] | None = None,
    all_token: str | None = 'ALL',  # noqa: S107
) -> list[str]:
    """Get the list of items to use.

    :param (Sequence[str] | None) select: items to select. Empty sequence or None is equivalent to `defaults`.
    :param (Sequence[str] | None) extend: like 'select', but add additional items (empty sequence does nothing).
    :param (Sequence[str] | None) ignore: items to ignore.
    :param (Sequence[str] | None) defaults: default items
    :param str all_token: token used to represent all the items.
    :return: the list of selected and not ignored items.
    :rtype: list[str]

    """
    extend = extend or []
    ignore = ignore or []
    defaults = defaults or []

    # Ignore all
    if all_token is not None and all_token in ignore:
        return []

    # Start with the defaults
    item_set = set(select or defaults)
    # Add the extend list
    item_set.update(set(extend))
    # Replace all_token
    if all_token is not None and all_token in item_set:
        item_set -= {all_token}
        item_set.update(defaults)
    # Remove the ignore list
    item_set -= set(ignore)

    return list(item_set)


def clip(value: float, minimum: float | None, maximum: float | None) -> float:
    """Clip the value between a minimum and maximum.

    Cheap replacement for the numpy.clip function.

    :param float value: the value to clip (float or int).
    :param (float | None) minimum: the minimum value (no minimum if None).
    :param (float | None) maximum: the maximum value (no maximum if None).
    :return: the clipped value.
    :rtype: float

    """
    if maximum is not None:
        value = min(value, maximum)
    if minimum is not None:
        value = max(value, minimum)
    return value


def trim_pattern(string: str, patterns: str | Sequence[str], *, sep: str = '') -> tuple[str, str]:
    """Trim a prefix or suffix from a string, with an optional separator.

    If patterns is a list, order is important as the first match will be returned.

    :param str string: the string to trim.
    :param patterns: a pattern or list of pattern to match as a prefix or suffix to the string.
    :type patterns: str | Sequence[str]
    :param str sep: a separator for the pattern.
    :return: a tuple with the trimmed string and the matching pattern.
    :rtype: tuple[str, str]
    """
    patterns = ensure_list(patterns)
    # trim hearing_impaired or foreign_only attribute, if present
    for pattern in patterns:
        # suppose a string in the form '<pattern><sep><other>'
        if string.startswith(pattern + sep):
            return string.removeprefix(pattern + sep), pattern
        # suppose a string in the form '<other><sep><pattern>'
        if string.endswith(sep + pattern):
            return string.removesuffix(sep + pattern), pattern

    return string, ''
