# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Bookmarks.  I started by modifying the Sycamore RecentChanges.

    @copyright: 2005-2006 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO, os, urllib
from Sycamore import config, user, util, wikiutil, wikidb
from Sycamore.Page import Page
from Sycamore.widget.comments import Comment

_DAYS_SELECTION = [1, 2, 3, 7]
_MAX_DAYS = 2
_MAX_PAGENAME_LENGTH = 15 # 35

#############################################################################
### Bookmarks Macro
#############################################################################

# let's not bother trying to cache this macro
Dependencies = ["time"] # ["user", "pages", "pageparams", "bookmark"]

def groupFavorites(favorites):
    def cmp_lines_edit(first, second):
        return cmp(first.ed_time, second.ed_time)
       
    def cmp_lines_name(first, second):
        return cmp(first.pagename, second.pagename)

    favorites_dict = {}
    for page_line in favorites:
      lower_page_name = page_line.pagename.lower()
      if favorites_dict.has_key(lower_page_name):
        favorites_dict[lower_page_name].append(page_line)
      else:
        favorites_dict[lower_page_name] = [page_line]

    for lower_page_name in favorites_dict:
      if len(favorites_dict[lower_page_name]) > 1:
        favorites_dict[lower_page_name].sort(cmp_lines_edit)
      favorites_dict[lower_page_name] = favorites_dict[lower_page_name][-1]	

    favorites = favorites_dict.values()
    favorites.sort(cmp_lines_name)
    return favorites

def execute(macro, args, formatter=None, **kw):
    if not formatter: formatter = macro.formatter
    request = macro.request
    _ = request.getText
    pagename = macro.formatter.page.page_name
    pagename_propercased = macro.formatter.page.proper_name()
    cursor = request.cursor

    tnow = time.time()
    msg = ""

    pages = {}
    ignore_pages = {}

    today = request.user.getTime(tnow)[0:3]
    this_day = today
    day_count = 0
    local_favoriteList = []
    
    if not request.user.id:
      # not logged in user
      request.write('<p>You must be logged in to use the bookmarks functionality.  Bookmarks let you easily keep track of pages you think are interesting.</p>')
      return ''
    else:
      local_favoriteList = wikidb.getRecentChanges(request, per_page_limit=1, userFavoritesFor=request.user.id)
      local_favoriteList = groupFavorites(local_favoriteList)

      from Sycamore.formatter.text_html import Formatter
      from Sycamore import user
      formatter = Formatter(request)
      find_month = { 1:"Jan.", 2:"Feb.", 3:"Mar.", 4:"Apr.", 5:"May", 6:"Jun.", 7:"Jul.", 8:"Aug.", 9:"Sept.", 10:"Oct.", 11:"Nov.", 12:"Dec." }   

    rss_html = '<link rel=alternate type="application/rss+xml" href="%s/%s?action=rss_rc&amp;user=%s" title="Recent Changes on %s\'s bookmarks"><div style="float:right;"><a title="%s\'s Bookmarks RSS Feed" href="%s/%s?action=rss_rc&amp;user=%s" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a></div>' % (request.getScriptname(), wikiutil.quoteWikiname(pagename_propercased), urllib.quote_plus(request.user.propercased_name), request.user.propercased_name, request.user.propercased_name, request.getScriptname(), wikiutil.quoteWikiname(pagename_propercased), urllib.quote_plus(request.user.propercased_name))
    request.write(rss_html)
    request.write('<table>')
    if not local_favoriteList:
      request.write('<p>Bookmarks let you easily keep track of pages you think are interesting.</p><p><i>You have no Bookmarks.  To add a page click "Bookmark this page" at the bottom of the page.</i></p>')

    showed_update = False
    seen_list = []
    line_of_text = ''
    for page_line in local_favoriteList:
          page_line.comment = Comment(request, page_line.comment, page_line.action, page_line.pagename).render()
          bookmark = request.user.getFavBookmark(page_line.pagename)

	  # in the case of uploads/deletes of images, etc we'd like to show a useful comment
          page_line.time_tuple = request.user.getTime(page_line.ed_time)
          day = page_line.time_tuple[0:3]

          if page_line.ed_time > bookmark:
            # We do bold
            line_of_text = '<tr><td valign="center" class="rcpagelink">' + '<strong style="font-size: 10px;">[%s]</strong> &nbsp; %s' % (Page(page_line.pagename, request).link_to(text="diff", querystr='action=diff&date=%s'% repr(bookmark)), Page(page_line.pagename, request).link_to())
            line_of_text = line_of_text + " &nbsp;" + '<b><span align="right" style="font-size: 12px;">' + 'last modified '
            line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2])
            line_of_text = line_of_text + time.strftime(" at %I:%M %p by</span></b>", page_line.time_tuple) + '<span class="faveditor">'
            if page_line.comment:
              line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (page_line.getEditor(request), page_line.comment)
            else:
              line_of_text = line_of_text + ' %s</span>' % (page_line.getEditor(request))
            line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="%s/Bookmarks?action=favorite&delete=%s">Remove</a>]</span>' % (request.getScriptname(), wikiutil.quoteWikiname(page_line.pagename)) + '</td></tr>'

          else:
             # We don't do bold
            line_of_text = '<tr><td valign="center" class="rcpagelink"><font style="font-size: 10px;">[%s]</font> &nbsp; %s &nbsp;<span align="right" class="favtime">last modified ' % (Page(page_line.pagename, request).link_to(text="diff", querystr="action=diff"), Page(page_line.pagename, request).link_to())
            line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2]) 
            line_of_text = line_of_text + time.strftime(" at %I:%M %p by</span>", page_line.time_tuple) + '<span class="faveditor">'
            if page_line.comment:
              line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (page_line.getEditor(request), page_line.comment)
            else:
               line_of_text = line_of_text + ' %s</span>' % (page_line.getEditor(request))

            line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="%s/Bookmarks?action=favorite&delete=%s">Remove</a>]</span>' % (request.getScriptname(), wikiutil.quoteWikiname((page_line.pagename)))
            line_of_text = line_of_text + '</td></tr>'

          seen_list.append((pagename, line_of_text))

    for pagename, line in seen_list:
        request.write(line)

    request.write('</table>') 

    return ''
