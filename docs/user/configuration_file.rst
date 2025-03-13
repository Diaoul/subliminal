.. _configuration-file:

Configuration file
==================

The `TOML <https://toml.io/en/>`_ format is used for the configuration file.
The path of the configuration file to use can be specified with the ``--config/-c``
option in the :ref:`cli`.

Sections
--------

The configuration file supports different sections or tables:

    - a ``[default]`` table, corresponding to the options of the :ref:`cli-subliminal-download` command.

    - ``[refiner.<refiner_name>]`` and ``[provider.<provider_name>]`` tables to specify refiner and provider options.

    - tables for each CLI sub-commands: ``[cache]``, ``[download]``.

Each CLI option can be specified in the configuration file, even mandatory options
like ``--language`` for the :ref:`cli-subliminal-download` sub-command.
CLI arguments (like ``path``) cannot be specified in the configuration file.

Options that can be used multiple times (like ``--language``) need to be defined as arrays.


Example
-------

An example of configuration file:

.. literalinclude:: ../config.toml
    :language: toml
