.. subliminal documentation master file, created by
   sphinx-quickstart on Wed Oct 23 23:24:28 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Subliminal
==========
Release v\ |release|

Subliminal is a python library to search and download subtitles.
It comes with an easy to use :abbr:`CLI (command-line interface)` suitable for direct use or cron jobs.


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

See :mod:`subliminal.cli`

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

    # download best subtitles
    subtitles = subliminal.download_best_subtitles(videos, {Language('eng'), Language('fra')}, age=timedelta(weeks=1))

    # save them to disk, next to the video
    subliminal.save_subtitles(subtitles)

See :mod:`subliminal.api`, :func:`~subliminal.video.scan_videos` and :func:`~subliminal.video.scan_video`

How it works
------------
Subliminal makes use of various libraries to achieve its goal:

* `enzyme <http://enzyme.readthedocs.org>`_ to detect embedded subtitles in videos and retrieve metadata
* `guessit <http://guessit.readthedocs.org>`_ to guess informations from filenames
* `babelfish <http://babelfish.readthedocs.org>`_ to work with languages
* `requests <http://docs.python-requests.org>`_ to make human readable HTTP requests
* `BeautifulSoup <http://www.crummy.com/software/BeautifulSoup>`_ to parse HTML and XML
* `dogpile.cache <http://dogpilecache.readthedocs.org>`_ to cache intermediate search data
* `charade <https://github.com/sigmavirus24/charade>`_ to detect subtitles' encoding
* `pysrt <https://github.com/byroot/pysrt>`_ to validate downloaded subtitles


License
-------
MIT


Documentation
-------------
.. toctree::
    :maxdepth: 2

    provider_guide


API Documentation
-----------------
If you are looking for information on a specific function, class or method,
this part of the documentation is for you.

.. toctree::
    :maxdepth: 2

    api/api
    api/cache
    api/cli
    api/exceptions
    api/providers
    api/score
    api/subtitle
    api/video


.. include:: ../HISTORY.rst
