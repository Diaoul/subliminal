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

    def update_obj_bs4_api(o):
        o.replace_with = o.replaceWith
        o.replace_with_children = o.replaceWithChildren
        o.find_all = o.findAll
        o.find_all_next = o.findAllNext
        o.find_all_previous = o.findAllPrevious
        o.find_next = o.findNext
        o.find_next_sibling = o.findNextSibling
        o.find_next_siblings = o.findNextSiblings
        o.find_parent = o.findParent
        o.find_parents = o.findParents
        o.find_previous = o.findPrevious
        o.find_previous_sibling = o.findPreviousSibling
        o.find_previous_siblings = o.findPreviousSiblings
        #o.next_sibling = o.nextSibling
        #o.previous_sibling = o.previousSibling
        return o

    update_obj_bs4_api(BeautifulSoup)
    update_obj_bs4_api(BeautifulStoneSoup)
    update_obj_bs4_api(Tag)

    def BeautifulSoup(*args, **kwargs):
        logger.debug('BS3 called with %s %s' % (args[1:], kwargs))
        text, parser = args
        if (parser == 'xml' or parser == ['lxml', 'xml']):
            bs3 = bs3BeautifulStoneSoup(text)
        else:
            bs3 = bs3BeautifulSoup(text)

        return update_obj_bs4_api(bs3)

    logger.debug('Imported BeautifulSoup3')
