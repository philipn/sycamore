# -*- coding: iso-8859-1 -*-
"""
    Sycamore - RecentChanges Macro

    Parameter "ddiffs" by Ralf Zosel <ralf@zosel.com>, 04.12.2003.

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>, 2005-2007 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO, urllib
from Sycamore import config, user, util, wikiutil, wikidb, farm
from Sycamore.wikidb import getEditor
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

Dependencies = ["time"]

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

def group_changes_by_day(lines, tnow, max_days, request):
    days_and_lines = []
    today = request.user.getTime(tnow)[0:3]
    this_day = today
    days_lines = []
    day_tm = tnow
    days_total = 1
    for line in lines:
        line.time_tuple = request.user.getTime(line.ed_time)
        day = line.time_tuple[0:3]
        
        if this_day != day:
            this_day = day
            days_and_lines.append((day_tm, days_lines))
            days_lines = []
            day_tm = line.ed_time
            days_total += 1
            if days_total > max_days:
                break

        days_lines.append(line)

    # final item
    if days_lines:
        days_and_lines.append((day_tm, days_lines))

    return days_and_lines

def group_changes_by_wiki(lines, request):
    wikis = request.user.getWatchedWikis()
    for wiki in wikis:
        wikis[wiki] = []

    for line in lines: 
        wikis[line.wiki_name].append(line)

    return wikis

def is_new_page(lines):
    """
    Looks at lines and determines if the page is newly created or not.
    """
    for line in lines:
        if line.action == 'SAVENEW':
            return True
    return False

def format_page_edit_icon(request, lines, page, hilite, bookmark, formatter):
    is_new = is_new_page(lines)
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
           html_link = '<div class="rcTag"><div class="rcTagNew">%s</div></div>' % page.link_to(querystr=diff, text=tag, absolute=True)
    elif hilite:
        # show bolder status if page was edited after the user's rc bookmark
        tag = 'changes'
        html_link = '<div class="rcTag"><div class="rcTagChanges">%s</div></div>' % page.link_to(
                                      querystr="action=diff&date=%s" % str(bookmark),
                                      text=tag, absolute=True)
    else:
        # show normal changes link else
        tag = 'changes'
        diff = 'action=diff&at_date=%s' % (repr(lines[0].ed_time))
        html_link = '<div class="rcTag"><div class="rcTagChanges">%s</div></div>' % page.link_to(
                                      querystr=diff,
                                      text=tag, absolute=True)

    return html_link
      
def format_page_edits(request, lines, showcomments, bookmark, formatter, wiki_global=False, grouped_by_wiki=False):
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
    getPageStatus(lines, pagename, request) # we can infer 'exists?' from current rc data in some cases

    html_link = format_page_edit_icon(request, lines, page, hilite, bookmark, formatter)
    
    # print name of page, with a link to it
    force_split = len(page.page_name) > _MAX_PAGENAME_LENGTH
    
    d['rc_tag_html'] = html_link

    if wiki_global:
        if not grouped_by_wiki:
            on_wiki = ' <span class="minorText">(on %s)</span>' % farm.link_to_wiki(line.wiki_name, formatter)
        else:
            on_wiki = ''
        d['pagelink_html'] = '%s%s' % (page.link_to(text=pagename, absolute=True), on_wiki)
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
            name = getEditor(lines[idx], request)
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

def print_day(day, request, d):
    d['date'] = request.user.getFormattedDateWords(day)
    request.write(request.theme.recentchanges_daybreak(d))

def print_changes(lines, bookmark, tnow, max_days, showComments, d, wiki_global, macro, request, formatter, grouped=False):
    pages = {}
    today = request.user.getTime(tnow)[0:3]
    this_day = today
    day_count = 0

    for line in lines:
        line.page = Page(line.pagename, macro.request, wiki_name=line.wiki_name)
        if not line.ed_time: continue
        line.time_tuple = request.user.getTime(line.ed_time)
        day = line.time_tuple[0:3]
        hilite = line.ed_time > (bookmark or line.ed_time)
        
        if pages.has_key((line.pagename, line.wiki_name)):
            pages[(line.pagename, line.wiki_name)].append(line)
        else:
            pages[(line.pagename, line.wiki_name)] = [line]

    if len(pages) > 0:
        pages = pages.values()
        pages.sort(cmp_lines)
        pages.reverse()
        
        for page_line in pages:
            request.write(format_page_edits(request, page_line, showComments, bookmark, formatter, wiki_global=wiki_global, grouped_by_wiki=grouped))

def cmp_lines(first, second):
    return cmp(first[0].ed_time, second[0].ed_time)

def execute(macro, args, formatter=None, **kw):
    if not formatter: formatter = macro.formatter
    
    request = macro.request
    _ = request.getText

    # set up javascript entry grouping -- this happens when the page renders
    request.write("""<script type="text/javascript">onLoadStuff.push('groupAllRcChanges();');</script>\n""")

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

    # set max size in days
    max_days = min(int(request.form.get('max_days', [0])[0]), _DAYS_SELECTION[-1])

    # get bookmark from valid user
    bookmark = request.user.getBookmark(wiki_global=wiki_global)

    # default to _MAX_DAYS for users without rc bookmark
    if not max_days:
        max_days = _MAX_DAYS
    d['rc_max_days'] = max_days

    if wiki_global:
        watched_wikis = request.user.getWatchedWikis()
        lines = wikidb.getRecentChanges(request, max_days=max_days, changes_since=bookmark, wiki_global=wiki_global, on_wikis=watched_wikis)
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
        if wiki_global:
            if request.user.getRcGroupByWiki():
                d['rc_group_by_wiki'] = ' | %s' % rc_page.link_to(querystr="action=groupbywiki&off=1", text="Group all changes together")
            else:
                d['rc_group_by_wiki'] = ' | %s' % rc_page.link_to(querystr="action=groupbywiki", text="Group changes by wiki")
        else:
            d['rc_group_by_wiki'] = ''
        
    # give known user the option to extend the normal display
    if request.user.valid:
        d['rc_days'] = _DAYS_SELECTION
    else:
        d['rc_days'] = []

    request.write(request.theme.recentchanges_header(d))
    
    if not lines:
        if wiki_global:
            request.write('<p>This page shows you changes on <strong>all</strong> of the wikis you are watching!</p>')
            if not watched_wikis:
                request.write("""<p>You are not watching any wikis, though.  To watch a wiki, simply go to the wiki you're interested in and click the "watch this wiki" link next to your user settings in the upper right.</p>""")
        if not wiki_global or watched_wikis:
            request.write("<p>No recent changes.  Quick &mdash; change something while nobody's looking!</p>")

    lines_by_day = group_changes_by_day(lines, tnow, max_days, request)
    for day, lines in lines_by_day:
        print_day(day, request, d)
        if request.user.getRcGroupByWiki():
            lines_grouped = group_changes_by_wiki(lines, request)
            wiki_names_sorted = lines_grouped.keys()
            wiki_names_sorted.sort()
            for wiki_name in wiki_names_sorted:
                if lines_grouped[wiki_name]:
                    request.write('<h3 style="padding: .15em;">%s:</h3>' % farm.link_to_wiki(wiki_name, formatter))
                    print_changes(lines_grouped[wiki_name], bookmark, tnow, max_days, showComments, d, wiki_global, macro, request, formatter, grouped=True)
        else:
            print_changes(lines, bookmark, tnow, max_days, showComments, d, wiki_global, macro, request, formatter)
        

    d['rc_msg'] = msg
    request.write(request.theme.recentchanges_footer(d))

    return ''


