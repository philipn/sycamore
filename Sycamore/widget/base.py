# -*- coding: utf-8 -*-
"""
    Sycamore - Widget base class

    @copyright: 2002 by J�rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

class Widget:
    def __init__(self, request, **kw):
        self.request = request

    def render(self):
        raise NotImplementedError 
