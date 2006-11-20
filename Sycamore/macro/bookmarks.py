# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Bookmarks display macro.

    @copyright: 2005-2006 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO, os, urllib
from Sycamore import config, user, util, wikiutil, wikidb, farm
from Sycamore.macro.recentchanges import format_page_edit_icon
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

def groupFavorites(changed_favorites, all_favorites):
    def cmp_lines_edit(first, second):
        return cmp(first.ed_time, second.ed_time)
       
    def cmp_lines_name(first, second):
        return cmp(first.pagename, second.pagename)

    fav_dict = {}
    # create dictionary for favorites
    for favorite in all_favorites:
        editline = wikidb.EditLine((favorite.page_name, 0, None, '', '', None))
        editline.wiki_name = favorite.wiki_name
        fav_dict[(favorite.page_name, favorite.wiki_name)] = [editline]

    for page_line in changed_favorites:
      lower_page_name = page_line.pagename.lower()
      if fav_dict[(lower_page_name, page_line.wiki_name)][0].ed_time:
        fav_dict[(lower_page_name, page_line.wiki_name)].append(page_line)
      else:
        fav_dict[(lower_page_name, page_line.wiki_name)] = [page_line]

    for lower_page_name, wiki_name in fav_dict:
      if len(fav_dict[(lower_page_name, wiki_name)]) > 1: # more than one change
        fav_dict[(lower_page_name, wiki_name)].sort(cmp_lines_edit)
      fav_dict[(lower_page_name, wiki_name)] = fav_dict[(lower_page_name, wiki_name)][-1]	# grab only the most recent change

    favorites = fav_dict.values()
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
      if args and args == 'global':
          wiki_global = True
      else:
          wiki_global = False

      all_favorites = request.user.getFavoriteList(wiki_global=wiki_global)
      changed_favorites = wikidb.getRecentChanges(request, per_page_limit=1, userFavoritesFor=request.user.id, wiki_global=wiki_global)
      local_favoriteList = groupFavorites(changed_favorites, all_favorites)

      from Sycamore.formatter.text_html import Formatter
      from Sycamore import user
      formatter = Formatter(request)
      find_month = { 1:"Jan.", 2:"Feb.", 3:"Mar.", 4:"Apr.", 5:"May", 6:"Jun.", 7:"Jul.", 8:"Aug.", 9:"Sept.", 10:"Oct.", 11:"Nov.", 12:"Dec." }   

    if not wiki_global:
        rss_html = '<link rel=alternate type="application/rss+xml" href="%s/%s?action=rss_rc&amp;user=%s" title="Recent Changes on %s\'s bookmarks"><div style="float:right;"><a title="%s\'s Bookmarks RSS Feed" href="%s/%s?action=rss_rc&amp;user=%s" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a></div>' % (request.getScriptname(), wikiutil.quoteWikiname(pagename_propercased), urllib.quote_plus(request.user.propercased_name), request.user.propercased_name, request.user.propercased_name, request.getScriptname(), wikiutil.quoteWikiname(pagename_propercased), urllib.quote_plus(request.user.propercased_name))
    else:
        rss_html = '<link rel=alternate type="application/rss+xml" href="%s/%s?action=rss_rc&amp;user=%s" title="Recent Changes on %s\'s bookmarks"><div style="float:right;"><a title="%s\'s Interwiki Bookmarks RSS Feed" href="%s/%s?action=rss_rc&amp;user=%s&amp;global=1" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a></div>' % (request.getScriptname(), wikiutil.quoteWikiname(pagename_propercased), urllib.quote_plus(request.user.propercased_name), request.user.propercased_name, request.user.propercased_name, request.getScriptname(), wikiutil.quoteWikiname(pagename_propercased), urllib.quote_plus(request.user.propercased_name))
    request.write(rss_html)
    request.write('<div class="bookmarks">')
    if not local_favoriteList:
      request.write('<p>Bookmarks let you easily keep track of pages you think are interesting.</p><p><i>You have no Bookmarks.  To add a page click "Bookmark this page" at the bottom of the page.</i></p>')

    showed_update = False
    seen_list = []
    line_of_text = ''
    for page_line in local_favoriteList:
          page = Page(page_line.pagename, request, wiki_name=page_line.wiki_name)
          page_line.comment = Comment(request, page_line.comment, page_line.action, page=page).render()
          bookmark = request.user.getFavBookmark(page)

	  # in the case of uploads/deletes of images, etc we'd like to show a useful comment
          page_line.time_tuple = request.user.getTime(page_line.ed_time)
          day = page_line.time_tuple[0:3]
          if not wiki_global:
            wiki_link = ''
          else:
            wiki_link = '<span class="minorText">(on %s)</span>' % farm.link_to_wiki(page_line.wiki_name, formatter)

          if page_line.ed_time > bookmark:
            # We do bold
            edit_icon = format_page_edit_icon(request, [page_line], page, True, bookmark, formatter)
            line_of_text = '<div class="rcpagelink"><b>%s</b> &nbsp; %s%s<b>' % (edit_icon, page.link_to(), wiki_link)
            line_of_text = line_of_text + " &nbsp;" + '<span align="right" style="font-size: 12px;">' + 'last modified '
            line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2])
            line_of_text = line_of_text + time.strftime(" at %I:%M %p</b> by</span>", page_line.time_tuple) + '<span class="faveditor">'
            if page_line.comment:
              line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (page_line.getEditor(request), page_line.comment)
            else:
              line_of_text = line_of_text + ' %s</span>' % (page_line.getEditor(request))
            line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="%s/%s?action=favorite&delete=%s&wiki_name=%s">Remove</a>]</span>' % (request.getScriptname(), wikiutil.quoteWikiname(macro.formatter.page.proper_name()), wikiutil.quoteWikiname(page_line.pagename), page.wiki_name) + '</div>'

          else:
            edit_icon = format_page_edit_icon(request, [page_line], page, False, bookmark, formatter)
            # We don't do bold
            if page_line.ed_time: # page has been created
                line_of_text = '<div class="rcpagelink">%s &nbsp; %s%s &nbsp;<span " class="favtime">last modified ' % (edit_icon, page.link_to(), wiki_link)
                line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2]) 
                line_of_text = line_of_text + time.strftime(" at %I:%M %p by</span>", page_line.time_tuple) + '<span class="faveditor">'
                if page_line.comment:
                  line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (page_line.getEditor(request), page_line.comment)
                else:
                   line_of_text = line_of_text + ' %s</span>' % (page_line.getEditor(request))

                line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="%s/%s?action=favorite&delete=%s&wiki_name=%s">Remove</a>]</span>' % (request.getScriptname(), wikiutil.quoteWikiname(macro.formatter.page.proper_name()), wikiutil.quoteWikiname(page_line.pagename), page.wiki_name)
                line_of_text = line_of_text + '</div>'
            else: # page has NOT been created
                line_of_text = '<div class="rcpagelink">%s &nbsp; %s%s &nbsp;<span align="right" class="favtime">page has not been created yet</span>' % (edit_icon, page.link_to(), wiki_link)
                line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="%s/%s?action=favorite&delete=%s&wiki_name=%s">Remove</a>]</span>' % (request.getScriptname(), wikiutil.quoteWikiname(macro.formatter.page.proper_name()), wikiutil.quoteWikiname(page_line.pagename), page.wiki_name)
                line_of_text = line_of_text + '</div>'


          seen_list.append((pagename, line_of_text))

    for pagename, line in seen_list:
        request.write(line)

    request.write('</div>') 

    return ''
