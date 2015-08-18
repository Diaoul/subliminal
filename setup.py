#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import re
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', 'Arguments to pass to py.test')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

# requirements
install_requirements = ['guessit>=0.9.1', 'babelfish>=0.5.2', 'enzyme>=0.4.1', 'beautifulsoup4>=4.2.0',
                        'requests>=2.0', 'click>=4.0', 'dogpile.cache>=0.5.4', 'stevedore>=1.0.0',
                        'chardet>=2.3.0', 'pysrt>=1.0.1', 'six>=1.9.0']

test_requirements = ['sympy', 'vcrpy>=1.6.1', 'pytest', 'pytest-pep8', 'pytest-flakes',
                     'pytest-cov']
if sys.version_info < (3, 3):
    test_requirements.append('mock')

dev_requirements = ['tox', 'sphinx', 'wheel']

# package informations
with io.open('subliminal/__init__.py', 'r') as f:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]$', f.read(),
                        re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')

with io.open('README.rst', 'r', encoding='utf-8') as f:
    readme = f.read()

with io.open('HISTORY.rst', 'r', encoding='utf-8') as f:
    history = f.read()


setup(name='subliminal',
      version=version,
      license='MIT',
      description='Subtitles, faster than your thoughts',
      long_description=readme + '\n\n' + history,
      keywords='subtitle subtitles video movie episode tv show',
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
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Multimedia :: Video'
      ],
      entry_points={
          'subliminal.providers': [
              'addic7ed = subliminal.providers.addic7ed:Addic7edProvider',
              'napiprojekt = subliminal.providers.napiprojekt:NapiProjektProvider',
              'opensubtitles = subliminal.providers.opensubtitles:OpenSubtitlesProvider',
              'podnapisi = subliminal.providers.podnapisi:PodnapisiProvider',
              'thesubdb = subliminal.providers.thesubdb:TheSubDBProvider',
              'tvsubtitles = subliminal.providers.tvsubtitles:TVsubtitlesProvider'
          ],
          'babelfish.language_converters': [
              'addic7ed = subliminal.converters.addic7ed:Addic7edConverter',
              'tvsubtitles = subliminal.converters.tvsubtitles:TVsubtitlesConverter'
          ],
          'console_scripts': [
              'subliminal = subliminal.cli:subliminal'
          ]
      },
      install_requires=install_requirements,
      tests_require=test_requirements,
      extras_require={
          'test': test_requirements,
          'dev': dev_requirements
      },
      cmdclass={'test': PyTest})
