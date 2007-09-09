# -*- coding: utf-8 -*-
"""
    Sycamore - Outgoing Links Macro

    @copyright: 2006-2007 by Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import wikiutil
from Sycamore import config
from Sycamore import wikidb

from Sycamore.Page import Page

system_pages_startswith = ('wiki settings/', 'templates/')
system_pages = ('wiki settings', 'templates', 'wanted pages', 'bookmarks',
                'recent changes', 'user statistics', 'events board',
                'all pages', 'random pages', 'orphaned pages', 'interwiki map')

def skip_page(name):
    lower_name = name.lower()
    if lower_name in system_pages:
        return True
    for startname in system_pages_startswith:
        if lower_name.startswith(startname):
            return True
    return False

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter

    cursor = macro.request.cursor
    cursor.execute("""
        SELECT c.propercased_name, count(c.source_pagename) as cnt
        FROM (
            SELECT curPages.propercased_name, links.source_pagename
            FROM curPages LEFT JOIN links on
                (links.source_pagename=curPages.name and
                 links.wiki_id=%(wiki_id)s and
                 curPages.wiki_id=%(wiki_id)s)
            WHERE curPages.wiki_id=%(wiki_id)s
        ) as c
        GROUP BY c.propercased_name ORDER BY cnt""",
        {'wiki_id': macro.request.config.wiki_id})
    results = cursor.fetchall()
   
    old_count = -1
    for entry in results:
        name = entry[0] 
        lower_name = name.lower()
        if skip_page(name):
            continue
        
        new_count = entry[1]
        page = Page(name, macro.request)
        if new_count == 0 and page.isRedirect():
            continue

        if new_count != old_count:
            old_count = new_count
            macro.request.write(macro.formatter.heading(2, str(new_count)))
        else:
            macro.request.write(", ")
        macro.request.write(page.link_to(know_status=True,
                                         know_status_exists=True))

    return ''
