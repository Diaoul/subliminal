CLI
===
.. module:: subliminal.cli

subliminal
----------
.. code-block:: none

    usage: subliminal -l LANGUAGE [LANGUAGE ...] [-s] [-c CACHE_FILE]
                      [-p PROVIDER [PROVIDER ...]] [-m MIN_SCORE] [-a AGE] [-h]
                      [-f] [--addic7ed-username USERNAME]
                      [--addic7ed-password PASSWORD] [-q | -v]
                      [--log-file LOG_FILE] [--color] [--debug] [--version]
                      [--help]
                      PATH [PATH ...]

    Subtitles, faster than your thoughts

    required arguments:
      PATH                  path to video file or folder
      -l LANGUAGE [LANGUAGE ...], --languages LANGUAGE [LANGUAGE ...]
                            wanted languages as IETF codes e.g. fr, pt-BR, sr-Cyrl

    configuration:
      -s, --single          download without language code in subtitle's filename
                            i.e. .srt only
      -c CACHE_FILE, --cache-file CACHE_FILE
                            cache file (default: ~/.config/subliminal.cache.dbm)

    filtering:
      -p PROVIDER [PROVIDER ...], --providers PROVIDER [PROVIDER ...]
                            providers to use (opensubtitles, thesubdb, podnapisi,
                            addic7ed, tvsubtitles)
      -m MIN_SCORE, --min-score MIN_SCORE
                            minimum score for subtitles (0-71 for episodes, 0-31
                            for movies)
      -a AGE, --age AGE     download subtitles for videos newer than AGE e.g. 12h,
                            1w2d
      -h, --hearing-impaired
                            download hearing impaired subtitles
      -f, --force           force subtitle download for videos with existing
                            subtitles

    addic7ed:
      --addic7ed-username USERNAME
                            username for addic7ed provider
      --addic7ed-password PASSWORD
                            password for addic7ed provider

    output:
      -q, --quiet           disable output
      -v, --verbose         verbose output
      --log-file LOG_FILE   log into a file instead of stdout
      --color               add color to console output (requires colorlog)

    troubleshooting:
      --debug               debug output
      --version             show program's version number and exit
      --help                show this help message and exit

    Suggestions and bug reports are greatly appreciated:
    https://github.com/Diaoul/subliminal/issues

