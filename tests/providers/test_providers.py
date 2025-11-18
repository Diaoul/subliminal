import os
from typing import cast
from unittest.mock import Mock

import pytest
from babelfish import Language  # type: ignore[import-untyped]
from vcr import VCR  # type: ignore[import-untyped]

from subliminal.core import (
    AsyncProviderPool,
    ProviderPool,
    download_best_subtitles,
    download_subtitles,
    list_subtitles,
)
from subliminal.extensions import disabled_providers, provider_manager
from subliminal.providers.tvsubtitles import TVsubtitlesSubtitle
from subliminal.score import episode_scores
from subliminal.subtitle import Subtitle
from subliminal.video import Episode, Movie

vcr = VCR(
    path_transformer=lambda path: path + '.yaml',
    record_mode=os.environ.get('VCR_RECORD_MODE', 'once'),
    decode_compressed_response=True,
    match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
    cassette_library_dir=os.path.realpath(os.path.join('tests', 'cassettes', 'providers')),
)


@pytest.fixture
def _mock_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    for provider in provider_manager:
        monkeypatch.setattr(provider.plugin, 'initialize', Mock())
        monkeypatch.setattr(provider.plugin, 'list_subtitles', Mock(return_value=[provider.name]))
        monkeypatch.setattr(provider.plugin, 'download_subtitle', Mock())
        monkeypatch.setattr(provider.plugin, 'terminate', Mock())


def test_provider_pool_get_keyerror() -> None:
    pool = ProviderPool()
    with pytest.raises(KeyError):
        pool['de7cidda']


def test_provider_pool_del_keyerror() -> None:
    pool = ProviderPool()
    with pytest.raises(KeyError):
        del pool['addic7ed']


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_iter() -> None:
    pool = ProviderPool()
    assert len(list(pool)) == 0
    pool['tvsubtitles']
    assert len(list(pool)) == 1


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_list_subtitles_provider(episodes: dict[str, Episode]) -> None:
    pool = ProviderPool()
    subtitles = pool.list_subtitles_provider('tvsubtitles', episodes['bbt_s07e05'], {Language('eng')})
    assert subtitles == ['tvsubtitles']  # type: ignore[comparison-overlap]
    assert provider_manager['tvsubtitles'].plugin.initialize.called  # type: ignore[attr-defined]
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_list_subtitles(episodes: dict[str, Episode]) -> None:
    pool = ProviderPool()
    subtitles = pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
    assert sorted(subtitles) == [  # type: ignore[type-var,comparison-overlap]
        'addic7ed',
        'gestdown',
        'opensubtitles',
        'opensubtitlescom',
        'podnapisi',
        'subtitulamos',
        'tvsubtitles',
    ]
    for provider in subtitles:
        provider_s = cast('str', provider)
        assert provider_manager[provider_s].plugin.initialize.called  # type: ignore[attr-defined]
        assert provider_manager[provider_s].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_async_provider_pool_list_subtitles_provider(episodes: dict[str, Episode]) -> None:
    pool = AsyncProviderPool()
    subtitles = pool.list_subtitles_provider_tuple('tvsubtitles', episodes['bbt_s07e05'], {Language('eng')})
    assert subtitles == ('tvsubtitles', ['tvsubtitles'])  # type: ignore[comparison-overlap]
    assert provider_manager['tvsubtitles'].plugin.initialize.called  # type: ignore[attr-defined]
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_async_provider_pool_list_subtitles(episodes: dict[str, Episode]) -> None:
    pool = AsyncProviderPool()
    subtitles = pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
    assert sorted(subtitles) == [  # type: ignore[type-var,comparison-overlap]
        'addic7ed',
        'gestdown',
        'opensubtitles',
        'opensubtitlescom',
        'podnapisi',
        'subtitulamos',
        'tvsubtitles',
    ]
    for provider in subtitles:
        provider_s = cast('str', provider)
        assert provider_manager[provider_s].plugin.initialize.called  # type: ignore[attr-defined]
        assert provider_manager[provider_s].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_movie(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitlesvip', 'tvsubtitles'):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    for name in ('opensubtitles', 'opensubtitlescom', 'podnapisi'):
        assert provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[movies['man_of_steel']]) == ['opensubtitles', 'opensubtitlescom', 'podnapisi']  # type: ignore[type-var,comparison-overlap]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_episode(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('heb')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('napiprojekt', 'opensubtitlesvip', 'opensubtitlescomvip'):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    for name in (
        'addic7ed',
        'gestdown',
        'opensubtitles',
        'opensubtitlescom',
        'podnapisi',
        'subtitulamos',
        'tvsubtitles',
    ):
        assert provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == [  # type: ignore[type-var,comparison-overlap]
        'addic7ed',
        'gestdown',
        'opensubtitles',
        'opensubtitlescom',
        'podnapisi',
        'subtitulamos',
        'tvsubtitles',
    ]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_providers(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages, providers=['opensubtitles'])

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitlesvip', 'podnapisi', 'tvsubtitles'):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    for name in ('opensubtitles',):
        assert provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == ['opensubtitles']  # type: ignore[type-var,comparison-overlap]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_episode_no_hash(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_s01e03']
    languages = {Language('eng'), Language('heb')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('napiprojekt', 'opensubtitlesvip', 'opensubtitlescomvip'):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    for name in ('addic7ed', 'gestdown', 'opensubtitles', 'podnapisi', 'subtitulamos', 'tvsubtitles'):
        assert provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['dallas_s01e03']]) == [  # type: ignore[type-var,comparison-overlap]
        'addic7ed',
        'gestdown',
        'opensubtitles',
        'opensubtitlescom',
        'podnapisi',
        'subtitulamos',
        'tvsubtitles',
    ]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_no_language(episodes: dict[str, Episode]) -> None:
    video = episodes['dallas_s01e03']
    languages = {Language('eng')}
    video.subtitles = [Subtitle(lang) for lang in languages]

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in (
        'addic7ed',
        'napiprojekt',
        'opensubtitles',
        'opensubtitlesvip',
        'podnapisi',
        'tvsubtitles',
    ):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 0


