"""Language converter for Subtitulamos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babelfish import LanguageReverseConverter, language_converters

if TYPE_CHECKING:
    from . import LanguageTuple


class SubtitulamosConverter(LanguageReverseConverter):
    """Language converter for Subtitulamos."""

    def __init__(self) -> None:
        self.name_converter = language_converters['name']
        self.from_subtitulamos: dict[str, LanguageTuple] = {
            'Español': ('spa',),
            'Español (España)': ('spa',),
            'Español (Latinoamérica)': ('spa', 'MX'),
            'Català': ('cat',),
            'English': ('eng',),
            'Galego': ('glg',),
            'Portuguese': ('por',),
            'English (US)': ('eng', 'US'),
            'English (UK)': ('eng', 'GB'),
            'Brazilian': ('por', 'BR'),
        }
        self.to_subtitulamos: dict[LanguageTuple, str] = {
            ('cat',): 'Català',
            ('glg',): 'Galego',
            ('por', 'BR'): 'Brazilian',
        }
        self.codes = set(self.from_subtitulamos.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3, country) in self.to_subtitulamos:
            return self.to_subtitulamos[(alpha3, country)]
        if (alpha3,) in self.to_subtitulamos:
            return self.to_subtitulamos[(alpha3,)]

        return self.name_converter.convert(alpha3, country, script)

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_subtitulamos:
            return self.from_subtitulamos[code]

        return self.name_converter.reverse(code)
