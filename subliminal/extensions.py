"""Extension managers for the providers, refiners and language converters."""

from __future__ import annotations

import re
from importlib.metadata import EntryPoint
from typing import TYPE_CHECKING, Any

from stevedore import ExtensionManager  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from collections.abc import Sequence


class RegistrableExtensionManager(ExtensionManager):
    """:class:~stevedore.extensions.ExtensionManager` with support for registration.

    It allows loading of internal extensions without setup and registering/unregistering additional extensions.

    Loading is done in this order:

    * Entry point extensions
    * Internal extensions
    * Registered extensions

    :param str namespace: namespace argument for :class:~stevedore.extensions.ExtensionManager`.
    :param list internal_extensions: internal extensions to use with entry point syntax.
    :param kwargs: additional parameters for the :class:~stevedore.extensions.ExtensionManager` constructor.

    """

    registered_extensions: list[str]
    internal_extensions: list[str]

    def __init__(self, namespace: str, internal_extensions: Sequence[str], **kwargs: Any) -> None:
        #: Registered extensions with entry point syntax
        self.registered_extensions = []

        #: Internal extensions with entry point syntax
        self.internal_extensions = list(internal_extensions)

        super().__init__(namespace, **kwargs)

    def list_entry_points(self) -> list[EntryPoint]:
        """List the entry points."""
        # copy of default extensions
        eps = list(super().list_entry_points())

        # internal extensions
        for iep in self.internal_extensions:
            ep = parse_entry_point(iep, self.namespace)
            if ep.name not in [e.name for e in eps]:
                eps.append(ep)

        # registered extensions
        for rep in self.registered_extensions:
            ep = parse_entry_point(rep, self.namespace)
            if ep.name not in [e.name for e in eps]:
                eps.append(ep)

        return eps

    def register(self, entry_point: str) -> None:
        """Register an extension.

        :param str entry_point: extension to register (entry point syntax).
        :raises: ValueError if already registered.

        """
        if entry_point in self.registered_extensions:
            msg = 'Extension already registered'
            raise ValueError(msg)

        ep = parse_entry_point(entry_point, self.namespace)
        if ep.name in self.names():
            msg = 'An extension with the same name already exist'
            raise ValueError(msg)

        ext = self._load_one_plugin(
            ep,
            invoke_on_load=False,
            invoke_args=(),
            invoke_kwds={},
            verify_requirements=False,
        )
        self.extensions.append(ext)
        if self._extensions_by_name is not None:
            self._extensions_by_name[ext.name] = ext
        self.registered_extensions.insert(0, entry_point)

    def unregister(self, entry_point: str) -> None:
        """Unregister a provider.

        :param str entry_point: provider to unregister (entry point syntax).
        :raises: ValueError if already registered.

        """
        if entry_point not in self.registered_extensions:
            msg = 'Extension not registered'
            raise ValueError(msg)

        ep = parse_entry_point(entry_point, self.namespace)
        self.registered_extensions.remove(entry_point)
        if self._extensions_by_name is not None:
            del self._extensions_by_name[ep.name]
        for i, ext in enumerate(self.extensions):
            if ext.name == ep.name:
                del self.extensions[i]
                break


def parse_entry_point(src: str, group: str) -> EntryPoint:
    """Parse a string entry point."""
    pattern = re.compile(r'\s*(?P<name>.+?)\s*=\s*(?P<value>.+)')
    m = pattern.match(src)
    if not m:
        msg = "EntryPoint must be in the 'name = module:attrs' format"
        raise ValueError(msg, src)
    res = m.groupdict()
    return EntryPoint(res['name'], res['value'], group)


#: Provider manager
provider_manager = RegistrableExtensionManager(
    'subliminal.providers',
    [
        'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
        'gestdown = subliminal.providers.gestdown:GestdownProvider',
        'napiprojekt = subliminal.providers.napiprojekt:NapiProjektProvider',
        'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
        'opensubtitlescom = subliminal.providers.opensubtitlescom:OpenSubtitlesComProvider',
        'opensubtitlescomvip = subliminal.providers.opensubtitlescom:OpenSubtitlesComVipProvider',
        'opensubtitlesvip = subliminal.providers.opensubtitles:OpenSubtitlesVipProvider',
        'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
        'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider',
    ],
)

#: Disabled providers
disabled_providers = ['addic7ed', 'napiprojekt', 'opensubtitlesvip', 'opensubtitlescomvip']

#: Default enabled providers
default_providers = [p for p in provider_manager.names() if p not in disabled_providers]

#: Refiner manager
refiner_manager = RegistrableExtensionManager(
    'subliminal.refiners',
    [
        'hash = subliminal.refiners.hash:refine',
        'metadata = subliminal.refiners.metadata:refine',
        'omdb = subliminal.refiners.omdb:refine',
        'tvdb = subliminal.refiners.tvdb:refine',
        'tmdb = subliminal.refiners.tmdb:refine',
    ],
)
