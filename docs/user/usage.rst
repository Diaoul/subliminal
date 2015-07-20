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

.. warning::

    For cron usage, make sure to specify a maximum age (with ``--age``) so subtitles are searched for recent videos
    only. Otherwise you will get banned from the providers for abuse due to too many requests. If subliminal didn't
    find subtitles for an old video, it's unlikely it will find subtitles for that video ever anyway.

See :ref:`cli` for more details on the available commands and options.


High level API
--------------
You can call subliminal in many different ways depending on how much control you want over the process. For most use
cases, you can stick to the standard API.

Common
^^^^^^
Let's start by importing subliminal:

    >>> from __future__ import unicode_literals
    >>> import os
    >>> from babelfish import *
    >>> from subliminal import *

Before going further, there are a few things to know about subliminal.

Video
^^^^^
The :class:`~subliminal.video.Movie` and :class:`~subliminal.video.Episode` classes represent a video,
existing or not. You can create a video by name (or path) with :meth:`Video.fromname <subliminal.video.Video.fromname>`,
use :func:`~subliminal.video.scan_video` on an existing file path to get even more information about the video or
use :func:`~subliminal.video.scan_videos` on an existing directory path to scan a whole directory for videos.

    >>> video = Video.fromname('The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4')
    >>> video
    <Episode ['The Big Bang Theory', 5x18]>

Here video informations were guessed based on the name of the video, you can access some video attributes:

    >>> video.video_codec
    'h264'
    >>> video.release_group
    'LOL'

Configuration
^^^^^^^^^^^^^
Before proceeding to listing and downloading subtitles, you need to configure the cache. Subliminal uses a cache to
reduce repeated queries to providers and improve overall performance with no impact on search quality. For the sake
of this example, we're going to use a memory backend.

    >>> my_region = region.configure('dogpile.cache.memory')

.. warning::

    Choose a cache that fits your application and prefer persistant over volatile backends. The ``file`` backend is
    usually a good choice.
    See `dogpile.cache's documentation <http://dogpilecache.readthedocs.org>`_ for more details on backends.

Now that we're done with the basics, let's have some *real* fun.

Listing
^^^^^^^
To list subtitles, subliminal provides a :func:`~subliminal.api.list_subtitles` function that will return all found
subtitles:

    >>> subtitles = list_subtitles([video], {Language('hun')}, providers=['podnapisi'])
    >>> subtitles[video]
    [<PodnapisiSubtitle 'ZtAW' [hu]>, <PodnapisiSubtitle 'ONAW' [hu]>]

.. note::

    As you noticed, all parameters are iterables but only contain one item which means you can deal with a lot of
    videos, languages and providers at the same time. For the sake of this example, we filter providers to use only one,
    pass ``providers=None`` (default) to search on all providers.

Scoring
^^^^^^^
It's usual you have multiple candidates for subtitles. To help you chose which one to download, subliminal can compare
them to the video and tell you exactly what matches with :meth:`~subliminal.subtitle.Subtitle.get_matches`:

    >>> for s in subtitles[video]:
    ...     sorted(s.get_matches(video))
    ['episode', 'format', 'hearing_impaired', 'release_group', 'season', 'series', 'video_codec', 'year']
    ['episode', 'format', 'hearing_impaired', 'season', 'series', 'year']

And then compute a score with those matches with :func:`~subliminal.subtitle.compute_score`:

    >>> for s in subtitles[video]:
    ...     {s: compute_score(s.get_matches(video), video)}
    {<PodnapisiSubtitle 'ZtAW' [hu]>: 132}
    {<PodnapisiSubtitle 'ONAW' [hu]>: 117}

Now you should have a better idea about which one you should choose.

Downloading
^^^^^^^^^^^
We can settle on the first subtitle and download its content using :func:`~subliminal.api.download_subtitles`:

    >>> subtitle = subtitles[video][0]
    >>> subtitle.content is None
    True
    >>> download_subtitles([subtitle])
    >>> subtitle.content.split(b'\n')[2]
    b'Elszaladok a boltba'

If you want a string instead of bytes, you can access decoded content with the
:attr:`~subliminal.subtitle.Subtitle.text` property:

    >>> subtitle.text.split('\n')[3]
    'néhány apróságért.'

Downloading best subtitles
^^^^^^^^^^^^^^^^^^^^^^^^^^
Downloading best subtitles is what you want to do in almost all cases, as a shortcut for listing, scoring and
downloading you can use :func:`~subliminal.api.download_best_subtitles`:

    >>> best_subtitles = download_best_subtitles([video], {Language('hun')}, providers=['podnapisi'])
    >>> best_subtitles[video]
    [<PodnapisiSubtitle 'ZtAW' [hu]>]
    >>> best_subtitle = best_subtitles[video][0]
    >>> best_subtitle.content.split(b'\n')[2]
    b'Elszaladok a boltba'

We end up with the same subtitle but with one line of code. Neat.

Save
^^^^
We got ourselves a nice subtitle now we can save it on the file system using :func:`~subliminal.api.save_subtitles`:

    >>> save_subtitles(video, [best_subtitle])
    [<PodnapisiSubtitle 'ZtAW' [hu]>]
    >>> os.listdir()
    ['The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.hu.srt']
