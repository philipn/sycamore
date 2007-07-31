# -*- coding: utf-8 -*-
"""
    Sycamore - RandomQuote Macro

    Selects a random quote from Fortune Cookies or a given page.

    Usage:
        [[RandomQuote()]]
        [[RandomQuote(WikiTips)]]
    
    Comments:
        It will look for list delimiters on the page in question.
        It will ignore anything that is not in an "*" list.

    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
    
    Originally written by Thomas Waldmann.
    Gustavo Niemeyer added wiki markup parsing of the quotes.
"""

# Imports
import random
import cStringIO

from Sycamore import wikiutil

from Sycamore.Page import Page

Dependencies = ["time"]

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    _ = macro.request.getText

    pagename = args or 'Fortune Cookies'
    page = Page(pagename, macro.request)
    raw = page.get_raw_body()
    if not macro.request.user.may.read(page):
        raw = ""

    # this selects lines looking like a list item
    # !!! TODO: make multi-line quotes possible
    # (optionally split by "----" or something)
    quotes = raw.splitlines()
    quotes = [quote.strip() for quote in quotes]
    quotes = [quote[2:] for quote in quotes if quote.startswith('* ')]
    
    if not quotes:
        return (macro.formatter.highlight(1) +
                _('No quotes on %(pagename)s.') % {'pagename': pagename} +
                macro.formatter.highlight(0))
                
    quote = random.choice(quotes)

    if quote.lower().find("randomquote") == -1:
        quote = wikiutil.wikifyString(quote, macro.request, page, strong=True)
        quote = wikiutil.stripOuterParagraph(quote)

    return quote
