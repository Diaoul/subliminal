from __future__ import annotations

from babelfish import LanguageReverseConverter, language_converters


class OpenSubtitlesComConverter(LanguageReverseConverter):
    """Language converter for OpenSubtitlesCom.

    From GET API at: https://api.opensubtitles.com/api/v1/infos/languages
    """

    def __init__(self) -> None:
        self.alpha2_converter = language_converters['alpha2']
        self.from_opensubtitlescom = {
            'pt-br': ('por', 'BR'),
            'pt-pt': ('por', 'PT'),
            'zh-cn': ('zho', 'CN'),
            'zh-tw': ('zho', 'TW'),
            'ze': ('zho', 'US'),
            'me': ('srp', 'ME'),
            'sy': ('syr',),
            'ma': ('mni',),
            'at': ('ast',),
        }
        self.to_opensubtitlescom = {v: k for k, v in self.from_opensubtitlescom.items()}
        self.codes = self.alpha2_converter.codes | set(self.from_opensubtitlescom.keys())

    def convert(self, alpha3, country=None, script=None):
        if (alpha3, country) in self.to_opensubtitlescom:
            return self.to_opensubtitlescom[(alpha3, country)]
        if (alpha3,) in self.to_opensubtitlescom:
            return self.to_opensubtitlescom[(alpha3,)]

        return self.alpha2_converter.convert(alpha3, country, script)

    def reverse(self, opensubtitlescom):
        opensubtitlescom_lower = opensubtitlescom.lower()
        if opensubtitlescom_lower in self.from_opensubtitlescom:
            return self.from_opensubtitlescom[opensubtitlescom_lower]

        return self.alpha2_converter.reverse(opensubtitlescom)
