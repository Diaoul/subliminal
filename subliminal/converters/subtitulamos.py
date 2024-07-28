# -*- coding: utf-8 -*-
from babelfish import LanguageReverseConverter, language_converters


class SubtitulamosConverter(LanguageReverseConverter):
    def __init__(self):
        self.name_converter = language_converters['name']
        self.from_subtitulamos = {u'Español': ('spa',), u'Español (España)': ('spa',),
                                  u'Español (Latinoamérica)': ('spa', 'MX'), u'Català': ('cat',), 'English': ('eng',),
                                  'Galego': ('glg',), 'Portuguese': ('por',), 'English (US)': ('eng', 'US'),
                                  'English (UK)': ('eng', 'GB'), 'Brazilian': ('por', 'BR')}
        self.to_subtitulamos = {('cat',): u'Català', ('glg',): 'Galego', ('por', 'BR'): 'Brazilian'}
        self.codes = set(self.from_subtitulamos.keys())

    def convert(self, alpha3, country=None, script=None):
        if (alpha3, country) in self.to_subtitulamos:
            return self.to_subtitulamos[(alpha3, country)]
        if (alpha3,) in self.to_subtitulamos:
            return self.to_subtitulamos[(alpha3,)]

        return self.name_converter.convert(alpha3, country, script)

    def reverse(self, subtitulamos):
        if subtitulamos in self.from_subtitulamos:
            return self.from_subtitulamos[subtitulamos]

        return self.name_converter.reverse(subtitulamos)
