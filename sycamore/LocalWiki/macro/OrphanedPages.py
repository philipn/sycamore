# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - OrphanedPages Macro

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import config, user, wikiutil, wikidb

_guard = 0

Dependencies = ["pages"]

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    _ = macro.request.getText

    # prevent recursive calls
    global _guard
    if _guard: return ''

    # flush the request output because orphaned may take time to generate
    macro.request.flush()

    # delete all linked pages from a dict of all pages
    _guard = 1
    cursor = macro.request.cursor
    cursor.execute("SELECT curPages.name from curPages left join links on links.source_pagename=curPages.name where links.source_pagename is NULL;")
    orphanednames_result = cursor.fetchall()
    _guard = 0

    # check for the extreme case
    if not orphanednames_result:
        return "<p>%s</p>" % _("No orphaned pages in this wiki.")

    # return a list of page links
    from LocalWiki.Page import Page
    redirects = []
    pages = []
    for entry in orphanednames_result:
    	name = entry[0]
        page = Page(name, macro.request)
        is_redirect = False
        #if not macro.request.user.may.read(name): continue
        if page.isRedirect():
	  redirects.append(page)
	else:
	  pages.append(page)

    macro.request.write(macro.formatter.heading(2, 'Orphans'))
    macro.request.write(macro.formatter.bullet_list(1))
    for page in pages:
      macro.request.write(macro.formatter.listitem(1))
      macro.request.write(page.link_to(know_status=True, know_status_exists=True))
      macro.request.write(macro.formatter.listitem(0))
    macro.request.write(macro.formatter.bullet_list(0))

    macro.request.write(macro.formatter.heading(2, 'Orphaned Redirects'))
    macro.request.write(macro.formatter.bullet_list(1))
    for page in redirects:
      macro.request.write(macro.formatter.listitem(1))
      macro.request.write(page.link_to(know_status=True, know_status_exists=True))
      macro.request.write(macro.formatter.listitem(0))
    macro.request.write(macro.formatter.bullet_list(0))
    return ''
