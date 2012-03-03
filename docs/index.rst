.. subliminal documentation master file, created by
   sphinx-quickstart on Tue Feb 28 16:33:06 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Introduction
============
Release v\ |version|
Subtitles, faster than your thoughts!

Subliminal aims at finding the best subtitles for your video

Example
=======
You can use all subliminal functionalities with:

* a video file path
* a video file name
* a folder

CLI
---
Download subtitles from a video file or folder or directly from a filename::

    $ subliminal -l en The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4

Module
------
List english subtitles::

	>>> subliminal.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])

Multi-threaded use
------------------
Use 4 workers to achieve the same result::

	>>> with subliminal.Pool(4) as p:
	... 	p.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])

API Documentation
=================
Services
--------
.. automodule:: subliminal.services
    :member-order: bysource
    :members:

Core
----
.. automodule:: subliminal.core
    :members:

Videos
------
.. automodule:: subliminal.videos
    :members:

Subtitles
---------
.. automodule:: subliminal.subtitles
    :members:
