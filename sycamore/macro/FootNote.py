# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - FootNote Macro

    Collect and emit footnotes. Note that currently footnote
    text cannot contain wiki markup.

    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import sha

Dependencies = ["time"] # footnote macro cannot be cached

def execute(macro, args):
    # create storage for footnotes
    if not hasattr(macro.request, 'footnotes'):
        macro.request.footnotes = []
    
    if not args:
        return emit_footnotes(macro.request, macro.formatter)
    else:
        # store footnote and emit number
        idx = len(macro.request.footnotes)
        fn_id = "-%s-%s" % (sha.new(args).hexdigest(), idx)
        macro.request.footnotes.append((args, fn_id))
        return "%s%s%s" % (
            macro.formatter.sup(1),
            macro.formatter.anchorlink('fndef' + fn_id, str(idx+1), id = 'fnref' + fn_id),
            macro.formatter.sup(0),)

    # nothing to do or emit
    return ''


def emit_footnotes(request, formatter):
    # emit collected footnotes
    if request.footnotes:
        result = []
        result.append('<div class="footnotes">')
        result.append('<div></div><ul>')
        for idx in range(len(request.footnotes)):
            fn_id = request.footnotes[idx][1]
            fn_no = formatter.anchorlink('fnref' + fn_id, str(idx+1), id = 'fndef' + fn_id)

            result.append('<li><span>')
            result.append(fn_no + '</span> ')
            result.append(formatter.text(request.footnotes[idx][0]))
            result.append('</li>')
        result.append('</ul></div>')
        request.footnotes = []
        return ''.join(result)

    return ''

