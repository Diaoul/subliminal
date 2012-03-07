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

Tasks
-----
Subliminal is IO bound, it mostly waits for IO operations than for CPU. Thus, subliminal
is a good place for multi-threading.
