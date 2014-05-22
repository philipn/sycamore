# -*- coding: utf-8 -*-
"""
    Sycamore - FootNote Macro

    Collect and emit footnotes.

    @copyright: 2005-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import hashlib

from Sycamore import wikiutil

Dependencies = []

def execute(macro, args, formatter):
    if not formatter:
        formatter = macro.formatter
 
    # create storage for footnotes
    if not hasattr(formatter.request, 'footnotes'):
        formatter.request.footnotes = []
    
    if not args:
        return emit_footnotes(formatter.request, formatter)
    else:
        # store footnote and emit number
        idx = len(formatter.request.footnotes)
        fn_id = "-%s-%s" % (hashlib.new('sha1', args.encode('utf-8')).hexdigest(), idx)
        formatter.request.footnotes.append((args, fn_id))
        return "%s%s%s" % (
            formatter.sup(1),
            formatter.anchorlink('fndef'+fn_id, str(idx+1), id='fnref'+fn_id),
            formatter.sup(0))

    # nothing to do or emit
    return ''

def emit_footnotes(request, formatter):
    # emit collected footnotes
    if request.footnotes:
        request.write(formatter.rawHTML(
            '<div class="footnotes"><div></div><ul>'))
        for idx in range(len(request.footnotes)):
            fn_id = request.footnotes[idx][1]
            fn_no = formatter.anchorlink('fnref'+fn_id, str(idx+1),
                                         id='fndef'+fn_id)

            request.write(formatter.rawHTML('<li><span>%s</span>' % fn_no))
            request.write(wikiutil.stripOuterParagraph(wikiutil.wikifyString(
                request.footnotes[idx][0], formatter.request, formatter.page,
                formatter=formatter)))
            request.write(formatter.rawHTML('</li>'))
        request.write(formatter.rawHTML('</ul></div>'))
        request.footnotes = []
    return ''
