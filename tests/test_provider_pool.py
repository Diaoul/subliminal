from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock, call

import pytest
from babelfish import Language  # type: ignore[import-untyped]

from subliminal.core import (
    AsyncProviderPool,
    ProviderPool,
    download_best_subtitles,
    download_subtitles,
    list_subtitles,
    refine,
    refiner_manager,
)
from subliminal.score import episode_scores
from subliminal.subtitle import Subtitle

if TYPE_CHECKING:
    from typing import Callable

    from subliminal.extensions import RegistrableExtensionManager
    from subliminal.providers.mock import MockProvider
    from subliminal.video import Episode, Movie, Video

# Core test
pytestmark = [
    pytest.mark.core,
    pytest.mark.usefixtures('provider_manager'),
    pytest.mark.usefixtures('disabled_providers'),
]


@pytest.fixture
def _mock_providers(monkeypatch: pytest.MonkeyPatch, provider_manager: RegistrableExtensionManager) -> None:
    for provider in provider_manager:
        monkeypatch.setattr(provider.plugin, 'initialize', Mock())
        monkeypatch.setattr(provider.plugin, 'list_subtitles', Mock(return_value=[provider.name]))
        monkeypatch.setattr(provider.plugin, 'download_subtitle', Mock())
        monkeypatch.setattr(provider.plugin, 'terminate', Mock())


@pytest.fixture
def mock_refiners(monkeypatch: pytest.MonkeyPatch) -> Mock:
    mock = Mock()

    def mock_and_refine(refiner_name: str) -> Callable:
        def mock_refine(video: Video, **kwargs: Any) -> None:
            mock(refiner_name)

        return mock_refine

    for refiner in refiner_manager:
        monkeypatch.setattr(refiner, 'plugin', mock_and_refine(refiner.name))

    return mock


@pytest.fixture
def mock_refiners_hash_broken(monkeypatch: pytest.MonkeyPatch) -> Mock:
    mock = Mock()

    def mock_and_refine(refiner_name: str) -> Callable:
        def mock_refine(video: Video, **kwargs: Any) -> None:
            if refiner_name == 'hash':
                raise ValueError
            mock(refiner_name)

        return mock_refine

    for refiner in refiner_manager:
        monkeypatch.setattr(refiner, 'plugin', mock_and_refine(refiner.name))

    return mock


def test_provider_pool_get_keyerror() -> None:
    pool = ProviderPool()
    with pytest.raises(KeyError):
        pool['nwodtseg']


