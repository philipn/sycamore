# -*- coding: utf-8 -*-
"""
    Sycamore - Load I18N Text

    This macro has the main purpose of supporting Help* page authors
    to insert the texts that a user actually sees on his screen into
    the description of the related features (which otherwise could
    get very confusing).

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

Dependencies = ["language"]

def execute(macro, args, formatter):
    if not formatter:
        formatter = macro.formatter
    return macro.formatter.text(
        macro.request.getText(args).replace('<br>', '\n')
    )

