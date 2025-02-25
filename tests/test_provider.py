# ruff: noqa: PT011
from __future__ import annotations

import pytest

from subliminal.providers import FeatureNotFound, ParserBeautifulSoup, Provider
from subliminal.video import Episode, Movie

# Core test
pytestmark = pytest.mark.core


def test_parserbeautifulsoup_reject_features() -> None:
    with pytest.raises(ValueError):
        ParserBeautifulSoup('', ['lxml', 'html'])


def test_parserbeautifulsoup_reject_builder_kwarg() -> None:
    with pytest.raises(ValueError):
        ParserBeautifulSoup('', ['lxml', 'html.parser'], builder='reject')


def test_parserbeautifulsoup_reject_features_kwarg() -> None:
    with pytest.raises(ValueError):
        ParserBeautifulSoup('', ['lxml', 'html.parser'], features='reject')


def test_parserbeautifulsoup_no_parser() -> None:
    with pytest.raises(FeatureNotFound):
        ParserBeautifulSoup('', ['myparser'])


def test_parserbeautifulsoup() -> None:
    ParserBeautifulSoup('', ['lxml', 'html.parser'])


def test_check_episodes_only(episodes: dict[str, Episode], movies: dict[str, Movie]) -> None:
    Provider.video_types = (Episode,)
    Provider.required_hash = None
    assert Provider.check(movies['man_of_steel']) is False
    assert Provider.check(episodes['bbt_s07e05']) is True


def test_check_movies_only(episodes: dict[str, Episode], movies: dict[str, Movie]) -> None:
    Provider.video_types = (Movie,)
    Provider.required_hash = None
    assert Provider.check(movies['man_of_steel']) is True
    assert Provider.check(episodes['bbt_s07e05']) is False


def test_check_required_hash(episodes: dict[str, Episode], movies: dict[str, Movie]) -> None:
    Provider.video_types = (Episode, Movie)
    Provider.required_hash = 'opensubtitles'
    assert Provider.check(movies['man_of_steel']) is True
    assert Provider.check(episodes['dallas_s01e03']) is False
