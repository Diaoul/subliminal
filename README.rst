Subliminal
==========

.. image:: https://secure.travis-ci.org/Diaoul/subliminal.png?branch=develop

Subliminal is a python library to search and download subtitles.

It uses video hashes and the powerful `guessit <http://guessit.readthedocs.org/>`_ library
that extracts informations from filenames or filepaths to ensure you have the best subtitles.
It also relies on `enzyme <https://github.com/Diaoul/enzyme>`_ to detect embedded subtitles
and avoid duplicates.

Features
--------
Multiple subtitles services are available:

* Addic7ed
* BierDopje
* OpenSubtitles
* SubsWiki
* Subtitulos
* TheSubDB
* TvSubtitles

You can use main subliminal's functions with a **file path**, a **file name** or a **folder path**.

CLI
^^^
Download english subtitles::

    $ subliminal -l en The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4
    **************************************************
    Downloaded 1 subtitle(s) for 1 video(s)
    The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.srt from opensubtitles
    **************************************************

Example of configuration file ~/.config/subliminal/config::

    [subliminal]
    outputstyle = quiet     
    workers = 4
    compatibilitymode = False
    languages = fi,en
    cachedir = ~/.config/subliminal
    forceoverwrite = False
    services = opensubtitles,subswiki,thesubdb,addic7ed,tvsubtitles
    multisubs = True

Valid Values::

    outputstyle       (quiet|verbose)
    workers           (any integer value)
    compatibilitymode (True|False)
    forceoverwrite    (True|False)
    multisubs         (True|False)
    languages         (comma separated list of valid languages)
    services          (comma separated list of valid services)
    cachedir          (any directory where user has access to)


Module
^^^^^^
List english subtitles::

    >>> subliminal.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])

Multi-threaded use
^^^^^^^^^^^^^^^^^^
Use 4 workers to achieve the same result::

    >>> with subliminal.Pool(4) as p:
    ...     p.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])
