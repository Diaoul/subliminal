Subliminal
==========
Subtitles, faster than your thoughts.

.. image:: https://img.shields.io/pypi/v/subliminal.svg
    :target: https://pypi.python.org/pypi/subliminal
    :alt: Latest Version

.. image:: https://readthedocs.org/projects/subliminal/badge/?version=latest
    :target: https://subliminal.readthedocs.org/
    :alt: Documentation Status

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Diaoul/subliminal/python-coverage-comment-action-data/endpoint.json
    :target: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Diaoul/subliminal/python-coverage-comment-action-data/endpoint.json
    :alt: Code coverage

.. image:: https://img.shields.io/github/license/Diaoul/subliminal.svg
    :target: https://github.com/Diaoul/subliminal/blob/master/LICENSE
    :alt: License

.. image:: https://img.shields.io/badge/discord-7289da.svg?style=flat-square&logo=discord
    :alt: Discord
    :target: https://discord.gg/kXW6sWte9N


:Project page: https://github.com/Diaoul/subliminal
:Documentation: https://subliminal.readthedocs.org/
:Community: https://discord.gg/kXW6sWte9N


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

    #!/usr/bin/env python

    from datetime import timedelta

    from babelfish import Language
    from subliminal import download_best_subtitles, region, save_subtitles, scan_videos

    # configure the cache
    region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})

    # scan for videos newer than 2 weeks and their existing subtitles in a folder
    videos = scan_videos('/video/folder', age=timedelta(weeks=2))

    # download best subtitles
    subtitles = download_best_subtitles(videos, {Language('eng'), Language('fra')})

    # save them to disk, next to the video
    for v in videos:
        save_subtitles(v, subtitles[v])

Docker
^^^^^^
Run subliminal in a docker container::

    $ docker run --rm --name subliminal -v subliminal_cache:/usr/src/cache -v /tvshows:/tvshows -it diaoulael/subliminal download -l en /tvshows/The.Big.Bang.Theory.S05E18.HDTV.x264-LOL.mp4

Installation
------------
For a better isolation with your system you should use a dedicated virtualenv.
The preferred installation method is to use `pipx <https://github.com/pypa/pipx>`_ that does that for you::

    $ pipx install subliminal

Subliminal can be also be installed as a regular python module by running::

    $ pip install --user subliminal

If you want to modify the code, `fork <https://github.com/Diaoul/subliminal/fork>`_ this repo,
clone your fork locally and install a development version::

    $ git clone https://github.com/<my-username>/subliminal
    $ cd subliminal
    $ pip install --user -e '.[dev,test,docs]'


Integrations
------------
Subliminal integrates with various desktop file managers to enhance your workflow:

- **Nautilus/Nemo**: See the dedicated `project page <https://github.com/Diaoul/nautilus-subliminal>`_ for more information.
- **Dolphin**: See this `Gist <https://gist.github.com/maurocolella/03a9f02c56b1a90c64f05683e2840d57>`_. for more details.

Contributing
------------
We welcome contributions from the community! If you're interested in contributing, here are a few ways you can get involved:

- **Browse Issues and Pull Requests**: Check out the existing `Issues <https://github.com/Diaoul/subliminal/issues>`_ and `Pull Requests <https://github.com/Diaoul/subliminal/pulls>`_ to see where you can help.
- **Report Bugs or Request Features**: If you encounter a bug or have a feature request, please create a GitHub Issue.
- **Follow the Contribution Guide**: For detailed instructions on how to contribute, please refer to our `Contribution Guide <https://github.com/Diaoul/subliminal/blob/main/CONTRIBUTING.md>`_.

Your contributions are greatly appreciated and help make this project better for everyone!
