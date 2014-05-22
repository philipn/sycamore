# -*- coding: utf-8 -*-
"""
    Sycamore - TableOfContents Macro

    Optional integer argument: maximal depth of listing.

    @copyright: 2007 Philip Neustrom <philipn@gmail.com>
    @copyright: 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re
import hashlib

from Sycamore import wikiutil

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter

    # A regular expression that borders on incomprehensible
    heading = re.compile(r"^\s*(?P<hmarker>=+)\s*(.*)\s*(?P=hmarker)")
    result = []
    baseindent = 0
    indent = 0
    lineno = 0
    titles = {}
    right = False
    left = False
    if args:
        if args.lower() == 'right':
            right = True
        elif args.lower() == 'left':
            left = True

    try:
        mindepth = int(macro.request.getPragma('section-numbers', 1))
    except (ValueError, TypeError):
        mindepth = 1

    try:
        maxdepth = max(int(args), 1)
    except (ValueError, TypeError):
        maxdepth = 99

    for line in macro.parser.lines:
        # Filter out the headings
        lineno = lineno + 1
        # FIXME this also finds "headlines" in {{{ code sections }}}:
        match = heading.match(line)
        if not match:
            continue
        title_text = match.group(2).strip() # A slightly questionable strip
        if not title_text:
            continue
        wikified_title = wikiutil.wikifyString(title_text, macro.request,
                                               formatter.page)
        title_text = wikiutil.simpleStrip(macro.request, 
                        wikiutil.stripOuterParagraph(wikified_title))
        titles.setdefault(title_text, 0)
        titles[title_text] += 1

        # Get new indent level
        newindent = len(match.group(1))
        if newindent > maxdepth:
            continue
        if newindent < mindepth:
            continue

        # Close lists
        for i in range(0,indent-newindent):
            result.append(macro.formatter.number_list(0))

        # Open Lists
        for i in range(0,newindent-indent):
            result.append(macro.formatter.number_list(1))

        # Add the heading
        unique_id = ''
        if titles[title_text] > 1:
            unique_id = '-%d' % titles[title_text]

        result.append(macro.formatter.listitem(1))
        result.append(macro.formatter.anchorlink(
                        "head-" +
                            hashlib.new('sha1', title_text.encode('utf-8')).hexdigest() +
                            unique_id,
                        title_text, escape=False))
        result.append(macro.formatter.listitem(0))
        
        # Set new indent level
        indent = newindent

    # Close pending lists
    for i in range(baseindent, indent):
        result.append(macro.formatter.number_list(0))

    html_class = 'tableOfContents'
    if not result:
        return ''
    if right:
        html_class += ' floatRightTOC'
    elif left:
        html_class += ' floatLeftTOC'
    return ('<table class="%s"><tr><td>' % html_class + ''.join(result) +
            '</td></tr></table>')
