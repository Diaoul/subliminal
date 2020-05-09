# -*- coding: utf-8 -*-
"""
"""
from babelfish import Language, LanguageReverseConverter

from ..exceptions import ConfigurationError


# alpha3 extracted from `https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes`
# Subscene language list extracted from it's upload form
from_subscene = {
        'Farsi/Persian': 'fas', 'Greek': 'ell', 'Greenlandic': 'kal',
        'Malay': 'msa', 'Pashto': 'pus', 'Punjabi': 'pan', 'Swahili': 'swa'
}

to_subscene = {val: key for key, val in from_subscene.items()}

from_subscene_with_country = {
    'Brazillian Portuguese': ('por', 'BR')
}

to_subscene_with_country = {val: key for key, val in from_subscene_with_country.items()}

exact_languages_alpha3 = [
        'ara', 'aze', 'bel', 'ben', 'bos', 'bul', 'cat', 'ces', 'dan', 'deu',
        'eng', 'epo', 'est', 'eus', 'fin', 'fra', 'heb', 'hin', 'hrv', 'hun',
        'hye', 'ind', 'isl', 'ita', 'jpn', 'kat', 'kor', 'kur', 'lav', 'lit',
        'mal', 'mkd', 'mni', 'mon', 'mya', 'nld', 'nor', 'pol', 'por', 'ron',
        'rus', 'sin', 'slk', 'slv', 'som', 'spa', 'sqi', 'srp', 'sun', 'swe',
        'tam', 'tel', 'tgl', 'tha', 'tur', 'ukr', 'urd', 'vie', 'yor'
]

# TODO: specify codes for unspecified_languages
unspecified_languages = [
        'Big 5 code', 'Bulgarian/ English', 'Chinese BG code',
        'Dutch/ English', 'English/ German', 'Hungarian/ English', 'Rohingya'
]

supported_languages = {Language(lang) for lang in exact_languages_alpha3}

alpha3_of_code = {lang.name: lang.alpha3 for lang in supported_languages}

supported_languages.update({Language(lang) for lang in to_subscene})

supported_languages.update({Language(lang, cr) for lang, cr in to_subscene_with_country})


class SubsceneConverter(LanguageReverseConverter):
    codes = {lang.name for lang in supported_languages}

    def convert(self, alpha3, country=None, script=None):
        if alpha3 in exact_languages_alpha3:
            return Language(alpha3).name

        if alpha3 in to_subscene:
            return to_subscene[alpha3]

        if (alpha3, country) in to_subscene_with_country:
            to_subscene_with_country[(alpha3, country)]

        message = "unsupported language for subscene: %s, %s, %s" \
            % (alpha3, country, script)
        raise ConfigurationError(message)

    def reverse(self, code):
        if code in from_subscene_with_country:
            return from_subscene_with_country[code]

        if code in from_subscene:
            return (from_subscene[code],)

        if code in alpha3_of_code:
            return (alpha3_of_code[code],)

        if code in unspecified_languages:
            message = "currently this language is unspecified: %s" % code
            raise NotImplementedError(message)

        message = "unknown language code for subscene: %s" % code
        raise ConfigurationError(message)
