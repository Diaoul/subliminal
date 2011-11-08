# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import re

#TODO: Make a languages.py with everything related to languages...
LANGUAGES = set(['aa', 'ab', 'ae', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi',
                 'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv',
                 'dz', 'ee', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd',
                 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ia', 'id', 'ie', 'ig',
                 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko',
                 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh',
                 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my', 'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no',
                 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt', 'qu', 'rm', 'rn', 'ro',
                 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st',
                 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty',
                 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zu', 'pt-br'])  # ISO 639-1 + pt-br

LANGUAGES_2_1 = {'aar': 'aa', 'abk': 'ab', 'afr': 'af', 'aka': 'ak', 'amh': 'am', 'ara': 'ar', 'arg': 'an', 'asm': 'as',
                 'ava': 'av', 'ave': 'ae', 'aym': 'ay', 'aze': 'az', 'bak': 'ba', 'bam': 'bm', 'bel': 'be', 'ben': 'bn',
                 'bih': 'bh', 'bis': 'bi', 'bos': 'bs', 'bre': 'br', 'bul': 'bg', 'cat': 'ca', 'cha': 'ch', 'che': 'ce',
                 'chu': 'cu', 'chv': 'cv', 'cor': 'kw', 'cos': 'co', 'cre': 'cr', 'dan': 'da', 'div': 'dv', 'dzo': 'dz',
                 'eng': 'en', 'epo': 'eo', 'est': 'et', 'ewe': 'ee', 'fao': 'fo', 'fij': 'fj', 'fin': 'fi', 'fry': 'fy',
                 'ful': 'ff', 'gla': 'gd', 'gle': 'ga', 'glg': 'gl', 'glv': 'gv', 'grn': 'gn', 'guj': 'gu', 'hat': 'ht',
                 'hau': 'ha', 'heb': 'he', 'her': 'hz', 'hin': 'hi', 'hmo': 'ho', 'hrv': 'hr', 'hun': 'hu', 'ibo': 'ig',
                 'ido': 'io', 'iii': 'ii', 'iku': 'iu', 'ile': 'ie', 'ina': 'ia', 'ind': 'id', 'ipk': 'ik', 'ita': 'it',
                 'jav': 'jv', 'jpn': 'ja', 'kal': 'kl', 'kan': 'kn', 'kas': 'ks', 'kau': 'kr', 'kaz': 'kk', 'khm': 'km',
                 'kik': 'ki', 'kin': 'rw', 'kir': 'ky', 'kom': 'kv', 'kon': 'kg', 'kor': 'ko', 'kua': 'kj', 'kur': 'ku',
                 'lao': 'lo', 'lat': 'la', 'lav': 'lv', 'lim': 'li', 'lin': 'ln', 'lit': 'lt', 'ltz': 'lb', 'lub': 'lu',
                 'lug': 'lg', 'mah': 'mh', 'mal': 'ml', 'mar': 'mr', 'mlg': 'mg', 'mlt': 'mt', 'mon': 'mn', 'nau': 'na',
                 'nav': 'nv', 'nbl': 'nr', 'nde': 'nd', 'ndo': 'ng', 'nep': 'ne', 'nno': 'nn', 'nob': 'nb', 'nor': 'no',
                 'nya': 'ny', 'oci': 'oc', 'oji': 'oj', 'ori': 'or', 'orm': 'om', 'oss': 'os', 'pan': 'pa', 'pli': 'pi',
                 'pol': 'pl', 'por': 'pt', 'pus': 'ps', 'que': 'qu', 'roh': 'rm', 'run': 'rn', 'rus': 'ru', 'sag': 'sg',
                 'san': 'sa', 'sin': 'si', 'slv': 'sl', 'sme': 'se', 'smo': 'sm', 'sna': 'sn', 'snd': 'sd', 'som': 'so',
                 'sot': 'st', 'spa': 'es', 'srd': 'sc', 'srp': 'sr', 'ssw': 'ss', 'sun': 'su', 'swa': 'sw', 'swe': 'sv',
                 'tah': 'ty', 'tam': 'ta', 'tat': 'tt', 'tel': 'te', 'tgk': 'tg', 'tgl': 'tl', 'tha': 'th', 'tir': 'ti',
                 'ton': 'to', 'tsn': 'tn', 'tso': 'ts', 'tuk': 'tk', 'tur': 'tr', 'twi': 'tw', 'uig': 'ug', 'ukr': 'uk',
                 'urd': 'ur', 'uzb': 'uz', 'ven': 've', 'vie': 'vi', 'vol': 'vo', 'wln': 'wa', 'wol': 'wo', 'xho': 'xh',
                 'yid': 'yi', 'yor': 'yo', 'zha': 'za', 'zul': 'zu'}  # ISO 639-2 to ISO 639-1


class PluginConfig(object):
    def __init__(self, multi=None, cache_dir=None, filemode=None):
        self.multi = multi
        self.cache_dir = cache_dir
        self.filemode = filemode

def get_keywords(guess):
    keywords = set()
    for k in ['releaseGroup', 'screenSize', 'videoCodec', 'format']:
        if k in guess:
            keywords = keywords | split_keyword(guess[k].lower())
    return keywords

def split_keyword(keyword):
    split = set(re.findall(r'\w+', keyword))
    return split
