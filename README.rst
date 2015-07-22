Subliminal
==========
Subtitles, faster than your thoughts.

.. image:: https://img.shields.io/pypi/v/subliminal.svg
    :target: https://pypi.python.org/pypi/subliminal
    :alt: Latest Version

.. image:: https://travis-ci.org/Diaoul/subliminal.svg?branch=master
   :target: https://travis-ci.org/Diaoul/subliminal
   :alt: Travis CI build status

.. image:: https://readthedocs.org/projects/subliminal/badge/?version=latest
   :target: https://subliminal.readthedocs.org/
   :alt: Documentation Status

.. image:: https://coveralls.io/repos/Diaoul/subliminal/badge.svg?branch=master&service=github
   :target: https://coveralls.io/github/Diaoul/subliminal?branch=master
   :alt: Code coverage

.. image:: https://img.shields.io/github/license/Diaoul/subliminal.svg
   :target: https://github.com/Diaoul/subliminal/blob/master/LICENSE
   :alt: License


:Project page: https://github.com/Diaoul/subliminal
:Documentation: https://subliminal.readthedocs.org/


Usage
-----
CLI
^^^
Download English subtitles::

    $ subliminal download -l en The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4
    Collecting videos  [####################################]  100%
    1 video collected / 0 video ignored / 0 error
    Downloading subtitles  [####################################]  100%
    Downloaded 1 subtitle

Library
^^^^^^^
Download best subtitles in French and English for videos less than two weeks old in a video folder:

.. code:: python

    from datetime import timedelta
    
    from babelfish import Language
    from subliminal import download_best_subtitles, region, save_subtitles, scan_videos
    
    # configure the cache
    region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})
    
    # scan for videos newer than 2 weeks and their existing subtitles in a folder
    videos = [v for v in scan_videos('/video/folder') if v.age < timedelta(weeks=2)]
    
    # download best subtitles
    subtitles = download_best_subtitles(videos, {Language('eng'), Language('fra')})
    
    # save them to disk, next to the video
    save_subtitles(subtitles)
