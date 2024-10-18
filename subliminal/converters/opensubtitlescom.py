"""Language converter for OpenSubtitlesCom."""

from __future__ import annotations

from typing import TYPE_CHECKING

from babelfish import LanguageReverseConverter, language_converters  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from . import LanguageTuple


class OpenSubtitlesComConverter(LanguageReverseConverter):
    """Language converter for OpenSubtitlesCom.

    From GET API at: https://api.opensubtitles.com/api/v1/infos/languages
    """

    def __init__(self) -> None:
        self.alpha2_converter = language_converters['alpha2']
        self.from_opensubtitlescom: dict[str, tuple[str, str | None]] = {
            'pt-br': ('por', 'BR'),
            'pt-pt': ('por', 'PT'),
            'zh-cn': ('zho', 'CN'),
            'zh-tw': ('zho', 'TW'),
            'ze': ('zho', 'US'),
            'me': ('srp', 'ME'),
            'sy': ('syr', None),
            'ma': ('mni', None),
            'at': ('ast', None),
        }
        self.to_opensubtitlescom: dict[tuple[str, str | None], str] = {
            v: k for k, v in self.from_opensubtitlescom.items()
        }
        self.codes = self.alpha2_converter.codes | set(self.from_opensubtitlescom.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        if (alpha3, country) in self.to_opensubtitlescom:
            return self.to_opensubtitlescom[(alpha3, country)]
        if (alpha3, None) in self.to_opensubtitlescom:
            return self.to_opensubtitlescom[(alpha3, None)]

        return self.alpha2_converter.convert(alpha3, country, script)  # type: ignore[no-any-return]

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        code_lower = code.lower()
        if code_lower in self.from_opensubtitlescom:
            return (*self.from_opensubtitlescom[code_lower], None)

        return self.alpha2_converter.reverse(code)  # type: ignore[no-any-return]
