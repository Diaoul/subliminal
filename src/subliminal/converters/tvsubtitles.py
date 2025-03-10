"""Language converter for TVsubtitles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babelfish import LanguageReverseConverter, language_converters  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from . import LanguageTuple


class TVsubtitlesConverter(LanguageReverseConverter):
    """Language converter for TVsubtitles."""

    def __init__(self) -> None:
        self.alpha2_converter = language_converters['alpha2']
        self.from_tvsubtitles: dict[str, tuple[str, str | None]] = {
            'br': ('por', 'BR'),
            'ua': ('ukr', None),
            'gr': ('ell', None),
            'cn': ('zho', None),
            'jp': ('jpn', None),
            'cz': ('ces', None),
        }
        self.to_tvsubtitles: dict[tuple[str, str | None], str] = {v: k for k, v in self.from_tvsubtitles.items()}
        self.codes = self.alpha2_converter.codes | set(self.from_tvsubtitles.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3, country) in self.to_tvsubtitles:
            return self.to_tvsubtitles[(alpha3, country)]

        return self.alpha2_converter.convert(alpha3, country, script)  # type: ignore[no-any-return]

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_tvsubtitles:
            return (*self.from_tvsubtitles[code], None)

        return self.alpha2_converter.reverse(code)  # type: ignore[no-any-return]
