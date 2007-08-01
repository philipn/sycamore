# -*- coding: utf-8 -*-
"""
    Sycamore - Plain Text Parser

    @copyright: 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import wikiutil


#############################################################################
### Plain Text Parser
#############################################################################

class Parser:
    """
    Send plain text in a HTML <pre> element.
    """
    def __init__(self, raw, request, **kw):
        self.raw = raw
        self.request = request
        self.form = request.form
        self._ = request.getText

    def format(self, formatter):
        """
        Send the text.
        """
        #!!! send each line via the usual formatter calls
        text = wikiutil.escape(self.raw)
        text = text.expandtabs()
        text = text.replace('\n', '<br>\n')
        text = text.replace(' ', '&nbsp;')
        self.request.write(text)
