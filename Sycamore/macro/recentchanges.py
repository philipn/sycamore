# -*- coding: iso-8859-1 -*-
"""
    Sycamore - RecentChanges Macro

    Parameter "ddiffs" by Ralf Zosel <ralf@zosel.com>, 04.12.2003.

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>, 2005-2006 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO, urllib
from Sycamore import config, user, util, wikiutil, wikidb, farm
from Sycamore.Page import Page
from Sycamore.formatter.text_html import Formatter
from Sycamore.widget.comments import Comment

_DAYS_SELECTION = [1, 2, 3, 7]
_MAX_DAYS = 2
_MAX_PAGENAME_LENGTH = 15 # 35

file_action = 'Files'

#############################################################################
### RecentChanges Macro
#############################################################################

Dependencies = ["time"] # ["user", "pages", "pageparams", "bookmark"]

def getPageStatus(lines, pagename, request):
    """
    Given some relevant lines for recent changes, we try our best to figure out if the page exists.
    If we fail, then we will end up calling memcached/db.
    """
    for edit in lines:
      if edit.action != 'ATTNEW' and edit.action != 'ATTDEL':
        if edit.action != 'DELETE':
	   request.req_cache['pagenames'][(pagename.lower(), request.config.wiki_name)] = pagename
	else: request.req_cache['pagenames'][(pagename.lower(), request.config.wiki_name)] = False
	break

def format_page_edit_icon(request, lines, page, hilite, bookmark, formatter):
    is_new = lines[-1].action == 'SAVENEW'
    is_event = lines[-1].action == 'NEWEVENT'
    if not page.exists():
        if lines[0].ed_time:
            # indicate page was deleted
            html_link = '<div class="rcTag"><div class="rcTagDeleted">deleted</div></div>'
        else:
            # indicate page was never created
            html_link = '<div class="rcTag">&nbsp;</div>'
    elif is_new:
        # show "NEW" icon if page was created after the user's bookmark
        if len(lines) == 1: 
           html_link = '<div class="rcTag"><div class="rcTagNew">new</div></div>'
        else:
           tag = 'changes'
           diff = 'action=diff&at_date=%s' % (repr(lines[0].ed_time))
           html_link = '<div class="rcTag"><div class="rcTagNew">%s</div></div>' % page.link_to(querystr=diff, text=tag)
    elif hilite:
        # show bolder status if page was edited after the user's rc bookmark
        tag = 'changes'
        html_link = '<div class="rcTag"><div class="rcTagChanges">%s</div></div>' % page.link_to(
                                      querystr="action=diff&date=%s" % str(bookmark),
                                      text=tag)
    else:
        # show normal changes link else
        tag = 'changes'
        diff = 'action=diff&at_date=%s' % (repr(lines[0].ed_time))
        html_link = '<div class="rcTag"><div class="rcTagChanges">%s</div></div>' % page.link_to(
                                      querystr=diff,
                                      text=tag)

    return html_link
      
def format_page_edits(request, lines, showcomments, bookmark, formatter, wiki_global=False):
    _ = request.getText
    d = {} # dict for passing stuff to theme
    line = lines[0]
    d['show_comments'] = showcomments
    pagename = line.pagename
    tnow = time.time()
    
    # check whether this page is newer than the user's bookmark
    hilite = line.ed_time > (bookmark or line.ed_time)
    if wiki_global:
        page = Page(line.pagename, request, wiki_name=line.wiki_name)
    else:
        page = Page(line.pagename, request)
    getPageStatus(lines, pagename, request) # can infer 'exists?' from current rc data?

    html_link = format_page_edit_icon(request, lines, page, hilite, bookmark, formatter)
    
    # print name of page, with a link to it
    force_split = len(page.page_name) > _MAX_PAGENAME_LENGTH
    
    d['rc_tag_html'] = html_link

    if wiki_global:
        d['pagelink_html'] = '%s <span class="minorText">(on %s)</span>' % (page.link_to(text=pagename), farm.link_to_wiki(line.wiki_name, formatter))
    else:
        d['pagelink_html'] = page.link_to(text=pagename) 
    
    # print time of change
    d['time_html'] = None
    if config.changed_time_fmt:
        tdiff = int(tnow - line.ed_time) / 60
        if tdiff < 1440:
            numhrs = int(tdiff/60)
            nummins = tdiff%60
            txthrs = ""
            txttime = ""
            if numhrs == 1:
               txthrs = '1 hour'
            if numhrs > 1:
               txthrs = '%s hours' % str(numhrs)
            txttime = txthrs
            if nummins == 1:
               txttime = '%s 1 minute' % str(txthrs)
            if nummins > 1:
               txttime = '%s %s minutes' % (str(txthrs), str(nummins))
            if nummins == 0 and numhrs == 0:
               numsecs = int(tnow - line.ed_time) % 60
               txttime = '%s second' % str(numsecs)
               if numsecs > 1:
                 txttime = '%ss' % txttime
            d['time_html'] = '%s ago' % txttime
        else:
            d['time_html'] = time.strftime("at %I:%M %p", line.time_tuple)
    
    # print editor name or IP
    d['editors'] = []
    if config.show_hosts:
        for idx in range(len(lines)):
            name = lines[idx].getEditor(request)
            ip = lines[idx].host
            d['editors'].append((name,ip))

    comments = []
    for idx in range(len(lines)):
        comment = Comment(request, lines[idx].comment,
			  lines[idx].action, page).render()
	comments.append(comment)
    
    d['changecount'] = len(lines)
    d['comments'] = comments

    return request.theme.recentchanges_entry(d)
    
def cmp_lines(first, second):
    return cmp(first[0].ed_time, second[0].ed_time)

def execute(macro, args, formatter=None, **kw):
    if not formatter: formatter = macro.formatter

    request = macro.request
    _ = request.getText

    pagename = formatter.page.page_name
    q_pagename = wikiutil.quoteWikiname(pagename)
    rc_page = Page(pagename, request)

    d = {}
    d['q_page_name'] = q_pagename
    d['page'] = rc_page

    if args == 'global':
        wiki_global = True
    else:
        wiki_global = False

    # flush output because getting all the changes may take a while in some cases
    # this may actually be bad for web server performance
    #request.flush()

    # set max size in days
    max_days = min(int(request.form.get('max_days', [0])[0]), _DAYS_SELECTION[-1])

    # get bookmark from valid user
    bookmark = request.user.getBookmark(wiki_global=wiki_global)

    # default to _MAX_DAYS for useres without bookmark
    if not max_days:
        max_days = _MAX_DAYS
    d['rc_max_days'] = max_days

    if wiki_global:
        lines = wikidb.getRecentChanges(request, max_days=max_days, changes_since=bookmark, wiki_global=wiki_global, on_wikis=request.user.getWatchedWikis())
    else:
        lines = wikidb.getRecentChanges(request, max_days=max_days, changes_since=bookmark, wiki_global=wiki_global)

    tnow = time.time()
    msg = ""

    showComments = request.user.getShowComments()
    d['show_comments_html'] = None
    d['show_comments'] = None
    d['show_comments'] = showComments
    if showComments == 1:
        d['show_comments_html'] = rc_page.link_to(querystr="action=showcomments&hide=1", text="Hide comments")
    else:
        d['show_comments_html'] = rc_page.link_to(querystr="action=showcomments", text="Show comments")

    # add bookmark link if valid user
    d['rc_curr_bookmark'] = None
    d['rc_update_bookmark'] = None
    if request.user.valid:
        d['rc_curr_bookmark'] = ''
        if wiki_global:
            globalstr = '&global=1'
        else:
            globalstr = ''
        if bookmark:
            d['rc_curr_bookmark'] = " | %s" % rc_page.link_to(querystr="action=bookmark&time=del%s" % globalstr, text=_("Show all changes"))
                 
        d['rc_update_bookmark'] = ' | %s' % rc_page.link_to(querystr="action=bookmark&time=%d%s" % (tnow, globalstr), text=_("Clear observed changes"))
        
    # give known user the option to extend the normal display
    if request.user.valid:
        d['rc_days'] = _DAYS_SELECTION
    else:
        d['rc_days'] = []

    ## add rss link
    #d['rc_rss_link'] = None
    #d['rc_rss_link'] = '<link rel=alternate type="application/rss+xml" href="%s/Recent_Changes?action=rss_rc" title="Recent Changes RSS Feed"><div style="float:right;"><a title="Recent Changes RSS Feed" href="%s/Recent_Changes?action=rss_rc" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a></div>' % (request.getScriptname(), request.getScriptname())

    request.write(request.theme.recentchanges_header(d))
    
    pages = {}
    today = request.user.getTime(tnow)[0:3]
    this_day = today
    day_count = 0
    
    if not lines:
        request.write("<p>No recent changes.  Quick &mdash; change something while nobody's looking!</p>")

    for line in lines:
        line.page = Page(line.pagename, macro.request)
	    # 2006-05 calling acl 'may' here is too expensive.  just show them the page.  on the off change they can't read it, then, well, clicking on it won't be too productive for them.
        #if not request.user.may.read(line.page):
        #    continue
        if not line.ed_time: continue
        line.time_tuple = request.user.getTime(line.ed_time)
        day = line.time_tuple[0:3]
        hilite = line.ed_time > (bookmark or line.ed_time)
        
        if (((this_day != day or (not hilite and not max_days)))
            and len(pages) > 0):
            # new day or bookmark reached: print out stuff 
            this_day = day
            pages = pages.values()
            pages.sort(cmp_lines)
            pages.reverse()
            d['show_comments'] = showComments        
            d['bookmark_link_html'] = None
            if request.user.valid:
                d['bookmark_link_html'] = rc_page.link_to(querystr="action=bookmark&time=%d" % pages[0][0].ed_time, text=_("set bookmark"))
            d['date'] = request.user.getFormattedDateWords(pages[0][0].ed_time)
            request.write(request.theme.recentchanges_daybreak(d))
            
            for page_line in pages:
                request.write(format_page_edits(request, page_line, showComments, bookmark, formatter, wiki_global=wiki_global))
            day_count += 1
            pages = {}
            if max_days and (day_count >= max_days):
                break

        elif this_day != day:
            # new day but no changes
            this_day = day

        # end listing by default if user has a bookmark and we reached it
        if not max_days and not hilite:
            msg = _('<h5>Bookmark reached</h5>')
            break

        if pages.has_key((line.pagename, line.wiki_name)):
            pages[(line.pagename, line.wiki_name)].append(line)
        else:
            pages[(line.pagename, line.wiki_name)] = [line]
    else:
        if len(pages) > 0:
            # end of loop reached: print out stuff 
            # XXX duplicated code from above
            # but above does not trigger if have the first day in wiki history
            pages = pages.values()
            pages.sort(cmp_lines)
            pages.reverse()
            
            d['bookmark_link_html'] = None
            if request.user.valid:
                d['bookmark_link_html'] = rc_page.link_to(querystr="action=bookmark&time=%d" % pages[0][0].ed_time,text=_("set bookmark"))
            d['date'] = request.user.getFormattedDateWords(pages[0][0].ed_time)
            request.write(request.theme.recentchanges_daybreak(d))
            
            for page_line in pages:
                request.write(format_page_edits(request, page_line, showComments, bookmark, formatter, wiki_global=wiki_global))
    

    d['rc_msg'] = msg
    request.write(request.theme.recentchanges_footer(d))

    return ''


