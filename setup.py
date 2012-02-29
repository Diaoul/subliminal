#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Subliminal.  If not, see <http://www.gnu.org/licenses/>.
from setuptools import setup
execfile('subliminal/infos.py')


setup(name='subliminal',
    version=__version__,
    license='LGPLv3',
    description='Subtitles, faster than your thoughts',
    long_description=open('README.rst').read() + '\n\n' +
                     open('NEWS.rst').read(),
    classifiers=['Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Multimedia :: Video'],
    keywords='subliminal video movie subtitle python library',
    author='Antoine Bertin',
    author_email='diaoulael@gmail.com',
    url='https://github.com/Diaoul/subliminal',
    packages=['subliminal'],
    scripts=['scripts/subliminal'],
    py_modules=['subliminal'],
    install_requires=['BeautifulSoup>=3.2.0', 'guessit>=0.2', 'requests>=0.10.6', 'enzyme>=0.1'])
