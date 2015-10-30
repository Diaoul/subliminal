Examples
========
This directory contains various examples, UI files and translations files.
Refer to subliminal's main README for install instructions.

Translations
------------
This is how to generate the po template file::

    # extract strings from ui files
    intltool-extract --type=gettext/glade ui/config.glade
    intltool-extract --type=gettext/glade ui/choose.glade

    # generate subliminal.pot
    xgettext -k_ -kN_ -w 120 --from-code=utf-8 -o i18n/subliminal.pot ui/config.glade.h ui/choose.glade.h nautilus.py

    # clean up
    rm ui/*.h
