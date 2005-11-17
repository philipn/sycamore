# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - RandomPage Macro

    @copyright: 2000 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import whrandom
from LocalWiki import config, wikiutil

Dependencies = ["time"]

def execute(macro, args):
    # get number of wanted links        
    try:
        links = max(int(args), 1)
    except StandardError:
        links = 1

    # select the pages from the page list
    all_pages = wikiutil.getPageList(config.text_dir)
    pages = []
    while len(pages) < links and all_pages:
        page = whrandom.choice(all_pages)
        if macro.request.user.may.read(page):
            pages.append(page)
        all_pages.remove(page)

    # return a single page link
    if links == 1: return macro.formatter.pagelink(pages[0], generated=1)

    # return a list of page links
    pages.sort()
    result = macro.formatter.bullet_list(1)
    for name in pages:
        result = result + macro.formatter.listitem(1)
        result = result + macro.formatter.pagelink(name, generated=1)
        result = result + macro.formatter.listitem(0)
    result = result + macro.formatter.bullet_list(0)

    return result

