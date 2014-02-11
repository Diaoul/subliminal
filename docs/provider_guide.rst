Provider Guide
==============
This guide is going to explain how to add a :class:`~subliminal.providers.Provider` to subliminal


Requirements
------------
When starting a provider you should be able to answer to the following questions:

* What languages does my provider support?
* What are the language codes for the supported languages?
* Does my provider deliver subtitles for episodes? for movies?
* Does my provider require a video hash?

Each response of these questions will help you set the correct attributes for your
:class:`~subliminal.providers.Provider`.


Video Validation
----------------
Not all providers deliver subtitles for :class:`~subliminal.video.Episode`. Some may require a hash.
The :meth:`~subliminal.providers.Provider.check` method does validation against a :class:`~subliminal.video.Video`
object and will return `False` if the given :class:`~subliminal.video.Video` isn't suitable. If you're not happy
with the default implementation, you can override it.


Configuration
-------------
API keys must not be configurable by the user and must remain linked to subliminal. Hence they must be written
in the provider module.

Per-user authentication is allowed and must be configured at instantiation as keyword arguments. Configuration
will be done by the user through the `provider_configs` argument of the :func:`~subliminal.api.list_subtitles` and
:func:`~subliminal.api.download_best_subtitles` functions. No network operation must be done during instantiation,
only configuration. Any error in the configuration must raise a
:class:`~subliminal.exceptions.ConfigurationError`.


Beyond this point, if an error occurs, a generic :class:`~subliminal.exceptions.ProviderError` exception 
must be raised. You can also use more explicit exception classes :class:`~subliminal.exceptions.AuthenticationError`
and :class:`~subliminal.exceptions.DownloadLimitExceeded`.


Initialization / Termination
----------------------------
Actual authentication operations must take place in the :meth:`~subliminal.providers.Provider.initialize` method.
If you need anything to be executed when the provider isn't used anymore like logout,
use :meth:`~subliminal.providers.Provider.terminate`.


Caching policy
--------------
To save bandwidth and improve querying time, intermediate data should be cached when possible. Typical use case is
when a query to retrieve show ids is required prior to the query to actually search for subtitles. In that case
the function that gets the show id from the show name must be cached.
Expiration time should be :data:`~subliminal.cache.SHOW_EXPIRATION_TIME` for shows and
:data:`~subliminal.cache.EPISODE_EXPIRATION_TIME` for episodes.


Language
--------
To be able to handle various language codes, subliminal makes use of `babelfish <http://babelfish.readthedocs.org>`_
Language and converters. You must set the attribute :attr:`~subliminal.providers.Provider.languages` with a set of
supported :class:`babelfish.Language`.

If you cannot find a suitable converter for your provider, you can `make one of your own
<http://babelfish.readthedocs.org/en/latest/#custom-converters>`_.


Querying
--------
The :meth:`~subliminal.providers.Provider.query` method parameters must include all aspects of provider's querying with
simple types.


Subtitle
--------
A custom :class:`~subliminal.subtitle.Subtitle` subclass must be created to represent a subtitle from the provider.
It must have relevant attributes that can be used to compute the matches of the subtitle against a
:class:`~subliminal.video.Video` object.


Score computation
-----------------

To be able to compare subtitles coming from different providers between them, the
:meth:`~subliminal.subtitle.Subtitle.compute_matches` method must be implemented.
If `guessit <http://guessit.readthedocs.org>`_ is used to extract data from the
:class:`~subliminal.subtitle.Subtitle` subclass, you can use :func:`~subliminal.subtitle.compute_guess_matches`
as a helper to compute matches between the :class:`~subliminal.video.Video` and the :class:`guessit.Guess`.

Refer to the `scores` attribute of  :class:`~subliminal.video.Episode` and :class:`~subliminal.video.Movie`
for a list of possible matches.


Unittesting
-----------
All possible uses of the :meth:`~subliminal.providers.Provider.query` method must be unittested.
The :meth:`~subliminal.subtitle.Subtitle.compute_matches` is used to validate the unittests.

As it is not possible to unittest all uses of the :meth:`~subliminal.providers.Provider.list_subtitles`
and :meth:`~subliminal.providers.Provider.download_subtitle` methods, unitests are only required to cover most common
use cases.

See existing unittests for more details on how to proceed.
