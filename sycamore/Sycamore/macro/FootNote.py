# -*- coding: iso-8859-1 -*-
"""
    Sycamore - FootNote Macro

    Collect and emit footnotes.

    @copyright: 2005 by philip neustrom <philipn@gmail.com>
    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import sha
from Sycamore import wikiutil

Dependencies = []

def execute(macro, args, formatter):
    if not formatter: formatter = macro.formatter
 
    # create storage for footnotes
    if not hasattr(formatter.request, 'footnotes'):
        formatter.request.footnotes = []
    
    if not args:
        return emit_footnotes(formatter.request, formatter)
    else:
        # store footnote and emit number
        idx = len(formatter.request.footnotes)
        fn_id = "-%s-%s" % (sha.new(args).hexdigest(), idx)
    	args = wikiutil.wikifyString(args, formatter.request, formatter.page, formatter=formatter)
        formatter.request.footnotes.append((args, fn_id))
        return "%s%s%s" % (
            formatter.sup(1),
            formatter.anchorlink('fndef' + fn_id, str(idx+1), id = 'fnref' + fn_id),
            formatter.sup(0),)

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
            result.append(request.footnotes[idx][0])
            result.append('</li>')
        result.append('</ul></div>')
        request.footnotes = []
        return ''.join(result)

    return ''

