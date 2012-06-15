#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from subliminal.language import Language, Country, language_set, language_list
import unittest


class LanguageListTestCase(unittest.TestCase):
    def test_list_contains(self):
        languages = list([Language('fr'), Language('en-US'), Language('en-GB')])
        self.assertTrue(Language('fr') in languages)
        self.assertTrue(Language('en-US') in languages)
        self.assertTrue(Language('en') not in languages)
        self.assertTrue(Language('fr-BE') not in languages)

    def test_language_list_contains(self):
        languages = language_list(['fr', 'en-US', 'en-GB'])
        self.assertTrue(Language('fr') in languages)
        self.assertTrue(Language('en-US') in languages)
        self.assertTrue(Language('en') not in languages)
        self.assertTrue(Language('fr-BE') in languages)

    def test_list_index(self):
        languages = [Language('fr'), Language('en-US'), Language('en-GB')]
        self.assertTrue(languages.index(Language('fr')) == 0)
        self.assertTrue(languages.index(Language('en-US')) == 1)
        self.assertTrue(languages.index(Language('en-GB')) == 2)
        with self.assertRaises(ValueError):
            languages.index(Language('fr-BE'))

    def test_language_list_index(self):
        languages = language_list(['fr', 'en-US', 'en-GB'])
        self.assertTrue(languages.index(Language('fr')) == 0)
        self.assertTrue(languages.index(Language('en-US')) == 1)
        self.assertTrue(languages.index(Language('en-GB')) == 2)
        self.assertTrue(languages.index(Language('fr-BE')) == 0)


class LanguageSetTestCase(unittest.TestCase):
    def test_set_contains(self):
        languages = set([Language('fr'), Language('en-US'), Language('en-GB')])
        self.assertTrue(Language('fr') in languages)
        self.assertTrue(Language('en-US') in languages)
        self.assertTrue(Language('en') not in languages)
        self.assertTrue(Language('fr-BE') not in languages)

    def test_language_set_contains(self):
        languages = language_set(['fr', 'en-US', 'en-GB'])
        self.assertTrue(Language('fr') in languages)
        self.assertTrue(Language('en-US') in languages)
        self.assertTrue(Language('en') not in languages)
        self.assertTrue(Language('fr-BE') in languages)

    def test_language_set_intersect(self):
        languages = language_set(['fr', 'en-US', 'en-GB'])
        self.assertTrue(len(languages & language_set([Language('en')])) == 2)
        self.assertTrue(len(language_set([Language('en')]) & languages) == 2)
        self.assertTrue(len(languages & language_set([Language('fr')])) == 1)

    def test_language_set_substract(self):
        languages = language_set(['fr', 'en-US', 'en-GB'])
        self.assertTrue(len(languages - language_set(['en'])) == 1)
        self.assertTrue(len(languages - language_set(['en-US'])) == 2)
        self.assertTrue(len(languages - language_set(['en-US', 'fr'])) == 1)


class LanguageTestCase(unittest.TestCase):
    def test_attrs(self):
        language = Language('French')
        self.assertTrue(language.alpha2 == 'fr')
        self.assertTrue(language.alpha3 == 'fre')
        self.assertTrue(language.terminologic == 'fra')
        self.assertTrue(language.name == 'French')
        self.assertTrue(language.french_name == u'français')

    def test_eq(self):
        language = Language('French')
        self.assertTrue(language == Language('fr'))
        self.assertTrue(language == Language('fre'))
        self.assertTrue(language == Language('fra'))
        self.assertTrue(language == Language('Français'))

    def test_ne(self):
        self.assertTrue(Language('French') != Language('en'))

    def test_in(self):
        self.assertTrue(Language('Portuguese (BR)') in Language('Portuguese - Brazil'))
        self.assertTrue(Language('Portuguese (BR)') in Language('Portuguese'))
        self.assertTrue(Language('Portuguese') not in Language('Portuguese (BR)'))

    def test_with_country(self):
        self.assertTrue(Language('Portuguese (BR)').country == Country('Brazil'))
        self.assertTrue(Language('pt_BR').country == Country('Brazil'))
        self.assertTrue(Language('fr - France').country == Country('France'))
        self.assertTrue(Language('fra', country='FR').country == Country('France'))
        self.assertTrue(Language('fra', country=Country('FRA')).country == Country('France'))

    def test_eq_with_country(self):
        self.assertTrue(Language('Portuguese (BR)') == Language('Portuguese - Brazil'))
        self.assertTrue(Language('English') == Language('en'))

    def test_ne_with_country(self):
        self.assertTrue(Language('Portuguese') != Language('Portuguese (BR)'))
        self.assertTrue(Language('English (US)') != Language('English (GB)'))

    def test_hash(self):
        self.assertTrue(hash(Language('French')) == hash('fre'))

    def test_missing(self):
        with self.assertRaises(ValueError):
            Language('zzz')


class CountryTestCase(unittest.TestCase):
    def test_attrs(self):
        country = Country('France')
        self.assertTrue(country.alpha2 == 'FR')
        self.assertTrue(country.alpha3 == 'FRA')
        self.assertTrue(country.name == 'France')

    def test_eq(self):
        country = Country('France')
        self.assertTrue(country == Country('FR'))
        self.assertTrue(country == Country('FRA'))
        self.assertTrue(country == Country('250'))

    def test_ne(self):
        self.assertTrue(Country('France') != Country('GB'))

    def test_hash(self):
        self.assertTrue(hash(Country('France')) == hash('FRA'))

    def test_missing(self):
        with self.assertRaises(ValueError):
            Country('ZZ')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(CountryTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(LanguageTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(LanguageSetTestCase))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(LanguageListTestCase))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(suite())
