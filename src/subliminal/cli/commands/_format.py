"""Helper functions."""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

import click
from babelfish import Error as BabelfishError  # type: ignore[import-untyped]
from babelfish import Language

logger = logging.getLogger(__name__)


class LanguageParamType(click.ParamType):
    """:class:`~click.ParamType` for languages that returns a :class:`~babelfish.language.Language`."""

    name = 'language'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> Language:
        """Convert ietf language to :class:`~babelfish.language.Language`."""
        try:
            return Language.fromietf(value)
        except BabelfishError:
            self.fail(f'{value} is not a valid language', param, ctx)  # pragma: no cover


class AgeParamType(click.ParamType):
    """:class:`~click.ParamType` for age strings that returns a :class:`~datetime.timedelta`.

    An age string is in the form `number + identifier` with possible identifiers:

        * ``w`` for weeks
        * ``d`` for days
        * ``h`` for hours

    The form can be specified multiple times but only with that identifier ordering. For example:

        * ``1w2d4h`` for 1 week, 2 days and 4 hours
        * ``2w`` for 2 weeks
        * ``3w6h`` for 3 weeks and 6 hours
    """

    name = 'age'

    def convert(self, value: str, param: click.Parameter | None, ctx: click.Context | None) -> timedelta:
        """Convert an age string to :class:`~datetime.timedelta`."""
        match = re.match(r'^(?:(?P<weeks>\d+?)w)?(?:(?P<days>\d+?)d)?(?:(?P<hours>\d+?)h)?$', value)
        if not match:
            self.fail(f'{value} is not a valid age', param, ctx)

        return timedelta(**{k: int(v) for k, v in match.groupdict(0).items()})


def plural(quantity: int, name: str, *, bold: bool = True, **kwargs: Any) -> str:
    """Format a quantity with plural."""
    return '{} {}{}'.format(
        click.style(str(quantity), bold=bold, **kwargs),
        name,
        's' if quantity > 1 else '',
    )
