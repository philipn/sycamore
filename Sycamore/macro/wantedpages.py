# -*- coding: utf-8 -*-
"""
    Sycamore - WantedPages Macro

    @copyright: 2004-2007 Philip Neustrom <philipn@gmail.com>
    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import urllib

from Sycamore import config
from Sycamore import user
from Sycamore import wikiutil
from Sycamore import wikidb

from Sycamore.Page import Page

_guard = 0

Dependencies = ["pages"]

def comparey(x,y):
    if x[1] > y[1]:
        return -1 
    if x[1] == y[1]:
        return 0
    else:
        return 1

def comparey_alpha(x,y):
    if x[0] > y[0]:
        return 1 
    if x[0] == y[0]:
        return 0
    else:
        return -1

def showUsers(request):
    return (request.form.has_key("show_users") and
            request.form["show_users"][0] == "true")

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    _ = macro.request.getText

    # prevent recursive calls
    global _guard
    if _guard:
        return ''
    html = []

    # flush request output because this may take a second to generate
    macro.request.flush()

    # build a list of wanted pages tuples.  (pagename, k) where k is the number of links to pagename
    wanted = []
    cursor = macro.request.cursor
    if showUsers(macro.request):
        cursor.execute(
            """SELECT destination_pagename_propercased, c.propercased_name,
                      destination_pagename
               FROM (SELECT destination_pagename_propercased, source_pagename,
                            destination_pagename
                     FROM (SELECT destination_pagename_propercased,
                                  destination_pagename, source_pagename
                           FROM links
                           WHERE wiki_id=%(wiki_id)s
                           ) as ourLinks
                     LEFT JOIN
                     curPages ON (destination_pagename=curPages.name and
                                  curPages.wiki_id=%(wiki_id)s)
                     WHERE curPages.name is NULL
                     ) as wanted,
                     curPages as c
               WHERE c.name=source_pagename and c.wiki_id=%(wiki_id)s
               ORDER BY destination_pagename""",
            {'wiki_id':macro.request.config.wiki_id})
    else:
        cursor.execute(
            """SELECT destination_pagename_propercased, c.propercased_name,
                      destination_pagename
               FROM (SELECT destination_pagename_propercased, source_pagename,
                            destination_pagename
                     FROM (SELECT destination_pagename_propercased,
                                  destination_pagename, source_pagename
                           FROM links
                           WHERE wiki_id=%(wiki_id)s
                           ) as ourLinks
                     LEFT JOIN
                     curPages ON (destination_pagename=curPages.name and
                                  curPages.wiki_id=%(wiki_id)s)
                     LEFT JOIN
                     userWikiInfo ON (
                         destination_pagename=userWikiInfo.user_name and
                         userWikiInfo.wiki_id=%(wiki_id)s)
                     WHERE curPages.name is NULL and
                           userWikiInfo.user_name is NULL
                     ) as wanted,
                     curPages as c
                     WHERE c.name=source_pagename and c.wiki_id=%(wiki_id)s
                     ORDER BY destination_pagename""",
            {'wiki_id':macro.request.config.wiki_id})
      
    show_users = showUsers(macro.request)
    dont_append = False
    wanted_results = cursor.fetchall()
    if not wanted_results:
        macro.request.write("<p>%s</p>" % _("No wanted pages in this wiki."))
        return ''

    # we have wanted pages
    old_pagename_propercased = wanted_results[0][0]
    old_pagename = old_pagename_propercased.lower()
    num_links = 0
    links = []
    for w_result in wanted_results:
        if old_pagename.startswith(config.user_page_prefix.lower()):
            if user.unify_userpage(macro.request, old_pagename, old_pagename):
                theusername = old_pagename[len(config.user_page_prefix):]
                theuser = user.User(macro.request, name=theusername)
                if (theuser.wiki_for_userpage and
                    (theuser.wiki_for_userpage !=
                     macro.request.config.wiki_name)):
                    old_pagename_propercased = w_result[0]
                    old_pagename = old_pagename_propercased.lower()
                    continue

        new_pagename_propercased = w_result[0]
        new_pagename = new_pagename_propercased.lower()
        if old_pagename == new_pagename:
            num_links += 1
            links.append(w_result[1])
        else:
            # done counting -- we now append to the wanted list
            if not (old_pagename.startswith(config.user_page_prefix.lower()) and
                not show_users):
                wanted.append((old_pagename_propercased, num_links, links))
            num_links = 1
            links = [w_result[1]]
            old_pagename_propercased = new_pagename_propercased
            old_pagename = old_pagename_propercased.lower()
    wanted.append((old_pagename_propercased, num_links, links))
    
    # find the 'most wanted' pages
    wanted.sort(comparey)
    most_wanted = wanted[0:60]
    #alphabetize these
    most_wanted.sort(comparey_alpha)
    # usually 'Wanted Page' or something such
    pagename = macro.request.getPathinfo()[1:] 
    if not showUsers(macro.request):
        html.append('<div style="float: right;">'
                    '<div class="actionBoxes"><span>%s</span></div></div>' %
                    wikiutil.link_tag(macro.request,
                                      pagename + "?show_users=true",
                                      "show users"))
    else:
      html.append('<div style="float: right;">'
                  '<div class="actionBoxes"><span>%s</span></div></div>' %
                  wikiutil.link_tag(macro.request, pagename, "hide users"))
    html.append(
        '<p>The "most" wanted pages based upon the number of links made from '
        'other pages (bigger means more wanted):</p>\n'
        '<div style="margin-top: 0px; margin-left: auto; margin-right: auto; '
                    'width: 760px; text-align: left; vertical-align: top; '
                    'padding-left: 7px; padding-right: 7px;">\n'
        '<p style="padding: 15px;  line-height: 1.45; margin-top: 0; '
                  'padding-left: 7px; padding-right: 7px; width: 760px; '
                  'solid 1px #eee; background: #f5f5f5; '
                  'border: 1px solid rgb(170, 170, 170); ">\n')
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
        if print_number < 12:
            print_number = 12
        html.append('<a class="nonexistent" style="font-size: %spx;  '
                                                  'margin-top: 10px; '
                                                  'margin-bottom: 10px; '
                                                  'margin-right: 5px; " '
                       'href="%s/%s">%s</a> &nbsp;' %
                    (print_number, macro.request.getBaseURL(),
                     wikiutil.quoteWikiname(name), name))

    html.append('</p></div>')
    macro.request.write(''.join(html))
    macro.request.write('<p>What follows is a list of all "wanted" pages.  '
                        'Each wanted page includes a list, following it, of '
                        'all the pages where it is referred to:</p>\n'
                        '<ol>\n')

    for name, links, source_pagenames in wanted:
        macro.request.write('<li value="%s">' % links)
        macro.request.write(Page(name, macro.request).link_to(
                know_status=True, know_status_exists=False) +
            ": ")
        macro.request.write(Page(source_pagenames[0], macro.request).link_to(
                know_status=True, know_status_exists=True))
        if len(source_pagenames) > 1:
            for p in source_pagenames[1:-1]:
                macro.request.write(", " +
                    Page(p, macro.request).link_to(know_status=True,
                                                   know_status_exists=True))
            macro.request.write(", " +
                Page(source_pagenames[-1], macro.request).link_to(
                        know_status=True, know_status_exists=True))
        macro.request.write("</li>")
    macro.request.write("</ol>")

    return ''
