#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import re
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    return io.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


# requirements
setup_requirements = ['pytest-runner'] if {'pytest', 'test', 'ptr'}.intersection(sys.argv) else []

install_requirements = ['guessit>=2.0.1', 'babelfish>=0.5.2', 'enzyme>=0.4.1', 'beautifulsoup4>=4.2.0',
                        'requests>=2.0', 'click>=4.0', 'dogpile.cache>=0.5.4', 'stevedore>=1.0.0',
                        'chardet>=2.3.0', 'pysrt>=1.0.1', 'six>=1.9.0', 'appdirs>=1.3', 'rarfile>=2.7',
                        'pytz>=2012c']
if sys.version_info < (3, 2):
    install_requirements.append('futures>=3.0')

test_requirements = ['sympy', 'vcrpy>=1.6.1', 'pytest', 'pytest-pep8', 'pytest-flakes', 'pytest-cov']
if sys.version_info < (3, 3):
    test_requirements.append('mock')

dev_requirements = ['tox', 'sphinx', 'sphinxcontrib-programoutput', 'wheel']


setup(name='subliminal',
      version=find_version('subliminal', '__init__.py'),
      license='MIT',
      description='Subtitles, faster than your thoughts',
      long_description=read('README.rst') + '\n\n' + read('HISTORY.rst'),
      keywords='subtitle subtitles video movie episode tv show series',
      url='https://github.com/Diaoul/subliminal',
      author='Antoine Bertin',
      author_email='diaoulael@gmail.com',
      packages=find_packages(),
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Multimedia :: Video'
      ],
      entry_points={
          'subliminal.providers': [
              'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
              'legendastv = subliminal.providers.legendastv:LegendasTVProvider',
              'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
              'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
              'shooter = subliminal.providers.shooter:ShooterProvider',
              'subscenter = subliminal.providers.subscenter:SubsCenterProvider',
              'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
              'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
          ],
          'subliminal.refiners': [
              'metadata = subliminal.refiners.metadata:refine',
              'omdb = subliminal.refiners.omdb:refine',
              'tvdb = subliminal.refiners.tvdb:refine'
          ],
          'babelfish.language_converters': [
              'addic7ed = subliminal.converters.addic7ed:Addic7edConverter',
              'shooter = subliminal.converters.shooter:ShooterConverter',
              'thesubdb = subliminal.converters.thesubdb:TheSubDBConverter',
              'tvsubtitles = subliminal.converters.tvsubtitles:TVsubtitlesConverter'
          ],
          'console_scripts': [
              'subliminal = subliminal.cli:subliminal'
          ]
      },
      setup_requires=setup_requirements,
      install_requires=install_requirements,
      tests_require=test_requirements,
      extras_require={
          'test': test_requirements,
          'dev': dev_requirements
      })
