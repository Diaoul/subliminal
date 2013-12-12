Subliminal
==========

Subliminal is a python library to search and download subtitles.
It comes with an easy to use CLI (command-line interface) suitable for direct use or cron jobs.

.. image:: https://travis-ci.org/Diaoul/subliminal.png
    :target: https://travis-ci.org/Diaoul/subliminal

.. image:: https://coveralls.io/repos/Diaoul/subliminal/badge.png
    :target: https://coveralls.io/r/Diaoul/subliminal


Providers
---------
Subliminal uses multiple providers to give users a vast choice and have a better chance to find the
best matching subtitles. Providers are extensible through a dedicated entry point.

* Addic7ed
* OpenSubtitles
* Podnapisi
* TheSubDB
* TvSubtitles


Usage
-----
CLI
^^^
Download english subtitles::

    $ subliminal -l en -- The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4
    1 subtitle downloaded

Library
^^^^^^^
Download best subtitles in French and English for videos less than one week old in a video folder,
skipping videos that already have subtitles whether they are embedded or not::

    from __future__ import unicode_literals  # python 2 only
    from babelfish import Language
    from datetime import timedelta
    import subliminal
    
    # configure the cache
    subliminal.cache_region.configure('dogpile.cache.dbm', arguments={'filename': '/path/to/cachefile.dbm'})

    # scan for videos in the folder and their subtitles
    videos = subliminal.scan_videos(['/path/to/video/folder'], subtitles=True, embedded_subtitles=True, age=timedelta(weeks=1))

    # download
    subliminal.download_best_subtitles(videos, {Language('eng'), Language('fra')}, age=timedelta(weeks=1))


License
-------
MIT
