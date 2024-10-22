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
            'Català': ('cat', None, None),
            'Chinese (Simplified)': ('zho', None, None),
            'Chinese (Traditional)': ('zho', None, None),
            'Euskera': ('eus', None, None),
            'French (Canadian)': ('fra', 'CA', None),
            'Galego': ('glg', None, None),
            'Greek': ('ell', None, None),
            'Malay': ('msa', None, None),
            'Portuguese (Brazilian)': ('por', 'BR', None),
            'Serbian (Cyrillic)': ('srp', None, 'Cyrl'),
            'Serbian (Latin)': ('srp', None, None),
            'Spanish (Latin America)': ('spa', None, None),
            'Spanish (Spain)': ('spa', None, None),
        }
        self.to_addic7ed: dict[LanguageTuple, str] = {
            ('cat', None, None): 'Català',
            ('zho', None, None): 'Chinese (Simplified)',
            ('eus', None, None): 'Euskera',
            ('fra', 'CA', None): 'French (Canadian)',
            ('glg', None, None): 'Galego',
            ('ell', None, None): 'Greek',
            ('msa', None, None): 'Malay',
            ('por', 'BR', None): 'Portuguese (Brazilian)',
            ('srp', None, 'Cyrl'): 'Serbian (Cyrillic)',
        }
        self.codes = self.name_converter.codes | set(self.from_addic7ed.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3, country, script) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country, script)]
        if (alpha3, country, None) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country, None)]
        if (alpha3, None, None) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, None, None)]

        return self.name_converter.convert(alpha3, country, script)  # type: ignore[no-any-return]

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_addic7ed:
            ret = self.from_addic7ed[code]
            if len(ret) == 1:
                return (*ret, None, None)
            if len(ret) == 2:
                return (*ret, None)
            # if len(ret) == 3:
            return ret

        return self.name_converter.reverse(code)  # type: ignore[no-any-return]
