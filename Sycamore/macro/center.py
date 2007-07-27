# -*- coding: utf-8 -*-
"""
    Sycamore - center Macro

    This very complicated macro centers text.

    Use the markup:

    --> center this stuff! <--

    instead, now.

    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import wikiutil
from Sycamore import config

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    text = []
    if args:
        if args == "begin":
            text.append('<center>')
        elif args == "end":
 	text.append('</center>')
    else:
        text.append('<b>You must supply the center macro with either '
                    '"begin" or "end": i.e. [[center(begin)]] my '
                    'centered text [[center(end)]]')

    return formatter.rawHTML(''.join(text))
