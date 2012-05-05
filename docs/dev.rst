This guide is going to explain the main logic of subliminal and detail
every class or function.

Services
--------
Subliminal aims at downloading subtitles. Over the web, one can find subtitles
combining different websites but there is no guarantee of a perfect match.
Even if OpenSubtitles has a gigantic subtitles database, you may not be able to
find a subtitle on it but you will find it elsewhere, say BierDopje. Sometimes,
it just takes some time before it shows up on a website even if already available
on another, but you don't wanna wait to watch the latest Big Bang Theory, right?

Given this, to be reliable, subliminal has to use different :mod:`~subliminal.services`
and use a unified method to gather them all. The :class:`~subliminal.services.ServiceBase`
class will achieve this.

.. automodule:: subliminal.services
    :members:

Languages
---------
To be able to support many languages, subliminal uses :class:`guessit.Language`, refer
to guessit's documentation for more details.

Tasks
-----
Subliminal is IO bound: it mostly waits for IO operations (web requests) to complete.
Thus, subliminal is a good place for multi-threading. It works with atomic operations
represented by a :class:`~subliminal.tasks.Task` class which can be consumed with
:func:`~subliminal.core.consume_task` but we'll see that later.

.. automodule:: subliminal.tasks
    :members:

Asynchronous
------------
To consume those tasks in an asynchronous way without flooding services with requests,
subliminal uses multiple instances of the :class:`~subliminal.async.Worker` class that
will consume the same task queue. Each worker will only create a single instance of each
:mod:`service <subliminal.services>` and this save some initialization time.
The :class:`~subliminal.async.Pool` is here to instantiate and manage multiple workers
at a time.

.. automodule:: subliminal.async
    :members:

Core
----
The goal of subliminal's :mod:`~subliminal.core` module is to merge results from
consumed tasks. Merging has to be intelligent and take user preferences into account.
Core module is thus responsible for the computation of a :func:`matching confidence
<subliminal.core.matching_confidence>` so the user knows the chances that the
:class:`~subliminal.subtitles.ResultSubtitle` matches the :class:`~subliminal.videos.Video`

.. automodule:: subliminal.core
    :members:

Other objects
-------------
Subliminal uses some other self-explanatory functions and classes listed below.

Video
^^^^^

.. automodule:: subliminal.videos
    :members:

Subtitle
^^^^^^^^

.. automodule:: subliminal.subtitles
    :members:

Utilities
^^^^^^^^^

.. automodule:: subliminal.utils
    :members:

Exceptions
^^^^^^^^^^

.. automodule:: subliminal.exceptions
    :members:
