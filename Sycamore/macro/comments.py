# -*- coding: utf-8 -*-
"""
    Sycamore - comments macro.

    This macro displays a comments box on a page when inserted.

    Interacts with the comments action to produce the comment.

    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2005 by Mike Ivanov <mivanov@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import wikiutil
from Sycamore import config

Dependencies = ["time"] # cannot be cached - depends on may.edit()

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    macro.parser.inhibit_br += 2
    text = []
    if args:
        title = args
    else:
        title = "Comments:"
    if not macro.request.user.may.edit(macro.formatter.page):
        text.append('<h3>%s</h3>\n'
                    '<p><strong>Note: You must be logged in to add '
                    'comments</strong></p>\n' % title)
    else:
        text.append(
            '<h3>%(title)s</h3>\n'
            '<form method="POST" action="%(scriptname)s/%(q_pagename)s">\n'
            '<p><input type="hidden" name="action" value="comments">\n'
            '<textarea id="comment_text" name="comment_text" rows="1" '
                      'style="width:100%%" '
                      'onSelect="sizeTextField(this.id,event)" '
                      'onPaste="sizeTextField(this.id,event)" '
                      'onFocus="sizeTextField(this.id,event)" '
                      'onKeyPress="sizeTextField(this.id,event)">'
            '</textarea>\n'
            '<input style="display: none;" type="submit" name="button_dont" '
                    'value="Dont press me">'
            '<input type="hidden" name="button" value="Add Comment">\n'
            '<input class="formbutton" type="submit" name="button" '
                    'value="Add Comment">'
            '</p>\n'
            '</form>' % {'title': title,
                         'scriptname': macro.request.getScriptname(),
                         'q_pagename': wikiutil.quoteWikiname(macro.formatter.page.proper_name())})

    # we want to print a paragraph after the comments area if there's
    # anything following it
    macro.parser.force_print_p = True

    return formatter.rawHTML(''.join(text))
