from sys import version_info

if version_info >= (3, 10):
    # 'group' keyword argument was introduced in 3.10
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points  # type: ignore[assignment,no-redef,import-not-found]

import pytest

from subliminal.extensions import (
    EntryPoint,
    RegistrableExtensionManager,
    disabled_providers,
    disabled_refiners,
    get_default_providers,
    get_default_refiners,
    parse_entry_point,
    provider_manager,
    refiner_manager,
)

# Core test
pytestmark = pytest.mark.core


def test_parse_entry_point() -> None:
    src = 'addic7ed = subliminal.providers.addic7ed:Addic7edProvider'
    ep = parse_entry_point(src, group='subliminal.providers')
    assert isinstance(ep, EntryPoint)
    assert ep.name == 'addic7ed'
    assert ep.value == 'subliminal.providers.addic7ed:Addic7edProvider'
    assert ep.group == 'subliminal.providers'


def test_parse_entry_point_wrong() -> None:
    src = 'subliminal.providers.addic7ed:Addic7edProvider'
    with pytest.raises(ValueError, match='EntryPoint must be'):
        parse_entry_point(src, group='subliminal.providers')


def test_registrable_extension_manager_all_extensions() -> None:
    native_extensions = sorted(e.name for e in provider_manager)

    manager = RegistrableExtensionManager(
        'subliminal.providers', ['esopensubtitl = subliminal.providers.opensubtitles:OpenSubtitlesProvider']
    )
    extensions = sorted(e.name for e in manager)
    assert len(extensions) == len(native_extensions) + 1
    assert extensions == sorted(name for name in ('esopensubtitl', *native_extensions))


def test_registrable_extension_manager_internal_extension() -> None:
    manager = RegistrableExtensionManager(
        'subliminal.test_providers',
        [
            'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
            'bsplayer = subliminal.providers.bsplayer:BSPlayerProvider',
            'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
            'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
            'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider',
        ],
    )
    assert len(list(manager)) == 5
    assert len(manager.internal_extensions) == 5


def test_registrable_extension_manager_register() -> None:
    manager = RegistrableExtensionManager(
        'subliminal.test_providers',
        [
            'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
            'bsplayer = subliminal.providers.bsplayer:BSPlayerProvider',
            'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
        ],
    )
    assert len(list(manager)) == 3
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert len(list(manager)) == 4
    assert 'de7cidda' in manager.names()

    eps = manager.list_entry_points()
    ep_names = [ep.name for ep in eps]
    assert ep_names == ['addic7ed', 'bsplayer', 'opensubtitles', 'de7cidda']

    # Raise ValueError on same entry point
    with pytest.raises(ValueError, match='Extension already registered'):
        manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')

    # Raise ValueError on same entry point name
    with pytest.raises(ValueError, match='An extension with the same name already exist'):
        manager.register('de7cidda = subliminal.providers.opensubtitles:OpenSubtitlesProvider')


def test_registrable_extension_manager_unregister() -> None:
    manager = RegistrableExtensionManager(
        'subliminal.test_providers',
        [
            'gestdown = subliminal.providers.gestdown:GestdownProvider',
            'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider',
        ],
    )
    assert len(list(manager)) == 2
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    manager.unregister('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert len(list(manager)) == 2
    assert set(manager.names()) == {'gestdown', 'tvsubtitles'}

    # Raise ValueError on entry point not found
    with pytest.raises(ValueError, match='Extension not registered'):
        manager.unregister('seltitbusnepo = subliminal.providers.opensubtitles:OpenSubtitlesProvider')


def test_provider_manager() -> None:
    setup_names = {ep.name for ep in entry_points(group=provider_manager.namespace)}
    internal_names = {
        parse_entry_point(iep, provider_manager.namespace).name for iep in provider_manager.internal_extensions
    }
    enabled_names = set(get_default_providers())
    disabled_names = set(disabled_providers)
    assert enabled_names == setup_names - disabled_names
    assert internal_names == enabled_names | disabled_names


def test_refiner_manager() -> None:
    setup_names = {ep.name for ep in entry_points(group=refiner_manager.namespace)}
    internal_names = {
        parse_entry_point(iep, refiner_manager.namespace).name for iep in refiner_manager.internal_extensions
    }
    enabled_names = set(get_default_refiners())
    disabled_names = set(disabled_refiners)
    assert enabled_names == setup_names - disabled_names
    assert internal_names == enabled_names | disabled_names
