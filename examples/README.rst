Examples
========
This directory contains various examples, UI files and translations files.
Refer to subliminal's main README for install instructions.

Translations
------------
This is how to generate the po template file::

    # generate .pot files
    intltool-extract --type=gettext/glade ui/config.glade
    xgettext -k_ -kN_ -o i18n/config_messages.pot ui/config.glade.h
    intltool-extract --type=gettext/glade ui/choose.glade
    xgettext -k_ -kN_ -o i18n/choose_messages.pot ui/choose.glade.h
    xgettext -k_ -kN_ -o i18n/nautilus_messages.pot nautilus.py

    # concatenate in one .pot file
    msgcat --use-first i18n/*.pot -o i18n/subliminal.pot

    # clean up
    rm ui/*.h i18n/*.pot
