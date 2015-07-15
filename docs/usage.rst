Usage
=====
CLI
---
Download English subtitles::

    $ subliminal download -l en The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4
    Collecting videos  [####################################]  100%
    1 video collected / 0 video ignored
    Downloading subtitles  [####################################]  100%
    Downloaded 1 subtitle

See :ref:`cli` for more details on the available commands and options.

Library
-------
Download best subtitles in French and English for videos less than two weeks old in a video folder,
skipping videos that already have subtitles::

    from datetime import timedelta

    from babelfish import Language
    from subliminal import download_best_subtitles, region, save_subtitles, scan_videos

    # configure the cache
    region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})

    # scan for videos newer than 2 weeks and their existing subtitles in a folder
    videos = [v for v in scan_videos('/video/folder', subtitles=True, embedded_subtitles=True)
              if v.age < timedelta(weeks=2)]

    # download best subtitles
    subtitles = download_best_subtitles(videos, {Language('eng'), Language('fra')})

    # save them to disk, next to the video
    save_subtitles(subtitles)

See :mod:`subliminal.api` and :mod:`subliminal.video` for more details about each function used.
