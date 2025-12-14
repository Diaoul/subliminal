

.. towncrier release notes start

2.5.0 (2025-12-14)
^^^^^^^^^^^^^^^^^^

Provider Changes
----------------

- OpenSubtitlesCom: add a max_result_pages parameter to limit the number of result pages to speed up the search (`#1321 <https://github.com/Diaoul/subliminal/issues/1321>`__)


Documentation
-------------

- fix ``generate_default_config`` for ``click==8.3`` and pin to ``click<8.3`` until another regression is fixed. (`#1318 <https://github.com/Diaoul/subliminal/issues/1318>`__)


Misc
----

- add support for python 3.14 (`#1317 <https://github.com/Diaoul/subliminal/issues/1317>`__)
- Fix test with click 8.3.0 running in parallel (`#1320 <https://github.com/Diaoul/subliminal/issues/1320>`__)
- fix test on big-endian system (`#1323 <https://github.com/Diaoul/subliminal/issues/1323>`__)
- compatibility with stevedore 5.6.0 (`#1325 <https://github.com/Diaoul/subliminal/issues/1325>`__)
- fix some tests to pass in a dirty environment (`#1326 <https://github.com/Diaoul/subliminal/issues/1326>`__)
- update pre-commit hook versions (`#1329 <https://github.com/Diaoul/subliminal/issues/1329>`__)
- Fix some test so they are more reliable and stable (`#1331 <https://github.com/Diaoul/subliminal/issues/1331>`__)


2.4.0 (2025-09-03)
^^^^^^^^^^^^^^^^^^

Changes
-------

- score: add fps match, remove hearing_impaired match (`#1250 <https://github.com/Diaoul/subliminal/issues/1250>`__)


CLI Changes
-----------

- cli: refactor the cli.py file into a folder (`#1299 <https://github.com/Diaoul/subliminal/issues/1299>`__)


Documentation
-------------

- doc: add a section in the README to run subliminal with the ``--debug`` flag. (`#1308 <https://github.com/Diaoul/subliminal/issues/1308>`__)


Misc
----

- ensure Episode.series is always a string, not a list from guessit bug (`#1304 <https://github.com/Diaoul/subliminal/issues/1304>`__)


2.3.2 (2025-05-08)
^^^^^^^^^^^^^^^^^^

Provider Changes
----------------

- [BSPlayer] disabled by default because it is slow. Can be enabled with the ``-pp bsplayer`` CLI option (`#1293 <https://github.com/Diaoul/subliminal/issues/1293>`__)


Misc
----

- `#1276 <https://github.com/Diaoul/subliminal/issues/1276>`__, `#1289 <https://github.com/Diaoul/subliminal/issues/1289>`__


2.3.1 (2025-05-08)
^^^^^^^^^^^^^^^^^^

Misc
----

- `#1278 <https://github.com/Diaoul/subliminal/issues/1278>`__


2.3.0 (2025-04-27)
^^^^^^^^^^^^^^^^^^

Changes
-------

- By default, use the latest of creation and modification date to compute the age of the file.
  Use the CLI option `--no-use-ctime` to use the modification date only, that was the previous behavior. (`#860 <https://github.com/Diaoul/subliminal/issues/860>`__)
- Make `rarfile` an optional dependency, install with subliminal[rar] (`#1096 <https://github.com/Diaoul/subliminal/issues/1096>`__)
- add `subtitles` attribute to Video (`#1151 <https://github.com/Diaoul/subliminal/issues/1151>`__)
- Use `knowit` to extract information from video file, instead of `enzyme`:
  frame rate, duration and subtitles.
  `knowit` relies on external programs (`mediainfo`, `ffmpeg`, `mkvmerge`)
  and falls back to using `enzyme` if none is installed.
  On Windows and MacOS, `libmediainfo` is installed automatically
  via the `pymediainfo` python package dependency.
  On Linux, the `libmediainfo` or `mediainfo` package needs to be installed
  with the package manager of your distribution. (`#1154 <https://github.com/Diaoul/subliminal/issues/1154>`__)
