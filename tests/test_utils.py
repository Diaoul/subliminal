from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any
from xmlrpc.client import ProtocolError

import pytest
import requests

from subliminal.exceptions import ServiceUnavailable
from subliminal.utils import (
    clip,
    creation_date,
    decorate_imdb_id,
    ensure_list,
    ensure_str,
    get_age,
    get_extend_and_ignore_union,
    handle_exception,
    matches_extended_title,
    merge_extend_and_ignore_unions,
    modification_date,
    sanitize,
    sanitize_id,
    sanitize_release_group,
    trim_pattern,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

# Core test
pytestmark = pytest.mark.core


@pytest.fixture
def docstring() -> str:
    """Generate a docstring with arguments."""
    return """Some class or function.

        This object has only one purpose: parsing.

        :param :class:`~babelfish.language.Language` language: the language of the subtitles.
        :param str keyword: the query term.
        :param (int | None) season: the season number.
        :param episode: the episode number.
        :type episode: int
        :param (int | None) year: the video year and
            on another line.
        :return: something
        """


def test_sanitize() -> None:
    assert sanitize(None) is None
    assert sanitize("Marvel's Agents of S.H.I.E.L.D.") == 'marvels agents of s h i e l d'


def test_sanitize_release_group() -> None:
    assert sanitize_release_group(None) is None
    assert sanitize_release_group(' Lol[x264]') == 'LOL'


def test_sanitize_id() -> None:
    assert sanitize_id(None) is None
    assert sanitize_id('tt0770828') == 770828

    assert decorate_imdb_id(sanitize_id(None)) is None
    assert decorate_imdb_id(sanitize_id('tt0770828')) == 'tt0770828'

    assert decorate_imdb_id(203) == 'tt0000203'


def test_get_creation_date(tmp_path: Path) -> None:
    NOW = datetime.datetime.now(datetime.timezone.utc)

    content = 'content'
    p = tmp_path / 'test.txt'
    p.write_text(content, encoding='utf-8')

    mdate = datetime.datetime.fromtimestamp(modification_date(p), tz=datetime.timezone.utc)
    cdate = datetime.datetime.fromtimestamp(creation_date(p), tz=datetime.timezone.utc)
    assert abs((cdate - mdate).total_seconds()) < 2
    assert abs((cdate - NOW).total_seconds()) < 2


def test_get_age(monkeypatch: pytest.MonkeyPatch) -> None:
    NOW = datetime.datetime.now(datetime.timezone.utc)

    # mock file age
    def mock_modification_date(filepath: str, **kwargs: Any) -> float:
        return (NOW - datetime.timedelta(weeks=2)).timestamp()

    def mock_creation_date_later(*args: Any) -> float:
        return (NOW - datetime.timedelta(weeks=1)).timestamp()

    def mock_creation_date_sooner(*args: Any) -> float:
        return (NOW - datetime.timedelta(weeks=3)).timestamp()

    monkeypatch.setattr('subliminal.utils.modification_date', mock_modification_date)
    monkeypatch.setattr('subliminal.utils.creation_date', mock_creation_date_later)

    age = get_age(__file__, use_ctime=False, reference_date=NOW)
    assert age == datetime.timedelta(weeks=2)

    c_age = get_age(__file__, use_ctime=True, reference_date=NOW)
    assert c_age == datetime.timedelta(weeks=1)

    not_file_age = get_age('not-a-file.txt', reference_date=NOW)
    assert not_file_age == datetime.timedelta()

    # creation sooner
    monkeypatch.setattr('subliminal.utils.creation_date', mock_creation_date_sooner)

    c_age_2 = get_age(__file__, use_ctime=True, reference_date=NOW)
    assert c_age_2 == datetime.timedelta(weeks=2)


@pytest.mark.parametrize(
    ('actual', 'title', 'alt', 'expected'),
    [
        (None, 'The Big Bang Theory', [], False),
        ('The Big Bang Theory', None, [], False),
        ('the.big.bang.theory', 'The Big Bang Theory', [], True),
        ('the.big.bang.theory', 'Big Bang Theory', None, False),
        ('the.big.bang.theory', 'Big Bang Theory', ['The Big Bang Theory'], True),
        ('the.big.bang.theory', 'Big Bang Theory', ['Not The Big Bang Theory'], False),
    ],
)
def test_matches_extended_title(actual: str | None, title: str | None, alt: list[str], expected: bool) -> None:
    ret = matches_extended_title(actual, title, alt)
    assert ret == expected


@pytest.mark.parametrize(
    ('err', 'msg'),
    [
        (requests.Timeout(), 'Request timed out'),
        (ServiceUnavailable(), 'Service unavailable'),
        (ProtocolError('', 0, '', {}), 'Service unavailable'),
        (requests.exceptions.HTTPError(response=requests.Response()), 'HTTP error'),
        (requests.exceptions.SSLError(''), 'SSL error'),
        (ValueError(), 'Unexpected error'),
    ],
)
def test_handle_exception(caplog: pytest.LogCaptureFixture, err: Exception, msg: str) -> None:
    handle_exception(err, '')
    for record in caplog.records:
        assert record.levelname == 'ERROR'
        assert record.message.startswith(msg)


def test_ensure_list() -> None:
    ret: list = ensure_list(None)
    assert isinstance(ret, list)
    assert ret == []

    ret = ensure_list('a')
    assert isinstance(ret, list)
    assert set(ret) == {'a'}

    ret = ensure_list(('a', 'b'))
    assert isinstance(ret, list)
    assert set(ret) == {'a', 'b'}

    ret = ensure_list({'a', 'b'})  # type: ignore[arg-type]
    assert isinstance(ret, list)
    assert set(ret) == {'a', 'b'}


def test_ensure_str() -> None:
    ret: str = ensure_str(None)
    assert isinstance(ret, str)
    assert ret == ''

    ret = ensure_str('a')
    assert isinstance(ret, str)
    assert ret == 'a'

    ret = ensure_str(('a', 'b'))
    assert isinstance(ret, str)
    assert ret == 'a b'

    ret = ensure_str(['a', 'b'], sep=' - ')
    assert isinstance(ret, str)
    assert ret == 'a - b'


@pytest.mark.parametrize(
    ('select', 'extend', 'ignore', 'defaults', 'expected'),
    [
        (None, None, None, None, set()),
        (None, None, None, ['a', 'b'], {'a', 'b'}),
        ([], None, None, ['a', 'b'], {'a', 'b'}),
        ([], [], ['a'], ['a', 'b'], {'b'}),
        ([], ['c'], ['a'], ['a', 'b'], {'b', 'c'}),
        (['a'], ['b'], ['c'], ['a', 'b'], {'a', 'b'}),
        (['a', 'b', 'c'], ['c'], ['a'], ['a', 'b'], {'b', 'c'}),
        (['a', 'b'], ['c'], ['c'], ['a', 'b'], {'a', 'b'}),
        ([], ['c'], ['c'], ['a', 'b'], {'a', 'b'}),
        (['ALL'], ['b'], [], ['a', 'b'], {'a', 'b'}),
        (['ALL'], ['c'], [], ['a', 'b'], {'a', 'b', 'c'}),
        (['ALL'], [], ['b'], ['a', 'b'], {'a'}),
        (['c'], ['ALL'], [], ['a', 'b'], {'a', 'b', 'c'}),
        ([], [], ['ALL'], ['a', 'b'], set()),
        (['ALL'], [], ['ALL'], ['a', 'b'], set()),
        (['ALL'], ['ALL'], ['ALL'], ['a', 'b'], set()),
    ],
)
def test_get_extend_and_ignore_union(
    select: list[str] | None,
    extend: list[str] | None,
    ignore: list[str] | None,
    defaults: list[str] | None,
    expected: set[str],
) -> None:
    final = set(get_extend_and_ignore_union(select, extend, ignore, defaults))
    assert final == expected


@pytest.mark.parametrize(
    ('lists', 'default_lists', 'defaults', 'expected'),
    [
        (
            {'select': None, 'extend': None, 'ignore': None},
            {'select': None, 'extend': None, 'ignore': None},
            ['a', 'b'],
            {'a', 'b'},
        ),
        (
            {'select': None, 'extend': None, 'ignore': 'ALL'},
            {'select': None, 'extend': None, 'ignore': None},
            ['a', 'b'],
            set(),
        ),
        (
            {'select': None, 'extend': None, 'ignore': None},
            {'select': None, 'extend': None, 'ignore': 'ALL'},
            ['a', 'b'],
            set(),
        ),
        (
            {'select': ['c'], 'extend': None, 'ignore': None},
            {'select': None, 'extend': None, 'ignore': 'ALL'},
            ['a', 'b'],
            {'c'},
        ),
        (
            {'select': ['c'], 'extend': ['ALL'], 'ignore': None},
            {'select': None, 'extend': None, 'ignore': 'ALL'},
            ['a', 'b'],
            {'a', 'b', 'c'},
        ),
    ],
)
def test_merge_extend_and_ignore_unions(
    lists: dict,
    default_lists: dict,
    defaults: list[str],
    expected: set[str],
) -> None:
    final = set(merge_extend_and_ignore_unions(lists, default_lists, defaults))  # type: ignore[arg-type]
    assert final == expected


@pytest.mark.parametrize(
    ('value', 'minimum', 'maximum', 'expected'),
    [
        (1, None, None, 1),
        (1, 0, 2, 1),
        (1, 2, 0, 2),
        (1, -1, 0, 0),
        (1, 2, 4, 2),
    ],
)
def test_clip(value: float, minimum: float | None, maximum: float | None, expected: float) -> None:
    out = clip(value, minimum, maximum)
    assert out == expected


@pytest.mark.parametrize(
    ('string', 'patterns', 'sep', 'expected'),
    [
        ('en', 'hi', '.', ('en', '')),
        ('[hi].en', '[hi]', '.', ('en', '[hi]')),
        ('fra.sdh', ('sdh',), '.', ('fra', 'sdh')),
        ('ukr-UA-cyrl.[fo]', ('[fo]',), '.', ('ukr-UA-cyrl', '[fo]')),
        ('fo.hi', ('fo',), '.', ('hi', 'fo')),
        ('fo.hi', ('hi',), '.', ('fo', 'hi')),
        ('mkv.it', ('hi', 'cc', 'sdh'), '.', ('mkv.it', '')),
    ],
)
def test_trim_pattern(string: str, patterns: str | Sequence[str], sep: str, expected: tuple[str, str]) -> None:
    res = trim_pattern(string, patterns, sep=sep)
    assert res == expected