def test_provider_pool_del_keyerror() -> None:
    pool = ProviderPool()
    with pytest.raises(KeyError):
        del pool['gestdown']


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_iter() -> None:
    pool = ProviderPool()
    assert len(list(pool)) == 0
    pool['tvsubtitles']
    # test printing
    print(pool['tvsubtitles'])  # noqa: T201
    assert len(list(pool)) == 1


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_list_subtitles_provider(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    pool = ProviderPool()
    subtitles = pool.list_subtitles_provider('tvsubtitles', episodes['bbt_s07e05'], {Language('eng')})
    assert subtitles == ['tvsubtitles']  # type: ignore[comparison-overlap]
    assert provider_manager['tvsubtitles'].plugin.initialize.called  # type: ignore[attr-defined]
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_provider_pool_list_subtitles(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    pool = ProviderPool()
    subtitles = pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
    assert sorted(subtitles) == [  # type: ignore[type-var,comparison-overlap]
        'gestdown',
        'opensubtitlescom',
        'podnapisi',
        'tvsubtitles',
    ]
    for provider in subtitles:
        provider_s = cast('str', provider)
        assert provider_manager[provider_s].plugin.initialize.called  # type: ignore[attr-defined]
        assert provider_manager[provider_s].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_async_provider_pool_list_subtitles_provider(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    pool = AsyncProviderPool()
    subtitles = pool.list_subtitles_provider_tuple('tvsubtitles', episodes['bbt_s07e05'], {Language('eng')})
    assert subtitles == ('tvsubtitles', ['tvsubtitles'])  # type: ignore[comparison-overlap]
    assert provider_manager['tvsubtitles'].plugin.initialize.called  # type: ignore[attr-defined]
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_async_provider_pool_list_subtitles(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    pool = AsyncProviderPool()
    subtitles = pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
    assert sorted(subtitles) == [  # type: ignore[type-var,comparison-overlap]
        'gestdown',
        'opensubtitlescom',
        'podnapisi',
        'tvsubtitles',
    ]
    for provider in subtitles:
        provider_s = cast('str', provider)
        assert provider_manager[provider_s].plugin.initialize.called  # type: ignore[attr-defined]
        assert provider_manager[provider_s].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_movie(
    movies: dict[str, Movie],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('gestdown', 'tvsubtitles', 'opensubtitlescomvip'):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    for name in ('opensubtitlescom', 'podnapisi'):
        assert provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[movies['man_of_steel']]) == ['opensubtitlescom', 'podnapisi']  # type: ignore[type-var,comparison-overlap]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_episode(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('heb')}

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in ('opensubtitlescomvip',):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    for name in (
        'gestdown',
        'opensubtitlescom',
        'podnapisi',
        'tvsubtitles',
    ):
        assert provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == [  # type: ignore[type-var,comparison-overlap]
        'gestdown',
        'opensubtitlescom',
        'podnapisi',
        'tvsubtitles',
    ]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_providers(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    subtitles = list_subtitles({video}, languages, providers=['opensubtitlescom'])

    # test providers
    for name in ('podnapisi', 'gestdown', 'tvsubtitles', 'opensubtitlescomvip'):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    for name in ('opensubtitlescom',):
        assert provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 1
    assert sorted(subtitles[episodes['bbt_s07e05']]) == ['opensubtitlescom']  # type: ignore[type-var,comparison-overlap]


@pytest.mark.usefixtures('_mock_providers')
def test_list_subtitles_no_language(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = episodes['dallas_s01e03']
    languages = {Language('eng')}
    video.subtitles = [Subtitle(lang) for lang in languages]

    subtitles = list_subtitles({video}, languages)

    # test providers
    for name in (
        'opensubtitlescom',
        'opensubtitlescomvip',
        'gestdown',
        'podnapisi',
        'tvsubtitles',
    ):
        assert not provider_manager[name].plugin.list_subtitles.called  # type: ignore[attr-defined]

    # test result
    assert len(subtitles) == 0


@pytest.mark.usefixtures('_mock_providers')
def test_download_subtitles(provider_manager: RegistrableExtensionManager) -> None:
    from subliminal.providers.mock import MockSubtitle

    MockTVsubtitlesSubtitle = type('MockTVsubtitlesSubtitle', (MockSubtitle,), {'provider_name': 'tvsubtitles'})

    subtitles = [
        MockTVsubtitlesSubtitle(
            language=Language('por'),
            subtitle_id='261077',
            page_link=None,
            parameters={
                'series': 'Game of Thrones',
                'season': 3,
                'episode': 10,
                'year': None,
                'rip': '1080p.BluRay',
                'release': 'DEMAND',
            },
        ),
    ]
    download_subtitles(subtitles)

    # test providers
    for name in ('gestdown', 'opensubtitlescom', 'opensubtitlescomvip', 'podnapisi'):
        assert not provider_manager[name].plugin.download_subtitle.called  # type: ignore[attr-defined]

    for name in ('tvsubtitles',):
        assert provider_manager[name].plugin.download_subtitle.called  # type: ignore[attr-defined]


def test_list_subtitles_discarded_provider(
    movies: dict[str, Movie],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}

    pool = ProviderPool(['opensubtitlescom'])

    # Working provider
    subtitles = pool.list_subtitles(video, languages)
    assert len(subtitles) == 1
    # keep listed subtitle
    subtitle = subtitles[0]

    provider = cast('MockProvider', pool['opensubtitlescom'])

    # Mock a broken provider
    provider.is_broken = True
    subtitles = pool.list_subtitles(video, languages)
    assert len(subtitles) == 0

    # Mock the provider now works, but it was discarded
    provider.is_broken = False
    assert 'opensubtitlescom' in pool.discarded_providers

    subtitles = pool.list_subtitles(video, languages)
    assert len(subtitles) == 0

    # Try failing downloading from discarded provider
    assert not pool.download_subtitle(subtitle)


def test_async_provider_pool_list_subtitles_discarded_providers(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    pool = AsyncProviderPool(max_workers=1)
    # One provider is broken
    cast('MockProvider', pool['opensubtitlescom']).is_broken = True

    subtitles = pool.list_subtitles(video, languages)
    assert {s.provider_name for s in subtitles} == {
        'gestdown',
        'podnapisi',
        'tvsubtitles',
    }
    assert 'opensubtitlescom' in pool.discarded_providers


def test_download_subtitles_discarded_provider(
    movies: dict[str, Movie],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}

    pool = ProviderPool(['opensubtitlescom'])

    # Working provider
    subtitles = pool.list_subtitles(video, languages)
    assert len(subtitles) == 1
    # keep listed subtitle
    subtitle = subtitles[0]
    assert 'opensubtitlescom' not in pool.discarded_providers

    # Mock a broken provider
    cast('MockProvider', pool['opensubtitlescom']).is_broken = True
    # Try failing downloading subtitle
    assert not pool.download_subtitle(subtitle)

    assert 'opensubtitlescom' in pool.discarded_providers


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


def test_download_best_subtitles_min_score(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    providers = ['gestdown']

    # No minimum score
    subtitles = download_best_subtitles({video}, languages, min_score=0, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 1

    # With minimum score
    subtitles = download_best_subtitles({video}, languages, min_score=episode_scores['hash'], providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 0


def test_download_best_subtitles_embedded_language(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('fra')}
    providers = ['gestdown']

    # Download best subtitle for given language
    subtitles = download_best_subtitles({video}, languages, only_one=True, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 1

    # With an embedded subtitle with given language
    video.subtitles = [Subtitle(lang) for lang in languages]
    subtitles = download_best_subtitles({video}, languages, providers=providers)

    assert len(subtitles) == 0


def test_download_best_subtitles_undefined(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('und')}
    providers = ['gestdown']

    # Download best subtitle for undefined language
    subtitles = download_best_subtitles({video}, languages, only_one=True, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 0

    # With an embedded subtitle with undefined language
    video.subtitles = [Subtitle(lang) for lang in languages]
    subtitles = download_best_subtitles({video}, languages, only_one=True, providers=providers)

    assert len(subtitles) == 0


def test_download_best_subtitles_no_language_provider(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('heb')}
    providers = ['gestdown']

    # Download best subtitle for provider that does not support the language
    subtitles = download_best_subtitles({video}, languages, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 0


def test_download_best_subtitles_only_one(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('por', 'BR')}
    providers = ['gestdown', 'podnapisi']
    expected_subtitles = {
        ('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6'),
        ('podnapisi', 'EdQo'),
    }

    subtitles = download_best_subtitles({video}, languages, only_one=True, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 1
    subtitle = subtitles[video][0]
    assert (subtitle.provider_name, subtitle.id) in expected_subtitles


def test_download_best_subtitles_language_type(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}
    providers = ['gestdown', 'podnapisi', 'tvsubtitles']
    expected_subtitles = {
        ('tvsubtitles', '23329'),
        # ('podnapisi', 'EdQo'),
        # ('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6'),
    }

    subtitles = download_best_subtitles({video}, languages, hearing_impaired=True, providers=providers)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 1
    assert {(s.provider_name, s.id) for s in subtitles[video]} == expected_subtitles


def test_download_best_subtitles_wrong_fps(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng'), Language('fra')}
    providers = ['tvsubtitles', 'gestdown']
    # with skip_wrong_fps=False, tvsubtitles would be best for Language('eng')
    expected_subtitles = {
        # ('tvsubtitles', '23329'),
        ('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6'),
        ('gestdown', '90fe1369-fa0c-4154-bd04-d3d332dec587'),
    }

    assert video.frame_rate == 23.976
    subtitles = download_best_subtitles({video}, languages, providers=providers, skip_wrong_fps=True)

    assert len(subtitles) == 1
    assert len(subtitles[video]) == 2
    assert {(s.provider_name, s.id) for s in subtitles[video]} == expected_subtitles


def test_download_bad_subtitle(movies: dict[str, Movie]) -> None:
    pool = ProviderPool()
    subtitles = pool.list_subtitles_provider('opensubtitlescom', movies['man_of_steel'], {Language('tur')})
    assert subtitles is not None
    assert len(subtitles) >= 1
    subtitle = subtitles[0]

    # The subtitle has no content
    pool.download_subtitle(subtitle)

    assert subtitle.content is None
    assert subtitle.is_valid() is False


def test_list_subtitles_providers_download(episodes: dict[str, Episode], disabled_providers: list[str]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    # Disable a provider
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


def test_refine_movie(movies: dict[str, Episode], mock_refiners: Mock) -> None:
    video = movies['man_of_steel']

    refine(video)

    calls = [call('hash'), call('metadata'), call('omdb'), call('tmdb')]
    mock_refiners.assert_has_calls(calls, any_order=True)


def test_refine_episode(episodes: dict[str, Episode], mock_refiners: Mock) -> None:
    video = episodes['bbt_s07e05']

    refine(video)

    calls = [call('hash'), call('metadata'), call('omdb'), call('tmdb'), call('tvdb')]
    mock_refiners.assert_has_calls(calls, any_order=True)


def test_refine_movie_broken(movies: dict[str, Episode], mock_refiners_hash_broken: Mock) -> None:
    video = movies['man_of_steel']

    refine(video)

    calls = [call('metadata'), call('omdb'), call('tmdb')]
    mock_refiners_hash_broken.assert_has_calls(calls, any_order=True)
