from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pytest

from subliminal.cli.helpers import (
    get_argument_doc,
    get_parameters_from_signature,
    split_doc_args,
)

if TYPE_CHECKING:
    from babelfish import Language  # type: ignore[import-untyped]

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


def test_split_doc_args(docstring: str) -> None:
    parts = split_doc_args(docstring)
    assert len(parts) == 5
    assert all(p.startswith(':param ') for p in parts)
    assert '\n' in parts[4]


@pytest.mark.parametrize('is_class', [False, True])
def test_get_argument_doc(docstring: str, is_class: bool) -> None:
    obj: Callable
    if is_class:

        def obj() -> None:
            pass

    else:

        class obj:  # type: ignore[no-redef]
            pass

    obj.__doc__ = docstring

    d = get_argument_doc(obj)
    assert d == {
        'language': 'the language of the subtitles.',
        'keyword': 'the query term.',
        'season': 'the season number.',
        'episode': 'the episode number.',
        'year': 'the video year and on another line.',
    }


def test_get_parameters_from_signature(docstring: str) -> None:
    def fun(
        language: Language | None = None,
        keyword: str = 'key',
        season: int = 0,
        episode: int | None = None,
        year: str | None = None,
        no_desc: bool = False,
    ) -> None:
        pass

    fun.__doc__ = docstring

    params = get_parameters_from_signature(fun)

    assert len(params) == 6

    assert params[0]['name'] == 'language'
    assert params[0]['default'] is None
    assert params[0]['annotation'] == 'Language | None'
    assert params[0]['desc'] == 'the language of the subtitles.'

    assert params[5]['name'] == 'no_desc'
    assert params[5]['default'] is False
    assert params[5]['annotation'] == 'bool'
    assert params[5]['desc'] is None
