# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from babelfish import LanguageReverseConverter, LanguageConvertError, LanguageReverseError


class ShooterConverter(LanguageReverseConverter):
    def __init__(self):
        self.from_shooter = {'chn': ('zho',), 'eng': ('eng',)}
        self.to_shooter = {v: k for k, v in self.from_shooter.items()}
        self.codes = set(self.from_shooter.keys())

    def convert(self, alpha3, country=None, script=None):
        if (alpha3,) in self.to_shooter:
            return self.to_shooter[(alpha3,)]
        if (alpha3, country) in self.to_shooter:
            return self.to_shooter[(alpha3, country)]
        if (alpha3, country, script) in self.to_shooter:
            return self.to_shooter[(alpha3, country, script)]
        raise LanguageConvertError(alpha3, country, script)

    def reverse(self, shooter):
        if shooter not in self.from_shooter:
            raise LanguageReverseError(shooter)
        return self.from_shooter[shooter]
