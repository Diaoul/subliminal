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
import sys
from setuptools import setup


requirements = open('requirements.txt').readlines()
if sys.version_info[:2] in ((2, 6), (3, 1)):
    requirements.append('argparse>=1.2.1')

setup(name='subliminal',
    version='0.7-dev',
    license='LGPLv3',
    description='Subtitles, faster than your thoughts',
    long_description=open('README.rst').read() + '\n\n' + open('NEWS.rst').read(),
    classifiers=['Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Multimedia :: Video'],
    keywords='subtitle subtitles video movie episode tv show',
    author='Antoine Bertin',
    author_email='diaoulael@gmail.com',
    url='https://github.com/Diaoul/subliminal',
    packages=['subliminal', 'subliminal.services', 'subliminal.tests'],
    entry_points={
        'console_scripts': ['subliminal = subliminal.scripts:main'],
    },
    test_suite='subliminal.tests.suite',
    tests_require=open('test-requirements.txt').readlines(),
    install_requires=requirements,
    extras_require={'full': open('optional-requirements.txt').readlines()})