@pytest.mark.usefixtures('_mock_providers')
def test_download_subtitles() -> None:
    subtitles = [
        TVsubtitlesSubtitle(
            language=Language('por'),
            subtitle_id='261077',
            page_link=None,
            series='Game of Thrones',
            season=3,
            episode=10,
            year=None,
            rip='1080p.BluRay',
            release='DEMAND',
        )
    ]

    download_subtitles(subtitles)

    # test providers
    for name in ('addic7ed', 'napiprojekt', 'opensubtitles', 'opensubtitlesvip', 'podnapisi'):
        assert not provider_manager[name].plugin.download_subtitle.called  # type: ignore[attr-defined]

    for name in ('tvsubtitles',):
        assert provider_manager[name].plugin.download_subtitle.called  # type: ignore[attr-defined]


@pytest.mark.integration
@vcr.use_cassette
def test_download_best_subtitles(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    providers = ['gestdown', 'podnapisi']
    expected_subtitles = {
        ('podnapisi', 'EdQo'),
        ('podnapisi', 'Dego'),
        # ('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6'),
        # ('gestdown', '90fe1369-fa0c-4154-bd04-d3d332dec587'),
    }

    subtitles = download_best_subtitles({video}, languages, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 2
    assert {(s.provider_name, s.id) for s in subtitles[video]} == expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_download_best_subtitles_min_score(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    providers = ['gestdown']

    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 0


def test_download_best_subtitles_no_language(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    video.subtitles = [Subtitle(lang) for lang in languages]
    providers = ['gestdown']

    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], providers=providers)

    assert len(subtitles) == 0


def test_download_best_subtitles_undefined(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('und')}
    video.subtitles = [Subtitle(lang) for lang in languages]
    providers = ['gestdown']

    subtitles = download_best_subtitles(
        {video}, languages, min_score=episode_scores['hash'], only_one=True, providers=providers
    )

    assert len(subtitles) == 0


@pytest.mark.integration
@vcr.use_cassette
def test_download_best_subtitles_only_one(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('por', 'BR')}
    providers = ['gestdown', 'podnapisi']
    expected_subtitles = {
        ('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6'),
        ('gestdown', 'a245f3f1-920f-41f5-b9af-876a633cc8dd'),
        ('podnapisi', 'EdQo'),
    }

    subtitles = download_best_subtitles({video}, languages, only_one=True, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 1
    subtitle = subtitles[video][0]
    assert (subtitle.provider_name, subtitle.id) in expected_subtitles


@pytest.mark.integration
@vcr.use_cassette
def test_list_subtitles_providers_download(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    # modify global variable
    try:
        if 'gestdown' not in disabled_providers:
            disabled_providers.append('gestdown')

        # no subtitles from 'gestdown'
        subtitles = list_subtitles({video}, languages)
        assert not any(sub.provider_name == 'gestdown' for sub in subtitles[video])

        # force using 'gestdown', bypass default when init ProviderPool
        subtitles = list_subtitles({video}, languages, providers=['gestdown'])

        # test result
        assert len(subtitles) == 1
        assert len(subtitles[video]) > 0
        subtitle = subtitles[video][0]
        assert subtitle.provider_name == 'gestdown'
        assert subtitle.content is None

        # download subtitles
        download_subtitles([subtitle], providers=['gestdown'])
        assert subtitle.content is not None

        # force using 'gestdown', bypass default when init ProviderPool
        subtitles = list_subtitles({video}, languages, providers=['gestdown'])

    finally:
        # reset global variable
        if 'gestdown' in disabled_providers:
            disabled_providers.remove('gestdown')
