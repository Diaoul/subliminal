# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from babelfish.converters.name import NameConverter


class Addic7edConverter(NameConverter):
    def __init__(self):
        super(Addic7edConverter, self).__init__()
        self.from_addic7ed = {'Català': ('cat', None), 'Chinese (Simplified)': ('zho', None),
                              'Chinese (Traditional)': ('zho', None), 'Euskera': ('eus', None),
                              'Galego': ('glg', None), 'Greek': ('ell', None),
                              'Malay': ('msa', None), 'Portuguese (Brazilian)': ('por', 'BR'),
                              'Serbian (Cyrillic)': ('srp', None), 'Serbian (Latin)': ('srp', None),
                              'Spanish (Latin America)': ('spa', None), 'Spanish (Spain)': ('spa', None)}
        self.to_addic7ed = {('cat', None): 'Català', ('zho', None): 'Chinese (Simplified)',
                            ('eus', None): 'Euskera', ('glg', None): 'Galego',
                            ('ell', None): 'Greek', ('msa', None): 'Malay',
                            ('por', 'BR'): 'Portuguese (Brazilian)', ('srp', None): 'Serbian (Cyrillic)'}
        self.codes |= set(self.from_addic7ed.keys())

    def convert(self, alpha3, country=None):
        if (alpha3, country) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country)]
        return super(Addic7edConverter, self).convert(alpha3, country)

    def reverse(self, addic7ed):
        if addic7ed in self.from_addic7ed:
            return self.from_addic7ed[addic7ed]
        return super(Addic7edConverter, self).reverse(addic7ed)