- show "Insufficient data to process the guess" without debug, but with verbose (`#1164 <https://github.com/Diaoul/subliminal/issues/1164>`__)
- Add Provider.hash_video staticmethod, to allow creating standalone providers. (`#1172 <https://github.com/Diaoul/subliminal/issues/1172>`__)
- Drop python 3.8, support python 3.13. (`#1176 <https://github.com/Diaoul/subliminal/issues/1176>`__)
- Remove addic7ed and napiprojekt from the list of disabled providers.
  Remove the default_providers and default_refiners variables,
  instead the get_default_providers() and get_default_refiners() functions can be used. (`#1181 <https://github.com/Diaoul/subliminal/issues/1181>`__)
- Add a mock provider.
  Fix doctest. (`#1185 <https://github.com/Diaoul/subliminal/issues/1185>`__)
- Add release scripts, documentation and Github Actions (`#1186 <https://github.com/Diaoul/subliminal/issues/1186>`__)
- Rename optional dependency test -> tests.
  Improve security of github actions using woodruffw/zizmor. (`#1190 <https://github.com/Diaoul/subliminal/issues/1190>`__)
- Use hatch builder and hatch-vcs (`#1192 <https://github.com/Diaoul/subliminal/issues/1192>`__)
- Add a Github action to publish the docker images to ghcr.io (`#1196 <https://github.com/Diaoul/subliminal/issues/1196>`__)
- Can use `python -m subliminal` (`#1197 <https://github.com/Diaoul/subliminal/issues/1197>`__)
- create a prepare_tests.py script to download the tests data beforehand and avoid repeated downloads (`#1220 <https://github.com/Diaoul/subliminal/issues/1220>`__)
- CLI option --use-ctime is set to True by default (`#1238 <https://github.com/Diaoul/subliminal/issues/1238>`__)


Provider Changes
----------------

- Added BSPlayer provider (`#996 <https://github.com/Diaoul/subliminal/issues/996>`__)
- [OpenSubtitlesCom] Avoid duplicate subtitles (`#1146 <https://github.com/Diaoul/subliminal/issues/1146>`__)
- Added Subtitulamos provider (`#1170 <https://github.com/Diaoul/subliminal/issues/1170>`__)


CLI Changes
-----------

- Add a --subtitle-format CLI option to force converting subtitles to another format (`#536 <https://github.com/Diaoul/subliminal/issues/536>`__)
- Add CLI `ignore` option for refiners, providers and subtitle ids. (`#585 <https://github.com/Diaoul/subliminal/issues/585>`__, `#1018 <https://github.com/Diaoul/subliminal/issues/1018>`__)
- Add a --skip-wrong-fps cli option to completely skip subtitles with FPS different from the video FPS (if detected) (`#748 <https://github.com/Diaoul/subliminal/issues/748>`__)
- add CLI options --force-embedded-subtitles and --force-external-subtitles.
  They are fine-tuned --force options to ignore only embedded or external existing subtitles.
  They are superseded by --force. (`#891 <https://github.com/Diaoul/subliminal/issues/891>`__)
- Add a `-n/--name` option to use a replacement name for the video.
  Sort files alphabetically before scanning a directory. (`#991 <https://github.com/Diaoul/subliminal/issues/991>`__, `#1132 <https://github.com/Diaoul/subliminal/issues/1132>`__)
- Add an option to change the style of the language suffix of saved subtitles.
  Allow adding the language type, hi or forced. (`#1022 <https://github.com/Diaoul/subliminal/issues/1022>`__)
- Remove the original-encoding CLI option, pass `--encoding=` for the same effect. (`#1125 <https://github.com/Diaoul/subliminal/issues/1125>`__)
- Add cli option to prefer or disfavor hearing impaired (-hi/-HI) or foreign only (-fo/-FO) subtitles. (`#1175 <https://github.com/Diaoul/subliminal/issues/1175>`__)
- Add a CLI option `--use-absolute-path` that can take the values 'fallback' (default), 'never' or 'always'
  to choose if the given path is transformed to an absolute path before guessing information from the path. (`#1216 <https://github.com/Diaoul/subliminal/issues/1216>`__)
