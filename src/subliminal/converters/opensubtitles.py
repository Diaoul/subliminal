# Copyright (c) 2013 the BabelFish authors. All rights reserved.
# Use of this source code is governed by the 3-clause BSD license
# that can be found in the LICENSE file.
#
"""Language converter for OpenSubtitles."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from babelfish import (  # type: ignore[import-untyped]
    LanguageReverseConverter,
    LanguageReverseError,
    language_converters,
)
from babelfish.converters import CaseInsensitiveDict  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from . import LanguageTuple


class OpenSubtitlesConverter(LanguageReverseConverter):
    """Language converter for OpenSubtitlesCom.

    Originally defined in :mod:`babelfish`.
    """

    codes: set[str]
    to_opensubtitles: dict[LanguageTuple, str]
    # from_opensubtitles: CaseInsensitiveDict[tuple[str, str | None]]
    from_opensubtitles: CaseInsensitiveDict

    def __init__(self) -> None:
        self.alpha3b_converter = language_converters['alpha3b']
        self.alpha2_converter = language_converters['alpha2']
        self.to_opensubtitles = {
            ('por', 'BR', None): 'pob',
            ('gre', None, None): 'ell',
            ('srp', None, None): 'scc',
            ('srp', 'ME', None): 'mne',
            ('srp', None, 'Latn'): 'scc',
            ('srp', None, 'Cyrl'): 'scc',
            ('spa', 'MX', None): 'spl',
            ('chi', None, 'Hant'): 'zht',
            ('chi', 'TW', None): 'zht',
        }
        self.from_opensubtitles = CaseInsensitiveDict(
            {
                'pob': ('por', 'BR', None),
                'pb': ('por', 'BR', None),
                'ell': ('ell', None, None),
                'scc': ('srp', None, None),
                'mne': ('srp', 'ME', None),
                'spl': ('spa', 'MX'),
                'zht': ('zho', None, 'Hant'),
            },
        )
        self.codes = self.alpha2_converter.codes | self.alpha3b_converter.codes | set(self.from_opensubtitles.keys())

    def convert(self, alpha3: str, country: str | None = None, script: str | None = None) -> str:
        """Convert an alpha3 language code with an alpha2 country code and a script code into a custom code."""
        alpha3b = self.alpha3b_converter.convert(alpha3, country, script)  # type: ignore[no-any-return]
        if (alpha3b, country, script) in self.to_opensubtitles:
            return self.to_opensubtitles[(alpha3b, country, script)]
        return alpha3b  # type: ignore[no-any-return]

    def reverse(self, code: str) -> LanguageTuple:
        """Reverse a custom code into alpha3, country and script code."""
        if code in self.from_opensubtitles:
            return self.from_opensubtitles[code]  # type: ignore[no-any-return]
        for conv in [self.alpha3b_converter, self.alpha2_converter]:
            conv = cast('LanguageReverseConverter', conv)
            try:
                return conv.reverse(code)  # type: ignore[no-any-return]
            except LanguageReverseError:
                pass
        raise LanguageReverseError(code)
