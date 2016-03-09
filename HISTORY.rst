Changelog
---------

1.2
^^^
**release date:** *not released*


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
