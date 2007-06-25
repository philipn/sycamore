# -*- coding: iso-8859-1 -*-
from Sycamore import config
"""
    Sycamore - RandomQuote Macro

    Selects a random quote from FortuneCookies or a given page.

    Usage:
        [[RandomQuote()]]
        [[RandomQuote(WikiTips)]]
    
    Comments:
        It will look for list delimiters on the page in question.
        It will ignore anything that is not in an "*" list.

    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
    
    Originally written by Thomas Waldmann.
    Gustavo Niemeyer added wiki markup parsing of the quotes.
"""


Dependencies = ["time"]

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    _ = macro.request.getText

    from Sycamore.Page import Page, wikiutil
    import re, random, cStringIO, array
    re_args = re.search('(?P<caption>.+)\,\s(?P<the_rest>.*)', args)
    pagename = re_args.group('caption')
    items = re_args.group('the_rest')
    page = Page(pagename, macro.request)

    try:
        links = max(int(items), 1)
    except StandardError:
        links = 1


    raw = page.get_raw_body()
    if not macro.request.user.may.read(page):
        raw = ""

    # this selects lines looking like a list item
    # !!! TODO: make multi-line quotes possible (optionally split by "----" or something)
    quotes = raw.splitlines()
    if links > 1:
        quotes = [quote for quote in quotes if quote.startswith(' *')]
        random.shuffle(quotes)
        while len(quotes) > links:
            quotes = quotes[:-1]
        quote = ''

        for name in quotes:
            quote = quote + name + '\n'
            
        page.set_raw_body(quote, 1)
        out = cStringIO.StringIO()
        macro.request.redirect(out)
        page.send_page(content_only=1, content_id="randomquote_%s" % wikiutil.quoteWikiname(page.page_name) )
        quote = out.getvalue()
        macro.request.redirect()

    else:
        quotes = [quote.strip() for quote in quotes]
        quotes = [quote[2:] for quote in quotes if quote.startswith('* ')]
        if quotes:
          quote = random.choice(quotes)
        else:
          quote = ''

        page.set_raw_body(quote, 1)
        out = cStringIO.StringIO()
        macro.request.redirect(out)
        page.send_page(content_only=1, content_id="randomquote_%s" % wikiutil.quoteWikiname(page.page_name) )
        quote = out.getvalue()
        macro.request.redirect()


    if not quotes:
        return (macro.formatter.highlight(1) +
                _('No quotes on %(pagename)s.') % {'pagename': pagename} +
                macro.formatter.highlight(0))
    
    return quote.decode(config.charset)
