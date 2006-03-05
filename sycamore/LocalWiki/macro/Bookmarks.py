# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Bookmarks.  I started by modifying the LocalWiki RecentChanges.

    Parameter "ddiffs" by Ralf Zosel <ralf@zosel.com>, 04.12.2003.

    @copyright: 2005 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO, os, urllib
from LocalWiki import config, user, util, wikiutil, wikixml, wikidb
from LocalWiki.widget.comments import Comment

_DAYS_SELECTION = [1, 2, 3, 7]
_MAX_DAYS = 2
_MAX_PAGENAME_LENGTH = 15 # 35

#############################################################################
### Bookmarks Macro
#############################################################################

# let's not bother trying to cache this macro
Dependencies = ["time"] # ["user", "pages", "pageparams", "bookmark"]

def execute(macro, args, formatter=None, **kw):
    if not formatter: formatter = macro.formatter
    request = macro.request
    _ = request.getText
    pagename = macro.formatter.page.page_name
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

      from LocalWiki.formatter.text_html import Formatter
      from LocalWiki import user
      formatter = Formatter(request)
      find_month = { 1:"Jan.", 2:"Feb.", 3:"Mar.", 4:"Apr.", 5:"May", 6:"Jun.", 7:"Jul.", 8:"Aug.", 9:"Sept.", 10:"Oct.", 11:"Nov.", 12:"Dec." }   

      if config.relative_dir: add_on = '/'
      else: add_on = ''

    rss_html = '<link rel=alternate type="application/rss+xml" href="/%s%s%s?action=rss_rc&amp;user=%s" title="Recent Changes on %s\'s bookmarks"><div style="float:right;"><a title="%s\'s Bookmarks RSS Feed" href="/%s%s%s?action=rss_rc&amp;user=%s" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a></div>' % (config.relative_dir, add_on, wikiutil.quoteWikiname(pagename), urllib.quote_plus(request.user.name), request.user.name, request.user.name, config.relative_dir, add_on, wikiutil.quoteWikiname(pagename), urllib.quote_plus(request.user.name))
    request.write(rss_html)
    request.write('<table>')
    if not local_favoriteList:
      request.write('<p>Bookmarks let you easily keep track of pages you think are interesting.</p><p><i>You have no Bookmarks.  To add a page to your Bookmarks list, simply go to "Info" on the page you wish to add and click "Add this page to your wiki Bookmarks."</i></p>')

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
            line_of_text = '<tr><td valign="center" class="rcpagelink">' + '<strong style="font-size: 10px;">[<a href="/%s%s' % (config.relative_dir, add_on) + wikiutil.quoteWikiname(page_line.pagename) + '?action=diff&date2=0&date1=' + str(bookmark) + '">diff</a>]</strong> &nbsp;' +  formatter.pagelink(page_line.pagename)
            line_of_text = line_of_text + " &nbsp;" + '<b><span align="right" style="font-size: 12px;">' + 'last modified '
            line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2])
            line_of_text = line_of_text + time.strftime(" at %I:%M %p by</span></b>", page_line.time_tuple) + '<span class="faveditor">'
            if page_line.comment:
              line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (formatter.pagelink(user.User(request, page_line.userid).name), page_line.comment)
            else:
              line_of_text = line_of_text + ' %s</span>' % (formatter.pagelink(user.User(request, page_line.userid).name))
            line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="/%s%sBookmarks?action=favorite&delete=%s">Remove</a>]</span>' % (config.relative_dir, add_on, wikiutil.quoteWikiname(page_line.pagename)) + '</td></tr>'

          else:
             # We don't do bold
            line_of_text = '<tr><td valign="center" class="rcpagelink">' + '<font style="font-size: 10px;">[<a href="/%s%s' % (config.relative_dir, add_on) + wikiutil.quoteWikiname(page_line.pagename) + '?action=diff">diff</a>]</font> &nbsp;' + formatter.pagelink(page_line.pagename) + ' &nbsp;<span align="right" class="favtime">last modified '
            line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2]) 
            line_of_text = line_of_text + time.strftime(" at %I:%M %p by</span>", page_line.time_tuple) + '<span class="faveditor">'
            if page_line.comment:
              line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (formatter.pagelink(user.User(request, page_line.userid).name), page_line.comment)
            else:
               line_of_text = line_of_text + ' %s</span>' % (formatter.pagelink(user.User(request, page_line.userid).name))

            line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="/%s%sBookmarks?action=favorite&delete=%s">Remove</a>]</span>' % (config.relative_dir, add_on, wikiutil.quoteWikiname((page_line.pagename)))
            line_of_text = line_of_text + '</td></tr>'

          seen_list.append((pagename, line_of_text))

    for pagename, line in seen_list:
        request.write(line)

    request.write('</table>') 

    return ''
