from __future__ import annotations

import asyncio
import logging
import os
import zipfile
from datetime import timedelta
from textwrap import dedent
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar, cast
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from babelfish import Language  # type: ignore[import-untyped]

from subliminal.core import (
    download_best_subtitles,
    download_subtitles,
    list_subtitles,
    refine,
    save_subtitles,
)
from subliminal.exceptions import DiscardingError
from subliminal.provider_pool import (
    AsyncProviderPool,
    AsyncRefinerPool,
    ResultStatus,
    check_video,
    is_async_provider,
    is_async_refiner,
    refiner_manager,
)
from subliminal.providers import AsyncProvider, Provider
from subliminal.refiners import AsyncRefiner, Refiner
from subliminal.score import episode_scores
from subliminal.subtitle import Subtitle
from subliminal.video import Episode
from tests.conftest import ensure

if TYPE_CHECKING:
    from collections.abc import Callable, Set
    from pathlib import Path

    from subliminal.extensions import RegistrableExtensionManager
    from subliminal.providers.mock import MockProvider
    from subliminal.video import Movie, Video

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


def test_check_video_languages(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('fra'), Language('eng')}
    assert check_video(video, languages=languages)
    video.subtitles = [Subtitle(lang) for lang in languages]
    assert not check_video(video, languages=languages)


def test_check_video_age(movies: dict[str, Movie], monkeypatch: pytest.MonkeyPatch) -> None:
    video = movies['man_of_steel']
    monkeypatch.setattr('subliminal.video.Video.age', timedelta(weeks=2))
    assert check_video(video, age=timedelta(weeks=3))
    assert not check_video(video, age=timedelta(weeks=1))


