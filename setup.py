#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(name='subliminal',
    version='0.7.3',
    license='MIT',
    description='Subtitles, faster than your thoughts',
    long_description=open('README.rst').read() + '\n\n' + open('HISTORY.rst').read(),
    keywords='subtitle subtitles video movie episode tv show',
    url='https://github.com/Diaoul/subliminal',
    author='Antoine Bertin',
    author_email='diaoulael@gmail.com',
    packages=find_packages(),
    classifiers=['Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Multimedia :: Video'],
    entry_points={
        'console_scripts': ['subliminal = subliminal.cli:subliminal'],
        'subliminal.providers': ['addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
                                 'bierdopje = subliminal.providers.bierdopje:BierDopjeProvider',
                                 'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
                                 'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
                                 'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
                                 'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'],
        'babelfish.language_converters': ['addic7ed = subliminal.converters.addic7ed:Addic7edConverter',
                                          'podnapisi = subliminal.converters.podnapisi:PodnapisiConverter',
                                          'tvsubtitles = subliminal.converters.tvsubtitles:TVsubtitlesConverter']
    },
    install_requires=open('requirements.txt').readlines(),
    test_suite='subliminal.tests.suite')
