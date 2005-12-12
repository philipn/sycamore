# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - OrphanedPages Macro

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import config, user, wikiutil

_guard = 0

Dependencies = ["pages"]

def execute(macro, args):
    _ = macro.request.getText

    # prevent recursive calls
    global _guard
    if _guard: return ''

    # delete all linked pages from a dict of all pages
    _guard = 1
    pages = wikiutil.getPageDict()
    # we do not look at pages we have no read rights on - this avoids
    # having MoinEditorBackup showing up (except your very own one)
    for key in pages.keys():
        if wikiutil.isSystemPage(macro.request, pages[key].page_name):
            del pages[key]
    orphaned = {}
    orphaned.update(pages)
    for page in pages.values():
        links = page.getPageLinks(macro.request)
        for link in links:
            if orphaned.has_key(link):
                del orphaned[link]
    _guard = 0

    # check for the extreme case
    if not orphaned:
        return "<p>%s</p>" % _("No orphaned pages in this wiki.")

    # return a list of page links
    orphanednames = orphaned.keys()
    orphanednames.sort()
    result = []
    result.append(macro.formatter.number_list(1))
    for name in orphanednames:
        if not name: continue
        result.append(macro.formatter.listitem(1))
        result.append(macro.formatter.pagelink(name, generated=1))
        result.append(macro.formatter.listitem(0))
    result.append(macro.formatter.number_list(0))

    return ''.join(result)

    #return "<p><b>This feature is disabled temporarily until we improve its performance.</b></p>"
