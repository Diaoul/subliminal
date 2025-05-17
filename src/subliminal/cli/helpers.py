# ruff: noqa: FBT001
"""CLI helper functions."""

from __future__ import annotations

import logging
import os
import pathlib
import traceback
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

import click
import tomlkit
from click_option_group import OptionGroup
from dogpile.cache.backends.file import AbstractFileLock
from dogpile.util.readwrite_lock import ReadWriteMutex

from subliminal import (
    provider_manager,
    refiner_manager,
)
from subliminal.utils import get_parameters_from_signature

if TYPE_CHECKING:
    from collections.abc import Callable, MutableMapping, Sequence

    from subliminal.utils import Parameter


logger = logging.getLogger(__name__)


class MutexLock(AbstractFileLock):  # pragma: no cover
    """:class:`MutexLock` is a thread-based rw lock based on :class:`dogpile.core.ReadWriteMutex`."""

    def __init__(self, filename: str) -> None:
        self.mutex = ReadWriteMutex()  # type: ignore[no-untyped-call]

    def acquire_read_lock(self, wait: bool) -> bool:
        """Acquire a reader lock."""
        ret = self.mutex.acquire_read_lock(wait)  # type: ignore[no-untyped-call]
        return wait or bool(ret)

    def acquire_write_lock(self, wait: bool) -> bool:
        """Acquire a writer lock."""
        ret = self.mutex.acquire_write_lock(wait)  # type: ignore[no-untyped-call]
        return wait or bool(ret)

    def release_read_lock(self) -> None:
        """Release a reader lock."""
        return self.mutex.release_read_lock()  # type: ignore[no-untyped-call,no-any-return]

    def release_write_lock(self) -> None:
        """Release a writer lock."""
        return self.mutex.release_write_lock()  # type: ignore[no-untyped-call,no-any-return]


PROVIDERS_OPTIONS_TEMPLATE = '_{ext}__{plugin}__{key}'
PROVIDERS_OPTIONS_CLI_TEMPLATE = '--{ext}.{plugin}.{key}'
PROVIDERS_OPTIONS_ENVVAR_TEMPLATE = 'SUBLIMINAL_{ext}_{plugin}_{key}'


def read_configuration(filename: str | os.PathLike) -> dict[str, dict[str, Any]]:
    """Read a configuration file."""
    filename = pathlib.Path(filename).expanduser()
    msg = ''
    toml_dict: MutableMapping[str, Any] = {}
    if filename.is_file():
        try:
            with open(filename, 'rb') as f:
                toml_dict = tomlkit.load(f)
        except tomlkit.exceptions.TOMLKitError:
            tb = traceback.format_exc()
            msg = f'Cannot read the configuration file at {os.fspath(filename)!r}:\n{tb}'
        else:
            msg = f'Using configuration file at {os.fspath(filename)!r}'
    else:
        msg = f'Not using any configuration file, not a file {os.fspath(filename)!r}'

    # make options for subliminal from [default] section
    options = toml_dict.setdefault('default', {})

    # make cache options
    options['cache'] = toml_dict.setdefault('cache', {})

    # make download options
    download_dict = toml_dict.setdefault('download', {})
    # handle language types
    for lt in ('hearing_impaired', 'foreign_only'):
        # if an option was defined in the config file, make it a tuple, the expected type
        if lt in download_dict and (isinstance(download_dict[lt], bool) or download_dict[lt] is None):
            download_dict[lt] = (download_dict[lt],)

    # remove the provider and refiner lists to select, extend and ignore
    provider_lists = {
        'select': download_dict.pop('provider', []),
        'extend': download_dict.pop('extend_provider', []),
        'ignore': download_dict.pop('ignore_provider', []),
    }
    refiner_lists = {
        'select': download_dict.pop('refiner', []),
        'extend': download_dict.pop('extend_refiner', []),
        'ignore': download_dict.pop('ignore_refiner', []),
    }
    options['download'] = download_dict

    # make provider and refiner options
    for ext in ('provider', 'refiner'):
        for plugin, d in toml_dict.setdefault(ext, {}).items():
            if not isinstance(d, Mapping):  # pragma: no cover
                continue
            for k, v in d.items():
                name = PROVIDERS_OPTIONS_TEMPLATE.format(ext=ext, plugin=plugin, key=k)
                options[name] = v

    return {
        'obj': {
            'debug_message': msg,
            'provider_lists': provider_lists,
            'refiner_lists': refiner_lists,
        },
        'default_map': options,
    }


providers_config = OptionGroup('Providers configuration')
refiners_config = OptionGroup('Refiners configuration')


def options_from_managers(
    group_name: str,
    options: Mapping[str, Sequence[Parameter]],
    group: OptionGroup | None = None,
) -> Callable[[Callable], Callable]:
    """Add click options dynamically from providers and refiners keyword arguments."""
    click_option = click.option if group is None else group.option

    def decorator(f: Callable) -> Callable:
        for plugin_name, opt_params in options.items():
            for opt in reversed(opt_params):
                name = opt['name']
                # CLI option has dots, variable has double-underscores to differentiate
                # with simple underscore in provider name or keyword argument.
                param_decls = (
                    PROVIDERS_OPTIONS_CLI_TEMPLATE.format(ext=group_name, plugin=plugin_name, key=name),
                    PROVIDERS_OPTIONS_TEMPLATE.format(ext=group_name, plugin=plugin_name, key=name),
                )
                # Setting the default value also decides on the type
                attrs = {
                    'default': opt['default'],
                    'help': opt['desc'],
                    'show_default': True,
                    'show_envvar': True,
                    'envvar': PROVIDERS_OPTIONS_ENVVAR_TEMPLATE.format(
                        ext=group_name.upper(),
                        plugin=plugin_name.upper(),
                        key=name.upper(),
                    ),
                }
                f = click_option(*param_decls, **attrs)(f)  # type: ignore[operator]
        return f

    return decorator


# Options from providers
provider_options = {
    name: get_parameters_from_signature(provider_manager[name].plugin) for name in provider_manager.names()
}

refiner_options = {
    name: [
        opt
        for opt in get_parameters_from_signature(refiner_manager[name].plugin)
        if opt['name'] not in ('video', 'kwargs', 'embedded_subtitles', 'providers', 'languages')
    ]
    for name in refiner_manager.names()
}

# Decorator to add click options from providers
options_from_providers = options_from_managers('provider', provider_options, group=providers_config)

# Decorator to add click options from refiners
options_from_refiners = options_from_managers('refiner', refiner_options, group=refiners_config)
