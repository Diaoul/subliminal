from __future__ import annotations

import os
from datetime import timedelta
from textwrap import dedent
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from babelfish import Language  # type: ignore[import-untyped]

from subliminal.provider_pool import (
    AsyncProviderPool,
    check_video,
    download_best_subtitles,
    download_subtitles,
    list_subtitles,
    refine,
    refiner_manager,
    save_subtitles,
)
from subliminal.score import episode_scores
from subliminal.subtitle import Subtitle
from tests.conftest import ensure

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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
        monkeypatch.setattr(provider.plugin, 'initialize', AsyncMock())
        monkeypatch.setattr(provider.plugin, 'list_subtitles', AsyncMock(return_value=[provider.name]))
        monkeypatch.setattr(provider.plugin, 'download_subtitle', AsyncMock())
        monkeypatch.setattr(provider.plugin, 'terminate', AsyncMock())


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
