.. _cli:

CLI
===

subliminal
----------
.. code-block:: none

    $ subliminal --help
    Usage: subliminal [OPTIONS] COMMAND [ARGS]...

      Subtitles, faster than your thoughts.

    Options:
      --addic7ed USERNAME PASSWORD  Addic7ed configuration.
      --cache-dir DIRECTORY         Path to the cache directory.  [default:
                                    ~/.config/subliminal]
      --debug                       Print useful information for debugging subliminal and for
                                    reporting bugs.
      --version                     Show the version and exit.
      --help                        Show this message and exit.

    Commands:
      cache     Cache management.
      download  Download best subtitles.

      Suggestions and bug reports are greatly appreciated: https://github.com/Diaoul/subliminal/


subliminal download
-------------------
.. code-block:: none

    $ subliminal download --help
    Usage: subliminal download [OPTIONS] PATH...

      Download best subtitles.

      PATH can be an directory containing videos, a video file path or a video file name. It can be
      used multiple times.

      If an existing subtitle is detected (external or embedded) in the correct language, the
      download is skipped for the associated video.

    Options:
      -l, --language LANGUAGE         Language as IETF code, e.g. en, pt-BR (can be used multiple
                                      times).  [required]
      -p, --provider [addic7ed|opensubtitles|podnapisi|thesubdb|tvsubtitles]
                                      Provider to use (can be used multiple times).
      -a, --age AGE                   Filter videos newer than AGE, e.g. 12h, 1w2d.
      -d, --directory DIR             Directory where to save subtitles, default is next to the video
                                      file.
      -e, --encoding ENC              Subtitle file encoding, default is to preserve original
                                      encoding.
      -s, --single                    Save subtitle without language code in the file name, i.e. use
                                      .srt extension.
      -f, --force                     Force download even if a subtitle already exist.
      -hi, --hearing-impaired         Prefer hearing impaired subtitles.
      -m, --min-score INTEGER RANGE   Minimum score for a subtitle to be downloaded (0 to 100).
      -v, --verbose                   Increase verbosity.
      --help                          Show this message and exit.


subliminal cache
----------------
.. code-block:: none

    $ subliminal cache --help
    Usage: subliminal cache [OPTIONS]

      Cache management.

    Options:
      --clear-subliminal  Clear subliminal's cache. Use this ONLY if your cache is corrupted or if
                          you experience issues.
      --help              Show this message and exit.
