# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - WantedPages Macro

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @copyright: 2004-2005 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import urllib
from LocalWiki import config, user, wikiutil, wikidb
from LocalWiki.Page import Page

_guard = 0

Dependencies = ["pages"]

def comparey(x,y):
    if x[1] > y[1]: return -1 
    if x[1] == y[1]: return 0
    else: return 1

def comparey_alpha(x,y):
    if x[0] > y[0]: return 1 
    if x[0] == y[0]: return 0
    else: return -1

def showUsers(request):
  if request.query_string=="show_users=true":
    return True
  else:
    return False

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    _ = macro.request.getText

    # prevent recursive calls
    global _guard
    if _guard: return ''
    html = []

    # flush request output because this may take a second to generate
    macro.request.flush()

    # build a list of wanted pages tuples.  (pagename, k) where k is the number of links to pagename
    wanted = []
    cursor = macro.request.cursor
    if showUsers(macro.request):
      cursor.execute("SELECT destination_pagename, source_pagename from links left join curPages on (destination_pagename=curPages.name) where curPages.name is NULL order by destination_pagename")
    else:
      cursor.execute("SELECT destination_pagename, source_pagename from links left join curPages on (destination_pagename=curPages.name) left join users on (destination_pagename=users.name) where curPages.name is NULL and users.name is NULL order by destination_pagename")
      
    wanted_results = cursor.fetchall()
    if wanted_results:
      # we have wanted pages
      old_pagename = wanted_results[0][0]
      num_links = 0
      links = []
      for w_result in wanted_results:
        new_pagename = w_result[0]
	if old_pagename == new_pagename:
	  num_links += 1
	  links.append(w_result[1])
	else:
	   wanted.append((old_pagename, num_links, links))
	   num_links = 1
	   links = [w_result[1]]
	   old_pagename = new_pagename
      wanted.append((old_pagename, num_links, links))
    else:
        macro.request.write("<p>%s</p>" % _("No wanted pages in this wiki."))
	return ''

    # find the 'most wanted' pages
    wanted.sort(comparey)
    most_wanted = wanted[0:60]
    #alphabetize these
    most_wanted.sort(comparey_alpha)
    pagename = macro.request.getPathinfo()[1:] # usually 'Wanted Page' or something such
    if not showUsers(macro.request):
      html.append('<div style="float: right;">[%s]</div>' % wikiutil.link_tag(macro.request, pagename + "?show_users=true", "show users"))
    else:
      html.append('<div style="float: right;">[%s]</div>' % wikiutil.link_tag(macro.request, pagename, "hide users"))
    html.append("""<p>The "most" wanted pages based upon the number of links made from other pages (bigger means more wanted):</p>
    <div style="margin-top: 0px; margin-left: auto; margin-right: auto; width: 760px; text-align: left; vertical-align: top;padding-left: 7px; padding-right: 7px;">
    <p style="padding: 15px;  line-height: 1.45; margin-top: 0; padding-left: 7px; padding-right: 7px; width: 760px; solid 1px #eee; background: #f5f5f5; border: 1px solid rgb(170, 170, 170); ">""")
    # find the max number of links
    number_list = []
    for name, number, source_name in most_wanted:
        number_list.append(number)
    if number_list:
      max_links = max(number_list)
    else:
      max_links = 0

    for name, number, source_pagenames in most_wanted:
        print_number = ((number*1.0)/max_links) * 30
        if print_number < 12: print_number = 12
        html.append('<a class="nonexistent" style="font-size: %spx;  margin-top: 10px; margin-bottom: 10px; margin-right: 5px; " href="%s/%s">%s</a> &nbsp;' % (print_number, macro.request.getBaseURL(), wikiutil.quoteWikiname(name), name))

    html.append('</p></div>')
    macro.request.write(''.join(html))
    macro.request.write("""<p>What follows is a list of all "wanted" pages.  Each wanted page includes a list, following it, of all the pages where it is referred to:</p>
    <ol>""")

    for name, links, source_pagenames in wanted:
        macro.request.write('<li value="%s">' % links)
	macro.request.write(Page(name, macro.request).link_to(know_status=True, know_status_exists=False) + ": ")
	macro.request.write(Page(source_pagenames[0], macro.request).link_to())
	if len(source_pagenames) > 1:
	  for p in source_pagenames[1:-1]:
            macro.request.write(", " + Page(p, macro.request).link_to(know_status=True, know_status_exists=True))
	  macro.request.write(", " + Page(source_pagenames[-1], macro.request).link_to(know_status=True, know_status_exists=True))
	macro.request.write("</li>")
    macro.request.write("</ol>")

    return ''

