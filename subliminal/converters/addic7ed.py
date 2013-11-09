# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from babelfish.converters.name import NameConverter


class Addic7edConverter(NameConverter):
    def __init__(self):
        super(Addic7edConverter, self).__init__()
        self.from_addic7ed = {'Català': ('cat',), 'Chinese (Simplified)': ('zho',), 'Chinese (Traditional)': ('zho',),
                              'Euskera': ('eus',), 'Galego': ('glg',), 'Greek': ('ell',), 'Malay': ('msa',),
                              'Portuguese (Brazilian)': ('por', 'BR'), 'Serbian (Cyrillic)': ('srp', None, 'Cyrl'),
                              'Serbian (Latin)': ('srp',), 'Spanish (Latin America)': ('spa',),
                              'Spanish (Spain)': ('spa',)}
        self.to_addic7ed = {('cat',): 'Català', ('zho',): 'Chinese (Simplified)', ('eus',): 'Euskera',
                            ('glg',): 'Galego', ('ell',): 'Greek', ('msa',): 'Malay',
                            ('por', 'BR'): 'Portuguese (Brazilian)', ('srp', None, 'Cyrl'): 'Serbian (Cyrillic)'}
        self.codes |= set(self.from_addic7ed.keys())

    def convert(self, alpha3, country=None, script=None):
        if (alpha3, country, script) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country, script)]
        if (alpha3, country) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3, country)]
        if (alpha3,) in self.to_addic7ed:
            return self.to_addic7ed[(alpha3,)]
        return super(Addic7edConverter, self).convert(alpha3, country, script)

    def reverse(self, addic7ed):
        if addic7ed in self.from_addic7ed:
            return self.from_addic7ed[addic7ed]
        return super(Addic7edConverter, self).reverse(addic7ed)
