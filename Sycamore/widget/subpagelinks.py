# -*- coding: utf-8 -*-
"""
    Sycamore - sub page title rendering widget

    This will take a string, such as "Front Page/Things to do/Fun stuff" and break it into logical subpage links. 

    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore.widget import base
from Sycamore.Page import Page

class SubpageLinks(base.Widget):
    def __init__(self, request, pagename):
        self.pagename = pagename
        base.Widget.__init__(self, request)

    def _subpages(self):
        possible_subpages = self.pagename.split('/') 
        max_number_possible = len(possible_subpages)
        n = 1
        pagelinks = []
        pagenames_queue = []
        while n <= max_number_possible:
            pagename = possible_subpages[-n]
            parent_pagename = '/'.join(possible_subpages[:-n])
            parent_page = Page(parent_pagename, self.request)
            pagenames_queue.append(pagename)
            if parent_page.exists() or parent_page.page_name == 'users':
                pagenames_queue.reverse()
                display_name = '/'.join(pagenames_queue)
                pagelinks.append(
                    ('%s/%s' % (parent_pagename, display_name), display_name))
                pagenames_queue = []

            n += 1

        pagenames_queue.reverse()
        pagelinks.append(('/'.join(pagenames_queue), '/'.join(pagenames_queue)))
        pagelinks.reverse()
        return pagelinks

    def render(self):
        """
        Returns a list of tuples [ .. (pagename, display_pagename), ... ] 
        """
        return self._subpages()
