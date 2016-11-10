How it works
============

Providers
---------
Subliminal uses multiple providers to give users a vast choice and have a better chance to find the best matching
subtitles. Current supported providers are:

* Addic7ed
* LegendasTV
* NapiProjekt
* OpenSubtitles
* Podnapisi
* Shooter
* TheSubDB
* TvSubtitles

Providers all inherit the same :class:`~subliminal.providers.Provider` base class and thus share the same API.
They are registered on the ``subliminal.providers`` entry point and are exposed through the
:data:`~subliminal.extensions.provider_manager` for easy access.

To work with multiple providers seamlessly, the :class:`~subliminal.core.ProviderPool` exposes the same API but
distributes it to its providers and :class:`~subliminal.core.AsyncProviderPool` does it asynchronously.

.. _scoring:

Scoring
-------
Rating subtitles and comparing them is probably the most difficult part and this is where subliminal excels with its
powerful scoring algorithm.

Using `guessit <http://guessit.readthedocs.org>`_ and `enzyme <http://enzyme.readthedocs.org>`_, subliminal extracts
properties of the video and match them with the properties of the subtitles found with the providers.

Equations in :mod:`subliminal.score` give a score to each property (called a match). The more matches the video and
the subtitle have, the higher the score computed with :func:`~subliminal.score.compute_score` gets.


Libraries
---------
Various libraries are used by subliminal and are key to its success:

* `guessit <http://guessit.readthedocs.org>`_ to guess information from filenames
* `enzyme <http://enzyme.readthedocs.org>`_ to detect embedded subtitles in videos and read other video metadata
* `babelfish <http://babelfish.readthedocs.org>`_ to work with languages
* `requests <http://docs.python-requests.org>`_ to make human readable HTTP requests
* `BeautifulSoup <http://www.crummy.com/software/BeautifulSoup>`_ to parse HTML and XML
* `dogpile.cache <http://dogpilecache.readthedocs.org>`_ to cache intermediate search results
* `stevedore <http://docs.openstack.org/developer/stevedore/>`_ to manage the provider entry point
* `chardet <http://chardet.readthedocs.org>`_ to detect subtitles' encoding
* `pysrt <https://github.com/byroot/pysrt>`_ to validate downloaded subtitles
