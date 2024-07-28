# -*- coding: utf-8 -*-
from babelfish import LanguageReverseConverter, language_converters


class TuSubtituloConverter(LanguageReverseConverter):
    def __init__(self):
        self.name_converter = language_converters['name']
        self.from_tusubtitulo = {u'Español': ('spa',), u'Español (España)': ('spa',),
                                 u'Español (Latinoamérica)': ('spa', 'MX'), u'Català': ('cat',), 'English': ('eng',),
                                 'Galego': ('glg',), 'Portuguese': ('por',), 'English (US)': ('eng', 'US'),
                                 'English (UK)': ('eng', 'GB'), 'Brazilian': ('por', 'BR')}
        self.to_tusubtitulo = {('cat',): u'Català', ('glg',): 'Galego', ('por', 'BR'): 'Brazilian'}
        self.codes = set(self.from_tusubtitulo.keys())

    def convert(self, alpha3, country=None, script=None):
        if (alpha3, country) in self.to_tusubtitulo:
            return self.to_tusubtitulo[(alpha3, country)]
        if (alpha3,) in self.to_tusubtitulo:
            return self.to_tusubtitulo[(alpha3,)]

        return self.name_converter.convert(alpha3, country, script)

    def reverse(self, tusubtitulo):
        if tusubtitulo in self.from_tusubtitulo:
            return self.from_tusubtitulo[tusubtitulo]

        return self.name_converter.reverse(tusubtitulo)
