# -*- coding: iso-8859-1 -*-
"""
    Sycamore - BR Macro

    This very complicated macro produces a line break.

    @copyright: 2000 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    return formatter.linebreak(0)
