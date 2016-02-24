# -*- coding: utf-8 -*-
from pkg_resources import EntryPoint, iter_entry_points

from subliminal.extensions import RegistrableExtensionManager


def test_registrable_extension_manager_all_extensions():
    manager = RegistrableExtensionManager('subliminal.providers', [
        'de7cidda = subliminal.providers.addic7ed:Addic7edProvider'
    ])
    extensions = sorted(e.name for e in manager)
    assert len(extensions) == 7
    assert extensions == ['addic7ed', 'de7cidda', 'opensubtitles', 'podnapisi', 'subscenter', 'thesubdb', 'tvsubtitles']


def test_registrable_extension_manager_internal_extension():
    manager = RegistrableExtensionManager('subliminal.providers', [
        'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
        'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
        'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
        'subscenter = subliminal.providers.subscenter:SubsCenterProvider',
        'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
        'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
    ])
    assert len(list(manager)) == 6
    setup_names = {ep.name for ep in iter_entry_points(manager.namespace)}
    internal_names = {EntryPoint.parse(iep).name for iep in manager.internal_extensions}
    assert internal_names == setup_names


def test_registrable_extension_manager_register():
    manager = RegistrableExtensionManager('subliminal.providers', [
        'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
        'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
        'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
        'subscenter = subliminal.providers.subscenter:SubsCenterProvider',
        'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
        'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
    ])
    assert len(list(manager)) == 6
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert len(list(manager)) == 7
    assert 'de7cidda' in manager.names()


def test_registrable_extension_manager_unregister():
    manager = RegistrableExtensionManager('subliminal.providers', [
        'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
        'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
        'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
        'subscenter = subliminal.providers.subscenter:SubsCenterProvider',
        'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
        'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
    ])
    assert len(list(manager)) == 6
    old_names = manager.names()
    manager.register('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    manager.unregister('de7cidda = subliminal.providers.addic7ed:Addic7edProvider')
    assert len(list(manager)) == 6
    assert set(old_names) == set(manager.names())
