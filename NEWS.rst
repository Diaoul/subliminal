News
====

0.6.3
-----
**release date:** 2013-01-17

* Fix requirements due to requests 1.0

0.6.2
-----
**release date:** 2012-09-15

* Fix BierDopje
* Fix Addic7ed
* Fix SubsWiki
* Fix missing enzyme import
* Add Catalan and Galician languages to Addic7ed
* Add possible services in help message of the CLI
* Allow existing filenames to be passed without the ./ prefix

0.6.1
-----
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
-----
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
-----
**release date:** 2012-03-25

* Improve error handling of enzyme parsing

0.5
---
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
---
**release date:** 2011-11-11

* Many fixes
* Better error handling

0.3
---
**release date:** 2011-08-18

* Fix a bug when series is not guessed by guessit
* Fix dependencies failure when installing package
* Fix encoding issues with logging
* Add a script to ease subtitles download
* Add possibility to choose mode of created files
* Add more checks before adjusting permissions

0.2
---
**release date:** 2011-07-11

* Fix plugin configuration
* Fix some encoding issues
* Remove extra logging

0.1
---
**release date:** not released yet

* Initial release
