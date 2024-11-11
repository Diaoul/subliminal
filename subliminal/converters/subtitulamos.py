"""Language converter for Subtitulamos."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babelfish import LanguageReverseConverter, language_converters  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from . import LanguageTuple


class SubtitulamosConverter(LanguageReverseConverter):
    """Language converter for Subtitulamos."""

    def __init__(self) -> None:
        self.name_converter = language_converters['name']
        self.from_subtitulamos: dict[str, tuple[str, str | None]] = {
            'Español': ('spa', None),
            'Español (España)': ('spa', None),
            'Español (Latinoamérica)': ('spa', 'MX'),
            'Català': ('cat', None),
            'English': ('eng', None),
            'Galego': ('glg', None),
            'Portuguese': ('por', None),
            'English (US)': ('eng', 'US'),
            'English (UK)': ('eng', 'GB'),
            'Brazilian': ('por', 'BR'),
        }
        self.to_subtitulamos: dict[tuple[str, str | None], str] = {
            item[1]: item[0] for item in self.from_subtitulamos.items()
        } | {
            ('spa', country): 'Español (Latinoamérica)'
            for country in [
                'AR',  # Argentina
                'BO',  # Bolivia
                'CL',  # Chile
                'CO',  # Colombia
                'CR',  # Costa Rica
                'DO',  # República Dominicana
                'EC',  # Ecuador
                'GT',  # Guatemala
                'HN',  # Honduras
                'NI',  # Nicaragua
                'PA',  # Panamá
                'PE',  # Perú
                'PR',  # Puerto Rico
                'PY',  # Paraguay
                'SV',  # El Salvador
                'US',  # United States
                'UY',  # Uruguay
                'VE',  # Venezuela
            ]
        }
        self.codes = set(self.from_subtitulamos.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3, country) in self.to_subtitulamos:
            return self.to_subtitulamos[(alpha3, country)]

        return self.name_converter.convert(alpha3, country, script)  # type: ignore[no-any-return]

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_subtitulamos:
            return (*self.from_subtitulamos[code], None)

        return self.name_converter.reverse(code)  # type: ignore[no-any-return]