def test_check_video_undefined(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    assert check_video(video, undefined=False)
    assert check_video(video, undefined=True)
    video.subtitles = [Subtitle(Language('und'))]
    assert check_video(video, undefined=False)
    assert not check_video(video, undefined=True)


@pytest.mark.asyncio
async def test_provider_pool_get_keyerror() -> None:
    pool = AsyncProviderPool()
    await pool.initialize()
    with pytest.raises(KeyError):
        await pool.get_provider('nwodtseg')


@pytest.mark.asyncio
@pytest.mark.usefixtures('_mock_providers')
async def test_provider_pool_iter() -> None:
    pool = AsyncProviderPool()
    await pool.initialize()
    assert len(list(pool)) == 0
    await pool.get_provider('tvsubtitles')
    # test printing
    print(await pool.get_provider('tvsubtitles'))  # noqa: T201
    assert len(list(pool)) == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures('_mock_providers')
async def test_provider_pool_list_subtitles_provider(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    episode = episodes['bbt_s07e05']
    languages = {Language('eng')}
    pool = AsyncProviderPool()
    await pool.initialize()
    provider_result = await pool.list_subtitles_provider('tvsubtitles', episode, languages)
    assert provider_result.provider == 'tvsubtitles'
    assert provider_result.video == episode
    assert provider_result.languages == languages
    assert provider_result.subtitles == ['tvsubtitles']  # type: ignore[comparison-overlap]
    assert provider_result.ok()
    assert not provider_result.unsupported()
    assert not provider_result.failure()
    assert not provider_result.outage()
    assert provider_manager['tvsubtitles'].plugin.initialize.called  # type: ignore[attr-defined]
    assert provider_manager['tvsubtitles'].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.asyncio
@pytest.mark.usefixtures('_mock_providers')
async def test_async_provider_pool_list_subtitles(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    pool = AsyncProviderPool()
    await pool.initialize()
    subtitles = await pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
    assert sorted(subtitles) == [  # type: ignore[type-var,comparison-overlap]  # ty: ignore[invalid-argument-type]
        'gestdown',
        'opensubtitlescom',
        'podnapisi',
        'tvsubtitles',
    ]
    for provider in subtitles:
        provider_s = cast('str', provider)
        assert provider_manager[provider_s].plugin.initialize.called  # type: ignore[attr-defined]
        assert provider_manager[provider_s].plugin.list_subtitles.called  # type: ignore[attr-defined]


@pytest.mark.asyncio
@pytest.mark.usefixtures('_mock_providers')
async def test_async_with_provider_pool_list_subtitles(
    episodes: dict[str, Episode],
    provider_manager: RegistrableExtensionManager,
) -> None:
    async with AsyncProviderPool() as pool:
        subtitles = await pool.list_subtitles(episodes['bbt_s07e05'], {Language('eng')})
        assert sorted(subtitles) == [  # type: ignore[type-var,comparison-overlap]  # ty: ignore[invalid-argument-type]
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
    assert sorted(subtitles[movies['man_of_steel']]) == ['opensubtitlescom', 'podnapisi']  # type: ignore[type-var,comparison-overlap]  # ty: ignore[invalid-argument-type]


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
    assert sorted(subtitles[episodes['bbt_s07e05']]) == [  # type: ignore[type-var,comparison-overlap]  # ty: ignore[invalid-argument-type]
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
    assert sorted(subtitles[episodes['bbt_s07e05']]) == ['opensubtitlescom']  # type: ignore[type-var,comparison-overlap]  # ty: ignore[invalid-argument-type]


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


@pytest.mark.asyncio
async def test_list_subtitles_discarded_provider(movies: dict[str, Movie]) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}

    pool = AsyncProviderPool(['opensubtitlescom'])
    await pool.initialize()

    # Working provider
    subtitles = await pool.list_subtitles(video, languages)
    assert len(subtitles) == 1
    # keep listed subtitle
    subtitle = subtitles[0]

    provider = cast('MockProvider', await pool.get_provider('opensubtitlescom'))

    # Mock a broken provider
    provider.is_broken = True
    subtitles = await pool.list_subtitles(video, languages)
    assert len(subtitles) == 0

    # Mock the provider now works, but it was discarded
    provider.is_broken = False
    assert 'opensubtitlescom' in pool.discarded_providers

    subtitles = await pool.list_subtitles(video, languages)
    assert len(subtitles) == 0

    # Try failing downloading from discarded provider
    assert not await pool.download_subtitle(subtitle)


@pytest.mark.asyncio
async def test_list_subtitles_discarding_error_reports_failed_and_discarded(movies: dict[str, Movie]) -> None:
    """A discarding error puts the provider in `failed_providers` and in `discarded_providers`."""
    video = movies['man_of_steel']
    languages = {Language('eng')}

    pool = AsyncProviderPool(['opensubtitlescom'])
    await pool.initialize()

    # a broken mock provider raises a DiscardingError
    cast('MockProvider', await pool.get_provider('opensubtitlescom')).is_broken = True

    subtitles = await pool.list_subtitles(video, languages)
    assert subtitles == []

    assert pool.failed_providers == {'opensubtitlescom'}
    assert pool.discarded_providers == {'opensubtitlescom'}


@pytest.mark.asyncio
async def test_list_subtitles_unknown_error_reports_failed_only(movies: dict[str, Movie]) -> None:
    """An unknown error puts the provider in `failed_providers` only."""
    video = movies['man_of_steel']
    languages = {Language('eng')}

    pool = AsyncProviderPool(['opensubtitlescom'])
    await pool.initialize()

    with patch.object(await pool.get_provider('opensubtitlescom'), 'list_subtitles', side_effect=KeyError('id')):
        subtitles = await pool.list_subtitles(video, languages)
        assert subtitles == []

    assert pool.failed_providers == {'opensubtitlescom'}
    assert pool.discarded_providers == set()


@pytest.mark.asyncio
async def test_async_provider_pool_list_subtitles_discarded_providers(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}

    pool = AsyncProviderPool()
    await pool.initialize()

    # One provider is broken
    cast('MockProvider', await pool.get_provider('opensubtitlescom')).is_broken = True

    subtitles = await pool.list_subtitles(video, languages)
    assert {s.provider_name for s in subtitles} == {
        'gestdown',
        'podnapisi',
        'tvsubtitles',
    }
    assert 'opensubtitlescom' in pool.discarded_providers
    # a discarded provider is also a failed provider
    assert 'opensubtitlescom' in pool.failed_providers


@pytest.mark.asyncio
async def test_download_subtitles_discarded_provider(
    movies: dict[str, Movie],
    provider_manager: RegistrableExtensionManager,
) -> None:
    video = movies['man_of_steel']
    languages = {Language('eng')}

    pool = AsyncProviderPool(['opensubtitlescom'])
    await pool.initialize()

    # Working provider
    subtitles = await pool.list_subtitles(video, languages)
    assert len(subtitles) == 1
    # keep listed subtitle
    subtitle = subtitles[0]
    assert 'opensubtitlescom' not in pool.discarded_providers

    # Mock a broken provider
    cast('MockProvider', await pool.get_provider('opensubtitlescom')).is_broken = True
    # Try failing downloading subtitle
    assert not await pool.download_subtitle(subtitle)

    assert 'opensubtitlescom' in pool.discarded_providers
    # a discarded provider is also a failed provider
    assert 'opensubtitlescom' in pool.failed_providers


@pytest.mark.asyncio
async def test_download_subtitle_unknown_error_reports_failed_only(
    movies: dict[str, Movie],
    provider_manager: RegistrableExtensionManager,
) -> None:
    """An unknown error while downloading puts the provider in `failed_providers` only."""
    video = movies['man_of_steel']
    languages = {Language('eng')}

    pool = AsyncProviderPool(['opensubtitlescom'])
    await pool.initialize()

    subtitles = await pool.list_subtitles(video, languages)
    assert len(subtitles) > 0
    subtitle = subtitles[0]

    with patch.object(await pool.get_provider('opensubtitlescom'), 'download_subtitle', side_effect=KeyError('id')):
        assert not await pool.download_subtitle(subtitle)

    assert pool.failed_providers == {'opensubtitlescom'}
    assert pool.discarded_providers == set()


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


def test_download_best_subtitles_category(episodes: dict[str, Episode]) -> None:
    video = episodes['bbt_s07e05']
    languages = {Language('eng')}
    providers = ['gestdown', 'podnapisi', 'tvsubtitles']
    expected_subtitles = {
        ('tvsubtitles', '23329'),
        # ('podnapisi', 'EdQo'),
        # ('gestdown', 'a295515c-a460-44ea-9ba8-8d37bcb9b5a6'),
    }

    subtitles = download_best_subtitles({video}, languages, subtitle_categories='hi,n,fo', providers=providers)

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


@pytest.mark.asyncio
async def test_download_bad_subtitle(movies: dict[str, Movie]) -> None:
    pool = AsyncProviderPool()
    await pool.initialize()

    provider_result = await pool.list_subtitles_provider('opensubtitlescom', movies['man_of_steel'], {Language('tur')})
    assert provider_result.ok()
    assert len(provider_result.subtitles) >= 1
    subtitle = provider_result.subtitles[0]

    # The subtitle has no content
    await pool.download_subtitle(subtitle)

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


def test_save_subtitles(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    ensure(tmp_path / movies['man_of_steel'].name)
    subtitle_no_content = Subtitle(Language('eng'), '')
    subtitle = Subtitle(Language('fra'), '')
    subtitle.set_content(b'Some content')
    subtitle_other = Subtitle(Language('fra'), '')
    subtitle_other.set_content(b'Some other content')
    subtitle_pt_br = Subtitle(Language('por', 'BR'), '')
    subtitle_pt_br.set_content(b'Some brazilian content')
    subtitles = [subtitle_no_content, subtitle, subtitle_other, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles)

    # subtitle without content is skipped
    path = tmp_path / (os.path.splitext(movies['man_of_steel'].name)[0] + '.en.srt')
    assert not path.is_file()

    # first subtitle with language is saved
    path = tmp_path / (os.path.splitext(movies['man_of_steel'].name)[0] + '.fr.srt')
    assert path.is_file()
    assert path.open('rb').read() == b'Some content'

    # ietf language in path
    path = tmp_path / (os.path.splitext(movies['man_of_steel'].name)[0] + '.pt-BR.srt')
    assert path.is_file()
    assert path.open('rb').read() == b'Some brazilian content'


def test_save_subtitles_single_directory_encoding(movies: dict[str, Movie], tmp_path: Path) -> None:
    subtitle = Subtitle(Language('jpn'), '')
    subtitle.set_content('ハローワールド'.encode('shift-jis'))
    subtitle_pt_br = Subtitle(Language('por', 'BR'), '')
    subtitle_pt_br.set_content(b'Some brazilian content')
    subtitles = [subtitle, subtitle_pt_br]

    save_subtitles(movies['man_of_steel'], subtitles, single=True, directory=os.fspath(tmp_path), encoding='utf-8')

    # first subtitle only and correctly encoded
    path = tmp_path / (os.path.splitext(os.path.split(movies['man_of_steel'].name)[1])[0] + '.srt')
    assert path.is_file()
    assert path.open(encoding='utf-8').read() == 'ハローワールド'


def test_save_subtitles_convert(movies: dict[str, Movie], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = movies['man_of_steel']

    monkeypatch.chdir(tmp_path)
    ensure(tmp_path / video.name)

    text = dedent(
        """\
        [Script Info]
        WrapStyle: 0
        ScaledBorderAndShadow: yes
        Collisions: Normal
        ScriptType: v4.00+

        [V4+ Styles]
        Format: Name, Fontname, Fontsize, PrimaryColour
        Style: Default,Arial,20,&H00FFFFFF

        [Events]
        Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        Dialogue: 0,0:00:49.54,0:00:52.96,Default,,0,0,0,,Tłumaczenie:\\Nsinu6
        Dialogue: 0,0:02:11.08,0:02:12.88,Default,,0,0,0,,/Nie rozumiecie?
        """
    )
    subtitle = Subtitle(Language('pol'), '')
    subtitle.set_content(text.encode('utf-8'))
    subtitles = [subtitle]

    save_subtitles(video, subtitles, single=True, subtitle_format='srt')

    # converted to srt
    srt_text = dedent(
        """\
        1
        00:00:49,540 --> 00:00:52,960
        Tłumaczenie:
        sinu6

        2
        00:02:11,080 --> 00:02:12,880
        /Nie rozumiecie?

        """
    )
    path = tmp_path / (os.path.splitext(video.name)[0] + '.srt')
    assert path.is_file()
    assert path.open(encoding='utf-8').read() == srt_text


def test_is_async_provider() -> None:
    class SyncProvider(Provider):
        def list_subtitles(self, video: Video, languages: Set[Language]) -> list[Subtitle]:
            return []

    class MyAsyncProvider(AsyncProvider):  # type: ignore[type-arg]
        async def list_subtitles(self, video: Video, languages: Set[Language]) -> list[Subtitle]:
            return []

    assert not is_async_provider(SyncProvider())
    assert is_async_provider(MyAsyncProvider())


def test_is_async_refiner() -> None:
    class SyncRefiner(Refiner):
        def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
            return {}

    class MyAsyncRefiner(AsyncRefiner):
        async def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
            return {}

    assert not is_async_refiner(SyncRefiner())
    assert is_async_refiner(MyAsyncRefiner())


# ----------------------------------------------------------------------
# provider pool
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_pool_repr_and_accessors() -> None:
    provider_configs = {'podnapisi': {'foo': 'bar'}}
    async with AsyncProviderPool(['opensubtitlescom', 'podnapisi'], provider_configs) as pool:
        assert repr(pool) == "<AsyncProviderPool ['opensubtitlescom', 'podnapisi']>"
        assert pool.providers == ['opensubtitlescom', 'podnapisi']
        assert pool.provider_configs == provider_configs
        assert pool.initialized_providers == {}

        provider = await pool.get_provider('podnapisi')
        assert pool.initialized_providers == {'podnapisi': provider}


@pytest.mark.asyncio
async def test_list_subtitles_provider_cancelled(movies: dict[str, Movie]) -> None:
    """A cancellation is never swallowed."""
    async with AsyncProviderPool(['opensubtitlescom']) as pool:
        provider = await pool.get_provider('opensubtitlescom')
        with (
            patch.object(provider, 'list_subtitles', new=AsyncMock(side_effect=asyncio.CancelledError)),
            pytest.raises(asyncio.CancelledError),
        ):
            await pool.list_subtitles_provider('opensubtitlescom', movies['man_of_steel'], {Language('eng')})


@pytest.mark.asyncio
async def test_download_subtitle_cancelled(movies: dict[str, Movie]) -> None:
    """A cancellation is never swallowed."""
    async with AsyncProviderPool(['opensubtitlescom']) as pool:
        subtitles = await pool.list_subtitles(movies['man_of_steel'], {Language('eng')})
        assert len(subtitles) > 0

        provider = await pool.get_provider('opensubtitlescom')
        with (
            patch.object(provider, 'download_subtitle', new=AsyncMock(side_effect=asyncio.CancelledError)),
            pytest.raises(asyncio.CancelledError),
        ):
            await pool.download_subtitle(subtitles[0])


@pytest.mark.asyncio
async def test_download_subtitle_bad_archive(movies: dict[str, Movie], caplog: pytest.LogCaptureFixture) -> None:
    """A bad archive invalidates the subtitle, but the provider is kept."""
    async with AsyncProviderPool(['opensubtitlescom']) as pool:
        subtitles = await pool.list_subtitles(movies['man_of_steel'], {Language('eng')})
        assert len(subtitles) > 0

        provider = await pool.get_provider('opensubtitlescom')
        with (
            caplog.at_level(logging.ERROR, logger='subliminal.provider_pool'),
            patch.object(provider, 'download_subtitle', side_effect=zipfile.BadZipFile),
        ):
            assert not await pool.download_subtitle(subtitles[0])

    assert 'Bad archive for subtitle' in caplog.text
    assert pool.failed_providers == {'opensubtitlescom'}
    assert pool.discarded_providers == set()


@pytest.mark.asyncio
async def test_download_best_subtitles_skip_downloaded_language(movies: dict[str, Movie]) -> None:
    """Only the best subtitle of each language is downloaded."""
    video = movies['man_of_steel']
    eng_best = Subtitle(Language('eng'), 'eng-best')
    eng_other = Subtitle(Language('eng'), 'eng-other')
    fra = Subtitle(Language('fra'), 'fra')
    scores = {'eng-best': 30, 'eng-other': 20, 'fra': 10}

    pool = AsyncProviderPool(['opensubtitlescom'])
    download = AsyncMock(return_value=True)
    with patch.object(pool, 'download_subtitle', new=download):
        downloaded = await pool.download_best_subtitles(
            [eng_other, fra, eng_best],
            video,
            {Language('eng'), Language('fra')},
            compute_score=lambda subtitle, video: scores[subtitle.id],
        )

    assert downloaded == [eng_best, fra]
    # the second english subtitle is skipped without being downloaded
    assert download.await_args_list == [call(eng_best), call(fra)]


# ----------------------------------------------------------------------
# refiner pool
# ----------------------------------------------------------------------


class ConstantRefiner(Refiner):
    """Synchronous refiner that returns a fixed update."""

    update: ClassVar[dict[str, Any]] = {}

    def __init__(self, **kwargs: Any) -> None:
        self.configs = kwargs

    def initialize(self) -> None:
        """Initialize the refiner."""

    def terminate(self) -> None:
        """Terminate the refiner."""

    def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
        """Return the fixed update."""
        return dict(self.update)


class GoodRefiner(ConstantRefiner):
    """Refiner that works."""

    update: ClassVar[dict[str, Any]] = {'resolution': 'test-resolution'}


class EpisodeRefiner(ConstantRefiner):
    """Refiner that only supports episodes."""

    video_types = (Episode,)


class BrokenRefiner(ConstantRefiner):
    """Refiner with an error that makes it unusable."""

    def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
        """Raise a discarding error."""
        msg = 'Broken refiner'
        raise DiscardingError(msg)


class AsyncConstantRefiner(AsyncRefiner):
    """Asynchronous refiner base class."""

    def __init__(self, **kwargs: Any) -> None:
        self.configs = kwargs

    async def initialize(self) -> None:
        """Initialize the refiner."""

    async def terminate(self) -> None:
        """Terminate the refiner."""


class SlowRefiner(AsyncConstantRefiner):
    """Refiner that takes too long."""

    async def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
        """Wait for much longer than the timeout used in the tests."""
        await asyncio.sleep(30)
        return {}


class CancelledRefiner(AsyncConstantRefiner):
    """Refiner that is cancelled."""

    async def refine(self, video: Video, **kwargs: Any) -> dict[str, Any]:
        """Raise a cancellation."""
        raise asyncio.CancelledError


@pytest.fixture
def refiner_plugins(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Make the refiner plugins added to the returned dict available to :class:`AsyncRefinerPool`."""
    plugins: dict[str, Any] = {}

    class FakeRefinerManager:
        def __getitem__(self, name: str) -> SimpleNamespace:
            return SimpleNamespace(plugin=plugins[name])

    manager = FakeRefinerManager()
    monkeypatch.setattr(AsyncRefinerPool, '_get_provider_manager', staticmethod(lambda: manager))
    return plugins


@pytest.mark.asyncio
async def test_refiner_pool_accessors(refiner_plugins: dict[str, Any]) -> None:
    refiner_plugins['good'] = GoodRefiner
    refiner_configs = {'good': {'foo': 'bar'}}

    async with AsyncRefinerPool(['good'], refiner_configs) as pool:
        assert pool.refiners == ['good']
        assert pool.refiner_configs == refiner_configs
        assert pool.initialized_refiners == {}

        refiner = await pool.get_provider('good')
        assert pool.initialized_refiners == {'good': refiner}
        assert cast('GoodRefiner', refiner).configs == {'foo': 'bar'}


@pytest.mark.asyncio
async def test_refine_provider_unsupported_video(
    movies: dict[str, Movie],
    episodes: dict[str, Episode],
    refiner_plugins: dict[str, Any],
) -> None:
    refiner_plugins['episode'] = EpisodeRefiner

    async with AsyncRefinerPool(['episode']) as pool:
        result = await pool.refine_provider('episode', movies['man_of_steel'])
        assert result.status == ResultStatus.UNSUPPORTED_VIDEO
        assert result.unsupported()

        result = await pool.refine_provider('episode', episodes['bbt_s07e05'])
        assert result.ok()


@pytest.mark.asyncio
async def test_refine_provider_cancelled(movies: dict[str, Movie], refiner_plugins: dict[str, Any]) -> None:
    """A cancellation is never swallowed, and does not count as a refiner error."""
    refiner_plugins['cancelled'] = CancelledRefiner

    async with AsyncRefinerPool(['cancelled']) as pool:
        with pytest.raises(asyncio.CancelledError):
            await pool.refine_provider('cancelled', movies['man_of_steel'])

    assert pool.failed_refiners == set()
    assert pool.discarded_refiners == set()


@pytest.mark.asyncio
@pytest.mark.parametrize('refiner_class', [BrokenRefiner, SlowRefiner], ids=['discarding-error', 'timeout'])
async def test_refine_provider_outage(
    movies: dict[str, Movie],
    refiner_plugins: dict[str, Any],
    refiner_class: type[Refiner | AsyncRefiner],
) -> None:
    refiner_plugins['refiner'] = refiner_class

    async with AsyncRefinerPool(['refiner'], timeout=0.05) as pool:
        result = await pool.refine_provider('refiner', movies['man_of_steel'])

    assert result.status == ResultStatus.OUTAGE
    assert result.outage()


@pytest.mark.asyncio
async def test_refine_by_stage_no_refiners(movies: dict[str, Movie], refiner_plugins: dict[str, Any]) -> None:
    """Without refiners, the video is only checked."""
    languages = {Language('eng')}
    video = movies['man_of_steel']

    async with AsyncRefinerPool([], check_kwargs={'languages': languages}) as pool:
        assert await pool.refine_by_stage(5, [], video)

        # the video already has a subtitle for each language, it does not pass the check
        video.subtitles = [Subtitle(lang) for lang in languages]
        assert not await pool.refine_by_stage(5, [], video)


@pytest.mark.asyncio
async def test_refine_discards_broken_refiner(
    movies: dict[str, Movie],
    refiner_plugins: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    refiner_plugins.update({'good': GoodRefiner, 'broken': BrokenRefiner})
    video = movies['man_of_steel']

    async with AsyncRefinerPool(['good', 'broken']) as pool:
        # the broken refiner is discarded, the video is still refined by the others
        assert await pool.refine(video) is video
        assert video.resolution == 'test-resolution'
        # a discarded refiner is also a failed refiner
        assert pool.failed_refiners == {'broken'}
        assert pool.discarded_refiners == {'broken'}

        # the discarded refiner is skipped, the others are still used
        video.resolution = None
        with caplog.at_level(logging.DEBUG, logger='subliminal.provider_pool'):
            assert await pool.refine(video) is video
        assert video.resolution == 'test-resolution'
        assert "Skipping discarded refiners 'broken'" in caplog.text
        assert pool.discarded_refiners == {'broken'}


@pytest.mark.asyncio
async def test_refine_all_refiners_discarded(movies: dict[str, Movie], refiner_plugins: dict[str, Any]) -> None:
    refiner_plugins['broken'] = BrokenRefiner
    video = movies['man_of_steel']

    async with AsyncRefinerPool(['broken']) as pool:
        assert await pool.refine(video) is video
        assert pool.discarded_refiners == {'broken'}

        # no refiner left, the video is passed along untouched
        assert await pool.refine(video) is video
        assert pool.discarded_refiners == {'broken'}
