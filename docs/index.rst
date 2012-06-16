.. subliminal documentation master file, created by
   sphinx-quickstart on Tue Feb 28 16:33:06 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Subliminal
==========
Release v\ |version|

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
* Podnapisi
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

Module
^^^^^^
List english subtitles::

	>>> subliminal.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])

Multi-threaded use
^^^^^^^^^^^^^^^^^^
Use 4 workers to achieve the same result::

	>>> with subliminal.Pool(4) as p:
	... 	p.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])

User Guide
----------
This part of the documentation details how to use subliminal for most common tasks

.. toctree::
   :maxdepth: 2
   
   user

Developer Guide
---------------
This part of the documentation explains internal behavior of subliminal and its algorithms

.. toctree::
   :maxdepth: 2
   
   dev


API Documentation
-----------------
Most common subliminal features are listed here

.. automodule:: subliminal
    :members:
    :noindex:
