# -*- coding: utf-8 -*-
# Copyright 2012 Nicolas Wack <wackou@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.

import logging

logger = logging.getLogger(__name__)


try:
    from bs4 import BeautifulSoup as bs4BeautifulSoup
    from bs4 import *

    def BeautifulSoup(*args, **kwargs):
        logger.debug('BS4 called with %s %s' % (args[1:], kwargs))
        text, parser = args
        if (parser == 'xml' or parser == ['lxml', 'xml']):
            # HACK: do not force xml, bierdopje won't work otherwise
            return bs4BeautifulSoup(args[0], 'lxml')
            #return bs4BeautifulSoup(*args, **kwargs)
        else:
            return bs4BeautifulSoup(*args, **kwargs)

    logger.debug('Imported BeautifulSoup4')

except ImportError:
    from BeautifulSoup import BeautifulSoup as bs3BeautifulSoup
    from BeautifulSoup import BeautifulStoneSoup as bs3BeautifulStoneSoup
    from BeautifulSoup import *

    def BeautifulSoup(*args, **kwargs):
        logger.debug('BS3 called with %s %s' % (args[1:], kwargs))
        text, parser = args
        if (parser == 'xml' or parser == ['lxml', 'xml']):
            return bs3BeautifulStoneSoup(text)
        else:
            return bs3BeautifulSoup(text)

    logger.debug('Imported BeautifulSoup3')
