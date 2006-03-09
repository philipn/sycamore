# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Processor for Syntax Highlighting

    @copyright: 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import cStringIO
from Sycamore.parser import python

Dependencies = []

def process(request, formatter, lines):
    if lines[0].strip() == "#!python":
        del lines[0]

    # !!! same code as with "inline:" handling in parser/wiki.py,
    # this needs to be unified!

    buff = cStringIO.StringIO()
    colorizer = python.Parser('\n'.join(lines), request, out = buff)
    colorizer.format(formatter)

    if not formatter.in_pre:
        request.write(formatter.preformatted(1))
    request.write(formatter.rawHTML(buff.getvalue()))
    request.write(formatter.preformatted(0))