- add a CLI option --logfile to log to file. Level can be specified with --logfile-level, default to DEBUG (`#1223 <https://github.com/Diaoul/subliminal/issues/1223>`__)


Deprecations
------------

- Deprecate the `--addic7ed USERNAME PASSWORD`, `--opensubtitles` and `--opensubtitlescom` CLI options
  in favor of `--provider.addic7ed.username USERNAME`, `--provider.addic7ed.password PASSWORD`, etc...
  Add a generic way of passing arguments to the providers using CLI options.
  Use environment variables to pass options to the CLI. (`#1179 <https://github.com/Diaoul/subliminal/issues/1179>`__)


Documentation
-------------

- `#1142 <https://github.com/Diaoul/subliminal/issues/1142>`__, `#1143 <https://github.com/Diaoul/subliminal/issues/1143>`__, `#1144 <https://github.com/Diaoul/subliminal/issues/1144>`__, `#1147 <https://github.com/Diaoul/subliminal/issues/1147>`__, `#1148 <https://github.com/Diaoul/subliminal/issues/1148>`__, `#1157 <https://github.com/Diaoul/subliminal/issues/1157>`__, `#1178 <https://github.com/Diaoul/subliminal/issues/1178>`__, `#1263 <https://github.com/Diaoul/subliminal/issues/1263>`__, `#1266 <https://github.com/Diaoul/subliminal/issues/1266>`__


Misc
----

- `#1134 <https://github.com/Diaoul/subliminal/issues/1134>`__, `#1153 <https://github.com/Diaoul/subliminal/issues/1153>`__, `#1171 <https://github.com/Diaoul/subliminal/issues/1171>`__, `#1174 <https://github.com/Diaoul/subliminal/issues/1174>`__, `#1187 <https://github.com/Diaoul/subliminal/issues/1187>`__, `#1191 <https://github.com/Diaoul/subliminal/issues/1191>`__, `#1209 <https://github.com/Diaoul/subliminal/issues/1209>`__, `#1211 <https://github.com/Diaoul/subliminal/issues/1211>`__, `#1228 <https://github.com/Diaoul/subliminal/issues/1228>`__, `#1229 <https://github.com/Diaoul/subliminal/issues/1229>`__, `#1237 <https://github.com/Diaoul/subliminal/issues/1237>`__, `#1243 <https://github.com/Diaoul/subliminal/issues/1243>`__


2.2.1
^^^^^
**release date:** 2024-06-27

* Add example subliminal.toml to documentation and fix documentation.
* [CLI] show the message about the config file only with the ``--debug`` option.
* Relax the ``platformdirs`` dependency requirement to ``>= 3``

2.2.0
^^^^^
**release date:** 2024-06-24

* Drop python2 support, the supported versions are `>=3.8,<=3.12`.
* Load CLI options from a configuration file with the ``--config/-c`` option (`#1084 <https://github.com/Diaoul/subliminal/pull/1084>`_).
* Change default encoding of downloaded subtitles to 'utf-8' (not the original encoding). Use the ``--original-encoding`` cli option to recover the previous default behavior (`#1125 <https://github.com/Diaoul/subliminal/pull/1125>`_).
* Add opensubtitlescom provider
* Add gestdown provider
* Add tmdb refiner (requires a personal API key)
* Fix tvsubtitles provider
* Fix opensubtitles provider
* Fix napiprojekt provider
* Fix podnapisi provider to use JSON API
* Fix addic7ed provider
* Remove thesubdb provider
* Remove argenteam provider
* Remove shooter provider
* Remove legendastv provider
* Use `pyproject.toml` to specify the package configurations.* Add pre-commit hook (`#1115 <https://github.com/Diaoul/subliminal/pull/1115>`_).
* Use ruff to lint and format
* Use mypy to check types
* Add type annotations
* Drop dependencies: pysrt, appdirs, six, pytz
* Add dependencies:
    - click-option-group>=0.5.6
    - platformdirs>=4.2
    - pysubs2>=1.7
    - srt>=3.5
    - tomli>=2
