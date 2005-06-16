# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - WantedPages Macro

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import urllib
from LocalWiki import config, user, wikiutil
from LocalWiki.Page import Page

_guard = 0

Dependencies = ["pages"]

def comparey(x,y):
    if x[1] > y[1]: return -1 
    if x[1] == y[1]: return 0
    else: return 1

def comparey2(x,y):
    if x[0] < y[0]: return -1 
    if x[0] == y[0]: return 0
    else: return 1


def execute(macro, args):
    _ = macro.request.getText

    # prevent recursive calls
    global _guard
    if _guard: return ''

    # build a dict of wanted pages
    _guard = 1
    wanted = {}
    translation_dict = wikiutil.getNoCaseDict(config.text_dir)
    pages = wikiutil.getNoCasePageDict(config.text_dir)
    for page in pages.values():
        #if not wikiutil.isSystemPage(macro.request, page.page_name):
#    continue
        # Regular users won't get /MoinEditorBackup pages shown anyway, but
        # WikiAdmin(s)  would - because they have global read rights.
        # Further, pages wanted from editor backup pages are irrelevant.
        links = page.getPageLinks(macro.request)
        for link in links:
            if not pages.has_key(link.lower()):
                if wanted.has_key(link):
                    wanted[link][page.page_name] = 1
                else:
                    wanted[link] = {page.page_name: 1}
    _guard = 0

    # check for the extreme case
    if not wanted:
        return "<p>%s</p>" % _("No wanted pages in this wiki.")

    # return a list of page links
    wantednames = wanted.keys()
    wantednames.sort()
    result = []
    
    wanted_omg = []
    for name in wantednames:
       wanted_omg.append((name, len(wanted[name].keys())))
    wanted_omg.sort(comparey)
    most_wanted = wanted_omg[0:60]
    most_wanted.sort(comparey2)
    result.append('<p>The "most" wanted pages based upon the number of links made from other pages:</p>')
    result.append('<div style="margin-top: 0px; margin-left: auto; margin-right: auto; width: 760px; text-align: left; vertical-align: top;padding-left: 7px; padding-right: 7px;">')
    result.append('<p style="padding: 15px;  line-height: 1.45; margin-top: 0; padding-left: 7px; padding-right: 7px; width: 760px; solid 1px #eee; background: #f5f5f5; border: 1px solid rgb(170, 170, 170); ">')
    if config.relative_dir:
        add_on = '/'
    else:
        add_on = ''

       
    number_list = []
    for name, number in most_wanted:
        number_list.append(number)

    for name, number in most_wanted:
        print_number = ((number*1.0)/max(number_list)) * 30
        if print_number < 12: print_number = 12
        result.append('<a class="nonexistent" style="font-size: %spx;  margin-top: 10px; margin-bottom: 10px; margin-right: 5px; " href="/%s%s%s">%s</a> &nbsp;' % (print_number, config.relative_dir, add_on, wikiutil.quoteWikiname(name), name))

    result.append('</p></div>')

    result.append('<p>A list of all non-existing pages (links made to pages that do not yet exist).  Each non-existing page includes a list, following it, of all the pages where it is referred to:</p>')
    result.append(macro.formatter.number_list(1))
    for name in wantednames:
        if not name: continue
        result.append(macro.formatter.listitem(1))
        result.append(macro.formatter.pagelink(name, generated=1))

        wherelink = lambda n, w=name, p=pages: \
            p[n.lower()].link_to(macro.request, querystr='action=highlight&value=%s' % urllib.quote_plus(w))
        where = wanted[name].keys()
        where.sort()
        if macro.formatter.page.page_name in where:
            where.remove(macro.formatter.page.page_name)
        result.append(": " + ', '.join(map(wherelink, where)))
        result.append(macro.formatter.listitem(0))
    result.append(macro.formatter.number_list(0))

       

    return ''.join(result)

