from importlib.metadata import entry_points

from subliminal.extensions import (
    RegistrableExtensionManager,
    provider_manager,
    default_providers,
    disabled_providers,
    parse_entry_point,
)


def test_registrable_extension_manager_all_extensions():
    native_extensions = sorted(e.name for e in provider_manager)

    manager = RegistrableExtensionManager('subliminal.providers', [
        'esopensubtitl = subliminal.providers.opensubtitles:OpenSubtitlesProvider'
    ])
    extensions = sorted(e.name for e in manager)
    assert len(extensions) == len(native_extensions) + 1
    assert extensions == sorted(name for name in ('esopensubtitl', *native_extensions))


def test_registrable_extension_manager_internal_extension():
    manager = RegistrableExtensionManager('subliminal.test_providers', [
        'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
        'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
        'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
        'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
        'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
    ])
    assert len(list(manager)) == 5
    assert len(manager.internal_extensions) == 5


def test_registrable_extension_manager_register():
    manager = RegistrableExtensionManager('subliminal.test_providers', [
        'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
        'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider'
    ])
    assert len(list(manager)) == 2
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert len(list(manager)) == 3
    assert 'de7cidda' in manager.names()


def test_registrable_extension_manager_unregister():
    manager = RegistrableExtensionManager('subliminal.test_providers', [
        'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
        'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
    ])
    assert len(list(manager)) == 2
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    manager.unregister('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert len(list(manager)) == 2
    assert set(manager.names()) == {'thesubdb', 'tvsubtitles'}


def test_provider_manager():
    setup_names = {ep.name for ep in entry_points() if ep.group == provider_manager.namespace}
    internal_names = {parse_entry_point(iep, provider_manager.namespace).name for iep in provider_manager.internal_extensions}
    enabled_names = set(default_providers)
    disabled_names = set(disabled_providers)
    assert enabled_names == setup_names - disabled_names
    assert internal_names == enabled_names | disabled_names
