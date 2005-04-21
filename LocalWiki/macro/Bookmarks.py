# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Bookmarks.  I started by modifying the LocalWiki RecentChanges.

    Parameter "ddiffs" by Ralf Zosel <ralf@zosel.com>, 04.12.2003.

    @copyright: 2005 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO, os
from LocalWiki import config, user, util, wikiutil, wikixml
from LocalWiki.Page import Page
from LocalWiki.logfile import editlog

_DAYS_SELECTION = [1, 2, 3, 7]
_MAX_DAYS = 2
_MAX_PAGENAME_LENGTH = 15 # 35

#############################################################################
### Bookmarks Macro
#############################################################################

Dependencies = ["time"] # ["user", "pages", "pageparams", "bookmark"]

def execute(macro, args, **kw):

    request = macro.request
    _ = request.getText
    pagename = macro.formatter.page.page_name

    tnow = time.time()
    msg = ""

    pages = {}
    ignore_pages = {}

    today = request.user.getTime(tnow)[0:3]
    this_day = today
    day_count = 0

    local_favoriteList = request.user.getFavoriteList()
    # make sure they can read the pages they add to the list

    from LocalWiki.formatter.text_html import Formatter
    from LocalWiki import user
    formatter = Formatter(request)
    find_month = { 1:"Jan.", 2:"Feb.", 3:"Mar.", 4:"Apr.", 5:"May", 6:"Jun.", 7:"Jul.", 8:"Aug.", 9:"Sept.", 10:"Oct.", 11:"Nov.", 12:"Dec." }   

    if config.relative_dir: add_on = '/'
    else: add_on = ''

    request.write('<table>')
    if not local_favoriteList:
        request.write('<p>Bookmarks let you easily keep track of pages you think are interesting.</p><p><i>You have no Bookmarks.  To add a page to your Bookmarks list, simply go to "Info" on the page you wish to add and click "Add this page to your wiki Bookmarks."</i></p>')

    showed_update = False
    seen_list = []
    line_of_text = ''
    for pagename in local_favoriteList:
     if os.path.exists(config.data_dir + '/pages/' + wikiutil.quoteFilename(pagename)):
          log = editlog.EditLog(config.data_dir + '/pages/' + wikiutil.quoteFilename(pagename) + '/last-edited')
	  # hack..
	  found = False
	  for pageline in log.lastline():
		found = True
		line = pageline
		break	
	   # in case there's no editlog info :0
	  if not found:
		line_of_text = '<tr><td valign="center" class="rcpagelink">' + '<font style="font-size: 10px;">[diff]</font> &nbsp;' + formatter.pagelink(pagename) + ' &nbsp;<span align="right" class="favtime"> no edit information found '
		seen_list.append((pagename, line_of_text))
		continue
	    
          bookmark = request.user.getFavBookmark(line.pagename)


          line.time_tuple = request.user.getTime(line.ed_time)
          day = line.time_tuple[0:3]

          if line.ed_time > bookmark:
            # We do bold
            line_of_text = '<tr><td valign="center" class="rcpagelink">' + '<strong style="font-size: 10px;">[<a href="/%s%s' % (config.relative_dir, add_on) + line.pagename + '?action=diff&date2=0&date1=' + str(bookmark) + '">diff</a>]</strong> &nbsp;' +  formatter.pagelink(line.pagename)
            line_of_text = line_of_text + " &nbsp;" + '<b><span align="right" style="font-size: 12px;">' + 'last modified '
            line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2])
            line_of_text = line_of_text + time.strftime(" at %I:%M %p by</span></b>", line.time_tuple) + '<span class="faveditor">'
            if line.comment:
              line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (formatter.pagelink(user.User(request, line.userid).name), line.comment)
            else:
              line_of_text = line_of_text + ' %s</span>' % (formatter.pagelink(user.User(request, line.userid).name))
            line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="/%s%sBookmarks?action=favorite&delete=%s">Remove</a>]</span>' % (config.relative_dir, add_on, wikiutil.quoteFilename(line.pagename)) + '</td></tr>'

          else:
             # We don't do bold
            line_of_text = '<tr><td valign="center" class="rcpagelink">' + '<font style="font-size: 10px;">[<a href="/%s%s' % (config.relative_dir, add_on) + line.pagename + '?action=diff&date2=0&date1=' + str(bookmark) + '">diff</a>]</font> &nbsp;' + formatter.pagelink(line.pagename) + ' &nbsp;<span align="right" class="favtime">last modified '
            line_of_text = line_of_text + '%s %s' % (find_month[day[1]], day[2]) 
            line_of_text = line_of_text + time.strftime(" at %I:%M %p by</span>", line.time_tuple) + '<span class="faveditor">'
            if line.comment:
              line_of_text = line_of_text + ' %s</span><span class="favcomment"> (%s)</span>' % (formatter.pagelink(user.User(request, line.userid).name), line.comment)
            else:
               line_of_text = line_of_text + ' %s</span>' % (formatter.pagelink(user.User(request, line.userid).name))

            line_of_text = line_of_text + '<span style="font-size:12px;">&nbsp;&nbsp;[<a href="/%s%sBookmarks?action=favorite&delete=%s">Remove</a>]</span>' % (config.relative_dir, add_on, wikiutil.quoteFilename(line.pagename))
            line_of_text = line_of_text + '</td></tr>'

          seen_list.append((pagename, line_of_text))

    seen_list.sort(lambda x, y: cmp(str.lower(x[0]), str.lower(y[0])))
    for pagename, line in seen_list:
        request.write(line)

    request.write('</table>') 

    return ''