* Bump dependency versions:
    - babelfish>=0.6.1
    - chardet>=5.0
    - click>=8.0
    - dogpile.cache>=1.0
    - enzyme>=0.5.0
    - stevedore>=3.0

2.1.0
^^^^^
**release date:** 2020-05-02

* Improve legendastv provider matches
* Fix video extensions (.mk3d .ogm .ogv)
* Use new url to search for titles in legendastv provider
* Fix stevedore incompatibility
* Add support to webm video extension
* Make providers easier to be extended and customized
* Update podnapisi URL
* Add support to VIP/Donor accounts in legendastv provider
* Proper handling titles with year / country in legendastv provider
* Several minor enhancements in legendastv provider
* Add support for python 3.6, 3.7 and 3.8
* Drop support for python 3.3 and 3.4
* Do not discard providers bad zip/rar is downloaded
* SubsCenter provider removal
* Fix lxml parsing for Addic7ed provider
* Support titles with asterics in Addic7ed provider
* Add support to multi-episode search in Opensubtitles provider
* Fix multi-episode search in TVSubtitles provider
* Update to guessit 3
* Improve archive scanning
* Add Opensubtitles VIP provider
* Add country to Movie and Episode
* Add streaming_service to Video
* Add info property to Subtitle
* Do not search for subtitles if all required languages is already present
* Improve TVDB refiner to support series with comma
* Add alternative_titles to Video and enhance OMDB refiner to use alternative_titles
* Only compute video hashes when required
* Add apikey to OMDB refiner
* Fix Subtitle validation when unable to guess encoding
* Add support to rar in Dockerfile


2.0.5
^^^^^
**release date:** 2016-09-03

* Fix addic7ed provider for some series name
* Fix existing subtitles detection
* Improve scoring
* Add Docker container
* Add .ogv video extension


2.0.4
^^^^^
**release date:** 2016-09-03

* Fix subscenter


2.0.3
^^^^^
**release date:** 2016-06-10

* Fix clearing cache in CLI


2.0.2
^^^^^
**release date:** 2016-06-06

* Fix for dogpile.cache>=0.6.0
* Fix missing sphinx_rtd_theme dependency


2.0.1
^^^^^
**release date:** 2016-06-06

* Fix beautifulsoup4 minimal requirement


2.0.0
^^^^^
**release date:** 2016-06-04

* Add refiners to enrich videos with information from metadata, tvdb and omdb
* Add asynchronous provider search for faster searches
* Add registrable managers so subliminal can run without install
* Add archive support
* Add the ability to customize scoring logic
* Add an age argument to scan_videos for faster scanning
* Add legendas.tv provider
* Add shooter.cn provider
* Improve matching and scoring
* Improve documentation
* Split nautilus integration into its own project


1.1.1
^^^^^
**release date:** 2016-01-03

* Fix scanning videos on bad MKV files


1.1
^^^
**release date:** 2015-12-29

* Fix library usage example in README
* Fix for series name with special characters in addic7ed provider
* Fix id property in thesubdb provider
* Improve matching on titles
* Add support for nautilus context menu with translations
* Add support for searching subtitles in a separate directory
* Add subscenter provider
* Add support for python 3.5


1.0.1
^^^^^
**release date:** 2015-07-23

* Fix unicode issues in CLI (python 2 only)
* Fix score scaling in CLI (python 2 only)
* Improve error handling in CLI
* Color collect report in CLI


1.0
^^^
**release date:** 2015-07-22

* Many changes and fixes
* New test suite
* New documentation
* New CLI
* Added support for SubsCenter


0.7.5
^^^^^
**release date:** 2015-03-04

