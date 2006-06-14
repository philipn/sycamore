# -*- coding: iso-8859-1 -*-
"""
    Sycamore - BR Macro

    This very complicated macro produces a line break.

    @copyright: 2000 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from Sycamore.Page import Page

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter

    if not macro.parser.in_table:
      if macro.parser.inhibit_br: return ''
      macro.parser.inhibit_br = 1 # so we don't print two brs! :)

    return formatter.linebreak(0)
