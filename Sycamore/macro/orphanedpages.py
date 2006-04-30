# -*- coding: iso-8859-1 -*-
"""
    Sycamore - OrphanedPages Macro

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore import config, user, wikiutil, wikidb

_guard = 0

Dependencies = ["pages"]

def showUsers(request):
  if request.form.has_key("show_users"):
    if request.form["show_users"][0] == "true":
      return True
    else: return False
  else:
    return False

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
    if showUsers(macro.request):
      cursor.execute("SELECT curPages.propercased_name from curPages left join links on links.destination_pagename=curPages.name where links.destination_pagename is NULL")
    else:
      cursor.execute("SELECT curPages.propercased_name from curPages left join links on links.destination_pagename=curPages.name left join users on users.name=curPages.name where links.destination_pagename is NULL and users.name is NULL")
     
    orphanednames_result = cursor.fetchall()
    _guard = 0

    # check for the extreme case
    if not orphanednames_result:
        return "<p>%s</p>" % _("No orphaned pages in this wiki.")

    # return a list of page links
    from Sycamore.Page import Page
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

    pagename = macro.request.getPathinfo()[1:] # usually 'Orphaned Pages' or something such
    if not showUsers(macro.request):
      macro.request.write('<div style="float: right;"><div class="actionBoxes"><span>%s</span></div></div>' % wikiutil.link_tag(macro.request, pagename + "?show_users=true", "show users"))
    else:
      macro.request.write('<div style="float: right;"><div class="actionBoxes"><span>%s</span></div></div>' % wikiutil.link_tag(macro.request, pagename, "hide users"))

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