* Update requirements
* Remove BierDopje provider
* Add pre-guessed video optional argument in scan_video
* Improve hearing impaired support
* Fix TVSubtitles and Podnapisi providers


0.7.4
^^^^^
**release date:** 2014-01-27

* Fix requirements for guessit and babelfish


0.7.3
^^^^^
**release date:** 2013-11-22

* Fix windows compatibility
* Improve subtitle validation
* Improve embedded subtitle languages detection
* Improve unittests


0.7.2
^^^^^
**release date:** 2013-11-10

* Fix TVSubtitles for ambiguous series
* Add a CACHE_VERSION to force cache reloading on version change
* Set CLI default cache expiration time to 30 days
* Add podnapisi provider
* Support script for languages e.g. Latn, Cyrl
* Improve logging levels
* Fix subtitle validation in some rare cases


0.7.1
^^^^^
**release date:** 2013-11-06

* Improve CLI
* Add login support for Addic7ed
* Remove lxml dependency
* Many fixes


0.7.0
^^^^^
**release date:** 2013-10-29

**WARNING:** Complete rewrite of subliminal with backward incompatible changes

* Use enzyme to parse metadata of videos
* Use babelfish to handle languages
* Use dogpile.cache for caching
* Use charade to detect subtitle encoding
* Use pysrt for subtitle validation
* Use entry points for subtitle providers
* New subtitle score computation
* Hearing impaired subtitles support
* Drop async support
* Drop a few providers
* And much more...


0.6.4
^^^^^
**release date:** 2013-05-19

* Fix requirements due to enzyme 0.3


0.6.3
^^^^^
**release date:** 2013-01-17

* Fix requirements due to requests 1.0


0.6.2
^^^^^
**release date:** 2012-09-15

* Fix BierDopje
* Fix Addic7ed
* Fix SubsWiki
* Fix missing enzyme import
* Add Catalan and Galician languages to Addic7ed
* Add possible services in help message of the CLI
* Allow existing filenames to be passed without the ./ prefix


0.6.1
^^^^^
**release date:** 2012-06-24

* Fix subtitle release name in BierDopje
* Fix subtitles being downloaded multiple times
* Add Chinese support to TvSubtitles
* Fix encoding issues
* Fix single download subtitles without the force option
* Add Spanish (Latin America) exception to Addic7ed
* Fix group_by_video when a list entry has None as subtitles
* Add support for Galician language in Subtitulos
* Add an integrity check after subtitles download for Addic7ed
* Add error handling for if not strict in Language
* Fix TheSubDB hash method to return None if the file is too small
* Fix guessit.Language in Video.scan
* Fix language detection of subtitles


0.6.0
^^^^^
**release date:** 2012-06-16

**WARNING:** Backward incompatible changes

* Fix --workers option in CLI
* Use a dedicated module for languages
* Use beautifulsoup4
* Improve return types
* Add scan_filter option
* Add --age option in CLI
* Add TvSubtitles service
* Add Addic7ed service


0.5.1
^^^^^
**release date:** 2012-03-25

* Improve error handling of enzyme parsing


0.5
^^^
**release date:** 2012-03-25
**WARNING:** Backward incompatible changes

* Use more unicode
* New list_subtitles and download_subtitles methods
* New Pool object for asynchronous work
* Improve sort algorithm
* Better error handling
* Make sorting customizable
* Remove class Subliminal
* Remove permissions handling


0.4
^^^
**release date:** 2011-11-11

* Many fixes
* Better error handling


0.3
^^^
**release date:** 2011-08-18

* Fix a bug when series is not guessed by guessit
* Fix dependencies failure when installing package
* Fix encoding issues with logging
* Add a script to ease subtitles download
* Add possibility to choose mode of created files
* Add more checks before adjusting permissions


0.2
^^^
**release date:** 2011-07-11

* Fix plugin configuration
* Fix some encoding issues
* Remove extra logging


0.1
^^^
**release date:** *private release*

* Initial release
