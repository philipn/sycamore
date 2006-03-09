# -*- coding: iso-8859-1 -*-
"""
    Sycamore - AbandonedPages Macro

    This is a list of pages that were not edited for a long time
    according to the edit log; if you shortened the log, the displayed
    information may not be what you expect.

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from Sycamore.macro import RecentChanges

def execute(macro, args):
    return RecentChanges.execute(macro, args, abandoned=1)

