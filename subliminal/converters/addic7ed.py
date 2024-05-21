"""Language converter for Addic7ed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babelfish import LanguageReverseConverter, language_converters  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from . import LanguageTuple


class Addic7edConverter(LanguageReverseConverter):
    """Language converter for Addic7ed."""

    def __init__(self) -> None:
        self.name_converter = language_converters['name']
        self.from_addic7ed: dict[str, LanguageTuple] = {
            'Català': ('cat',),
            'Chinese (Simplified)': ('zho',),
            'Chinese (Traditional)': ('zho',),
            'Euskera': ('eus',),
            'Galego': ('glg',),
            'Greek': ('ell',),
            'Malay': ('msa',),
            'Portuguese (Brazilian)': ('por', 'BR'),
            'Serbian (Cyrillic)': ('srp', None, 'Cyrl'),
            'Serbian (Latin)': ('srp',),
            'Spanish (Latin America)': ('spa',),
            'Spanish (Spain)': ('spa',),
        }
        self.to_addic7ed: dict[LanguageTuple, str] = {
            ('cat',): 'Català',
            ('zho',): 'Chinese (Simplified)',
            ('eus',): 'Euskera',
            ('glg',): 'Galego',
            ('ell',): 'Greek',
            ('msa',): 'Malay',
            ('por', 'BR'): 'Portuguese (Brazilian)',
            ('srp', None, 'Cyrl'): 'Serbian (Cyrillic)',
        }
        self.codes = self.name_converter.codes | set(self.from_addic7ed.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3, country, script) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country, script)]
        if (alpha3, country) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country)]
        if (alpha3,) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3,)]

        return self.name_converter.convert(alpha3, country, script)  # type: ignore[no-any-return]

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_addic7ed:
            return self.from_addic7ed[code]

        return self.name_converter.reverse(code)  # type: ignore[no-any-return]
