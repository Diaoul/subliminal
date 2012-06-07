There are 4 different ways of using subliminal and each one
is described in a dedicated section below.

First, here are some basics

Basics
------
Services
^^^^^^^^
You can use subliminal with multiple services to get the best result.
Current available services are available in the :data:`subliminal.SERVICES` variable.

.. autodata:: subliminal.SERVICES

Languages
^^^^^^^^^
Subliminal supports multiple languages that are represented with their extended ISO 639-1 code.
The current extensions to the ISO 639-1 are:

* *pb* for Portuguese Brazilian

Paths
^^^^^
All paths parameters in subliminal most commont functions can be either *a file path*,
*a file name* or a *folder path*

* File path (existing): hashes of the file will be computed and used during the search for services that supports
  this functionnality.
* File name (or non-existing file path): the guessit python library will be used to guess informations and a text-based search will
  be done with services.
* Folder path (containing video files): the given folder will be searched for video files using their :data:`~subliminal.videos.MIMETYPES`
  and/or :data:`~subliminal.videos.EXTENSIONS`. The default maximum depth to scan is 3

CLI
---
Subliminal is shipped with a Command Line Interface that allows you to
download subtitles for one or more videos in a multithreaded way.

.. note::

    The cache directory defaults to *~/.config/subliminal*. Even on Windows

Usage
^^^^^
You can have the documentation of the CLI using ``subliminal --help``::

    usage: subliminal [-h] [-l LG] [-s NAME] [-m] [-f] [-w N] [-a AGE] [-c]
                      [-q | -v] [--cache-dir DIR | --no-cache-dir] [--version]
                      PATH [PATH ...]

    Subtitles, faster than your thoughts

    positional arguments:
      PATH                  path to video file or folder

    optional arguments:
      -h, --help            show this help message and exit
      -l LG, --language LG  wanted language (ISO 639-1)
      -s NAME, --service NAME
                            service to use
      -m, --multi           download multiple subtitle languages
      -f, --force           replace existing subtitle file
      -w N, --workers N     use N threads (default: 4)
      -a AGE, --age AGE     scan only for files newer or older (prefix with +)
                            than AGE (e.g. 12h, 1w2d, +3d6h)
      -c, --compatibility   try not to use unicode (use this if you have encoding
                            errors)
      -q, --quiet           disable output
      -v, --verbose         verbose output
      --cache-dir DIR       cache directory to use
      --no-cache-dir        do not use cache directory (some services may not
                            work)
      --version             show program's version number and exit

Cron job
^^^^^^^^
This CLI is well suited for automatic subtitles downloads. For example, to download english and french
subtitles for videos newer than one week under /path/to/videos/ each day at 1:00AM with a single worker,
you can use the following crontab line::

    0 1 * * * user /path/to/subliminal -m -l en -l fr -w 1 -a 1w -q /path/to/videos/

Simple module use
-----------------
Subliminal comes with two basic functions to search and download subtitles. For example, you
can do::

    >>> subliminal.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])

.. autofunction:: subliminal.list_subtitles

Or even download missing subtitles for each episodes under the given folders in two different languages::

    >>> subliminal.download_subtitles(['/mnt/videos/BBT/Season 05', '/mnt/videos/HIMYM/Season 07'],
    ...                               ['en', 'fr'], force=False, multi=True)

.. autofunction:: subliminal.download_subtitles

Multi-threaded module use
-------------------------
You can call the same functions on a :class:`subliminal.Pool` object previously
created with the appropriate number of workers.

.. autoclass:: subliminal.Pool
    :members:

You have to call the :meth:`~subliminal.Pool.start` method before any actions and
:meth:`~subliminal.Pool.stop` before exiting your program::

    >>> p = subliminal.Pool(4)
    ... p.start()
    ... p.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])
    ... p.stop()

To make the use of :class:`~subliminal.Pool` easier, you can use the ``with`` statement
that takes care of that for you::

    >>> with subliminal.Pool(4) as p:
    ...     p.list_subtitles('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4', ['en'])


* from the command line
* basic functions :func:`~subliminal.list_subtitles` and :func:`~subliminal.download_subtitles`
* multi-threaded :class:`~subliminal.async.Pool` which implements the abovementioned functions
* using your own algorithm that produces and gather results of elementary :class:`~subliminal.tasks.Task`
