"""Subliminal uses `click <https://click.palletsprojects.com>`_ to provide a :abbr:`CLI (command-line interface)`."""

from __future__ import annotations

import logging

import click
import tomlkit
from click_option_group import GroupedOption

from .cli import subliminal

logger = logging.getLogger(__name__)


def generate_default_config(*, compact: bool = True, commented: bool = True) -> str:
    """Generate a default configuration file.

    :param compact: if True, generate a compact configuration without newlines between options.
    :param commented: if True, all the options are commented out.
    :return: the default configuration as a string.
    """

    def add_value_to_table(opt: click.Option, table: tomlkit.items.Table, *, name: str | None = None) -> str | None:
        """Add a value to a TOML table."""
        if opt.name is None:  # pragma: no cover
            return None
        # Override option name
        opt_name = name if name is not None else opt.name

        table.add(tomlkit.comment((opt.help or opt_name).capitalize()))
        # table.add(tomlkit.comment(f'{opt_name} = {opt.default}'))
        if opt.default is not None:
            if not commented:
                table.add(opt_name, opt.default)
            else:
                # Generate the entry in a dumb table
                dumb = tomlkit.table()
                dumb.add(opt_name, opt.default)
                # Add the string to the final table as a comment
                table.add(tomlkit.comment(dumb.as_string().strip('\n')))
        else:
            table.add(tomlkit.comment(f'{opt_name} = '))

        # Return the key to keep track of duplicates
        return opt_name

    # Create TOML document
    doc = tomlkit.document()
    doc.add(tomlkit.comment('Subliminal default configuration file'))
    doc.add(tomlkit.nl())

    # Get the options to the main command line
    default = tomlkit.table()
    for opt in subliminal.params:
        if not isinstance(opt, click.Option) or isinstance(opt, GroupedOption):
            continue
        if opt.name is None:  # pragma: no cover
            continue
        if opt.name.startswith(('__', 'fake')):
            continue
        if opt.name in ['version', 'config']:
            continue
        # Add key=value to table
        add_value_to_table(opt, default)
        if not compact:  # pragma: no cover
            default.add(tomlkit.nl())
    # Adding the table to the document
    doc.add('default', default)
    if not compact:  # pragma: no cover
        doc.add(tomlkit.nl())

    # Get subcommands
    for command_name, command in subliminal.commands.items():
        # Get the options for each subcommand
        com_table = tomlkit.table()
        # We need to keep track of duplicated options
        existing_options: set[str] = set()
        for opt in command.params:
            if opt.name is None:  # pragma: no cover
                continue
            if not isinstance(opt, click.Option):
                continue
            if opt.name in existing_options:
                # Duplicated option
                continue
            # Add key=value to table
            opt_name = add_value_to_table(opt, com_table)
            if opt_name is not None:
                existing_options.add(opt_name)
            if not compact:  # pragma: no cover
                com_table.add(tomlkit.nl())

        # Adding the table to the document
        doc.add(command_name, com_table)
        if not compact:  # pragma: no cover
            doc.add(tomlkit.nl())

    # Add providers and refiners options
    for class_type in ['provider', 'refiner']:
        provider_options = [
            o
            for o in subliminal.params
            if isinstance(o, click.Option) and o.name and o.name.startswith(f'_{class_type}__')
        ]
        provider_tables: dict[str, tomlkit.items.Table] = {}
        for opt in provider_options:
            if opt.name is None:  # pragma: no cover
                continue
            _, provider, opt_name = opt.name.split('__')
            provider_table = provider_tables.setdefault(provider, tomlkit.table())
            if opt.name in provider_table:  # pragma: no cover
                # Duplicated option
                continue

            # Add key=value to table
            add_value_to_table(opt, provider_table, name=opt_name)
            if not compact:  # pragma: no cover
                provider_table.add(tomlkit.nl())

        # Adding the table to the document
        parent_provider_table = tomlkit.table()
        for provider, table in provider_tables.items():
            parent_provider_table.add(provider, table)
            if not compact:  # pragma: no cover
                doc.add(tomlkit.nl())
        doc.add(class_type, parent_provider_table)
        if not compact:  # pragma: no cover
            doc.add(tomlkit.nl())

    return str(tomlkit.dumps(doc))
