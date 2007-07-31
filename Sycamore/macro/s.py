# -*- coding: utf-8 -*-
"""
    Sycamore - strikethrough macro, [[s(begin)]], [[s(end)]]

    DEPRECATED: use --X stuff X-- to strike through blocks of text.

    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import wikiutil
from Sycamore import config

from Sycamore.Page import Page

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    text = []
    if args:
        if args == "begin" or args == "start":
            text.append('<s>')
        elif args == "end" or args == "stop":
            text.append('</s>')
    else:
       text.append('<b>You must supply the strike-through macro with '
                   'either "begin" or "end": i.e. [[s(begin)]] my '
                   'striked-through text [[s(end)]]')

    return formatter.rawHTML(''.join(text))
