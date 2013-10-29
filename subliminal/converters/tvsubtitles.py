# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from babelfish.converters.alpha2 import Alpha2Converter


class TVsubtitlesConverter(Alpha2Converter):
    def __init__(self):
        super(TVsubtitlesConverter, self).__init__()
        self.from_tvsubtitles = {'br': ('por', 'BR'), 'ua': ('ukr', None), 'gr': ('ell', None), 'cn': ('zho', None),
                                 'jp': ('jpn', None), 'cz': ('ces', None)}
        self.to_tvsubtitles = {v: k for k, v in self.from_tvsubtitles}
        self.codes |= set(self.from_tvsubtitles.keys())

    def convert(self, alpha3, country=None):
        if (alpha3, country) in self.to_tvsubtitles:
            return self.to_tvsubtitles[(alpha3, country)]
        return super(TVsubtitlesConverter, self).convert(alpha3, country)

    def reverse(self, tvsubtitles):
        if tvsubtitles in self.from_tvsubtitles:
            return self.from_tvsubtitles[tvsubtitles]
        return super(TVsubtitlesConverter, self).reverse(tvsubtitles)
