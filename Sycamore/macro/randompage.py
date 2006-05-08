# -*- coding: iso-8859-1 -*-
"""
    Sycamore - RandomPage Macro

    @copyright: 2000 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import whrandom
from Sycamore import config, wikiutil
from Sycamore.Page import Page

Dependencies = ["time"]

def execute(macro, args, formatter):
    if not formatter: formatter = macro.formatter
    # get number of wanted links        
    try:
        links = max(int(args), 1)
    except StandardError:
        links = 1

    # select the pages from the page list
    random_list = wikiutil.getRandomPages(macro.request)
    pages = []
    while len(pages) < links and random_list:
        pagename = whrandom.choice(random_list)
	page = Page(pagename, macro.request)
        if macro.request.user.may.read(page) and page.exists():
            pages.append(page)

    # return a single page link
    if links == 1: return pages[0].link_to()

    # return a list of page links
    pages.sort()
    result = [macro.formatter.bullet_list(1)]
    for page in pages:
        result.append("%s%s%s" % (macro.formatter.listitem(1), page.link_to(), macro.formatter.listitem(0)))
    result.append(macro.formatter.bullet_list(0))

    return ''.join(result)

