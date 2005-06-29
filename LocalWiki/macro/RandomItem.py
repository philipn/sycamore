# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - RandomQuote Macro

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

def execute(macro, args):
    _ = macro.request.getText

    from LocalWiki.Page import Page, wikiutil
    import re, random, cStringIO, array
    split_args = args.split(',')
    pagename = ''
    items = ''
    if len(split_args) > 2:
        # if they wrote a page that had a comma in it..
        for i in split_args[:len(split_args)]:
            pagename += i
        items = split_args[len(split_args)]
    elif len(split_args) == 2:
      pagename = split_args[0]
      items = split_args[1]
    else:
      pagename = split_args[0]
      items = ''
        
    page = Page(pagename)

    try:
        links = max(int(items), 1)
    except StandardError:
        links = 1


    raw = page.get_raw_body()
    if not macro.request.user.may.read(pagename):
        raw = ""

    # this selects lines looking like a list item
    # !!! TODO: make multi-line quotes possible (optionally split by "----" or something)
    quotes = raw.splitlines()
    if links > 1:
        #quotes = [quote.strip() for quote in quotes]
        quotes = [quote for quote in quotes if quote.startswith(' *')]
        random.shuffle(quotes)
        while len(quotes) > links:
            quotes = quotes[:-1]
        quote = ''

    #quote = macro.formatter.bullet_list(1)        
        for name in quotes:
            #quote = quote + macro.formatter.listitem(1)            
            quote = quote + name + '\n'
            #quote = quote + macro.formatter.listitem(0)
    #quote = macro.formatter.bullet_list(0)
            
        page.set_raw_body(quote, 1)
        out = cStringIO.StringIO()
        macro.request.redirect(out)
        page.send_page(macro.request, content_only=1, content_id="RandomQuote_%s" % wikiutil.quoteWikiname(page.page_name) )
        quote = out.getvalue()
        macro.request.redirect()
        # quote = re.sub('(\<div[^\>]+\>)|(\</div\>)', '', quote)


        #quote = quote + macro.formatter.bullet_list(0)
    
    else:
        quotes = [quote.strip() for quote in quotes]
        quotes = [quote[2:] for quote in quotes if quote.startswith('* ')]
        quote = random.choice(quotes)

        page.set_raw_body(quote, 1)
        out = cStringIO.StringIO()
        macro.request.redirect(out)
        page.send_page(macro.request, content_only=1, content_id="RandomQuote_%s" % wikiutil.quoteWikiname(page.page_name) )
        quote = out.getvalue()
        macro.request.redirect()
        # quote = re.sub('(\<div[^\>]+\>)|(\</div\>)', '', quote)    



    if not quotes:
        return (macro.formatter.highlight(1) +
                _('No quotes on %(pagename)s.') % {'pagename': pagename} +
                macro.formatter.highlight(0))
                
    
    return ''.join(quote)

