# -*- coding: utf-8 -*-
from bs4 import FeatureNotFound
import pytest

from subliminal.providers import ParserBeautifulSoup, Provider, get_version
from subliminal.video import Episode, Movie


def test_parserbeautifulsoup_reject_features():
    with pytest.raises(ValueError):
        ParserBeautifulSoup('', ['lxml', 'html'])


def test_parserbeautifulsoup_reject_builder_kwarg():
    with pytest.raises(ValueError):
        ParserBeautifulSoup('', ['lxml', 'html.parser'], builder='reject')


def test_parserbeautifulsoup_reject_features_kwarg():
    with pytest.raises(ValueError):
        ParserBeautifulSoup('', ['lxml', 'html.parser'], features='reject')


def test_parserbeautifulsoup_no_parser():
    with pytest.raises(FeatureNotFound):
        ParserBeautifulSoup('', ['myparser'])


def test_parserbeautifulsoup():
    ParserBeautifulSoup('', ['lxml', 'html.parser'])


def test_check_episodes_only(episodes, movies):
    Provider.video_types = (Episode,)
    Provider.required_hash = None
    assert Provider.check(movies['man_of_steel']) is False
    assert Provider.check(episodes['bbt_s07e05']) is True


def test_check_movies_only(episodes, movies):
    Provider.video_types = (Movie,)
    Provider.required_hash = None
    assert Provider.check(movies['man_of_steel']) is True
    assert Provider.check(episodes['bbt_s07e05']) is False


def test_check_required_hash(episodes, movies):
    Provider.video_types = (Episode, Movie)
    Provider.required_hash = 'opensubtitles'
    assert Provider.check(movies['man_of_steel']) is True
    assert Provider.check(episodes['dallas_s01e03']) is False


@pytest.mark.parametrize('input,expected', [
    ('1.0.dev0', '1.0'),
    ('0.7.5', '0.7'),
    ('0.6', '0.6')
])
def test_get_version(input, expected):
    assert get_version(input) == expected
