"""Language converter for TheSubDB."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babelfish import LanguageReverseConverter  # type: ignore[import-untyped]

from subliminal.exceptions import ConfigurationError

if TYPE_CHECKING:
    from . import LanguageTuple


class TheSubDBConverter(LanguageReverseConverter):
    """Language converter for TheSubDB."""

    def __init__(self) -> None:
        self.from_thesubdb: dict[str, LanguageTuple] = {
            'en': ('eng',),
            'es': ('spa',),
            'fr': ('fra',),
            'it': ('ita',),
            'nl': ('nld',),
            'pl': ('pol',),
            'pt': ('por', 'BR'),
            'ro': ('ron',),
            'sv': ('swe',),
            'tr': ('tur',),
        }
        self.to_thesubdb: dict[LanguageTuple, str] = {v: k for k, v in self.from_thesubdb.items()}
        self.codes = set(self.from_thesubdb.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3, country) in self.to_thesubdb:
            return self.to_thesubdb[(alpha3, country)]
        if (alpha3,) in self.to_thesubdb:
            return self.to_thesubdb[(alpha3,)]

        msg = f'Unsupported language code for shooter: {(alpha3, country, script)}'
        raise ConfigurationError(msg)

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_thesubdb:
            return self.from_thesubdb[code]

        msg = f'Unsupported language code for thesubdb: {code}'
        raise ConfigurationError(msg)
