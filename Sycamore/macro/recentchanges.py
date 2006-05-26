# -*- coding: iso-8859-1 -*-
"""
    Sycamore - RecentChanges Macro

    Parameter "ddiffs" by Ralf Zosel <ralf@zosel.com>, 04.12.2003.

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>, 2005-2006 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO, urllib
from Sycamore import config, user, util, wikiutil, wikidb
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
	   request.req_cache['pagenames'][pagename.lower()] = pagename
	else: request.req_cache['pagenames'][pagename.lower()] = False
	break
      

def format_page_edits(macro, lines, showcomments, bookmark, formatter):
    request = macro.request
    _ = request.getText
    d = {} # dict for passing stuff to theme
    line = lines[0]
    d['show_comments'] = showcomments
    pagename = line.pagename
    tnow = time.time()
    is_new = lines[-1].action == 'SAVENEW'
    is_event = lines[-1].action == 'NEWEVENT'
    # check whether this page is newer than the user's bookmark
    hilite = line.ed_time > (bookmark or line.ed_time)
    page = Page(line.pagename, request)
    getPageStatus(lines, pagename, macro.request)

    html_link = ''
    if not page.exists():
        # indicate page was deleted
        html_link = request.theme.make_icon('deleted', actionButton=True)
    elif is_new:
        # show "NEW" icon if page was created after the user's bookmark
        if len(lines) == 1: 
           html_link = request.theme.make_icon('new', actionButton=True)
        else:
           img = request.theme.make_icon('new', actionButton=True)
           html_link = wikiutil.link_tag(request,wikiutil.quoteWikiname(pagename) + "?action=diff", img)
    elif hilite:
        # show "UPDATED" icon if page was edited after the user's bookmark
        img = request.theme.make_icon('updated', actionButton=True)
        html_link = wikiutil.link_tag(request,
                                      "%s?action=diff&date=%s" % (wikiutil.quoteWikiname(pagename), str(bookmark)),
                                      img, formatter=macro.formatter, pretty_url=1)
    else:
        # show "DIFF" icon else
        img = request.theme.make_icon('diffrc', actionButton=True)
        html_link = wikiutil.link_tag(request,
                                      "%s?action=diff" % wikiutil.quoteWikiname(line.pagename),
                                      img, formatter=macro.formatter, pretty_url=1)

    # print name of page, with a link to it
    force_split = len(page.page_name) > _MAX_PAGENAME_LENGTH
    
    d['icon_html'] = html_link
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
               numsecs = int(tnow - line.ed_time)%60
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
			  lines[idx].action, page.proper_name()).render()
	comments.append(comment)
    
    d['changecount'] = len(lines)
    d['comments'] = comments

    img = request.theme.make_icon('info')
    info_html = wikiutil.link_tag(request,
                                  "%s?action=info" % wikiutil.quoteWikiname(line.pagename),
                                  img, formatter=macro.formatter, pretty_url=1)
    d['info_html'] = info_html
    
    return request.theme.recentchanges_entry(d)
    
def cmp_lines(first, second):
    return cmp(first[0].ed_time, second[0].ed_time)

def execute(macro, args, formatter=None, **kw):
    if not formatter: formatter = macro.formatter

    request = macro.request

    if config.relative_dir: add_on = '/'
    else: add_on = ''

    _ = request.getText

    d = {}
    page_path = request.getScriptname() + request.getPathinfo()
    pagename = request.getPathinfo()[1:]
    d['q_page_name'] = wikiutil.quoteWikiname(pagename)

    # flush output because getting all the changes may take a while in some cases
    # this may actually be bad for web server performance
    #request.flush()

    # set max size in days
    max_days = min(int(request.form.get('max_days', [0])[0]), _DAYS_SELECTION[-1])

    # get bookmark from valid user
    bookmark = request.user.getBookmark()

    # default to _MAX_DAYS for useres without bookmark
    if not max_days:
        max_days = _MAX_DAYS
    d['rc_max_days'] = max_days

    lines = wikidb.getRecentChanges(request, max_days=max_days, changes_since=bookmark)

    tnow = time.time()
    msg = ""

    showComments = request.user.getShowComments()
    d['show_comments_html'] = None
    d['show_comments'] = None
    d['show_comments'] = showComments
    if showComments == 1:
        d['show_comments_html'] = '[%s]' % wikiutil.link_tag(request, "%s?action=showcomments&hide=1" % pagename, "Hide comments")
    else:
        d['show_comments_html'] = '[%s]' % wikiutil.link_tag(request, "%s?action=showcomments" % pagename, "Show comments")

    # add bookmark link if valid user
    d['rc_curr_bookmark'] = None
    d['rc_update_bookmark'] = None
    if request.user.valid:
        d['rc_curr_bookmark'] = _('(will show you only changes made since you last pressed \'clear\')')
        if bookmark:
            d['rc_curr_bookmark'] = "%s [%s]" % ( _('(currently set to %s)') % request.user.getFormattedDateTime(bookmark), 
                 wikiutil.link_tag(request, "%s?action=bookmark&time=del" % pagename, _("Show all changes")) )

        d['rc_update_bookmark'] = wikiutil.link_tag(
            request,
	    "%s?action=bookmark&time=%d" % (pagename, tnow), 
            _("Clear observed changes")
            )
    
        
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
    ignore_pages = {}

    today = request.user.getTime(tnow)[0:3]
    this_day = today
    day_count = 0

    for line in lines:
        line.page = Page(line.pagename, macro.request)
	# 2006-05 calling may here is too expensive.  just show them the page.  on the off change they can't read it, then, well, clicking on it won't be too productive for them.
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
            for page in pages:
                ignore_pages[page] = None
            pages = pages.values()
            pages.sort(cmp_lines)
            pages.reverse()
            d['show_comments'] = showComments        
            d['bookmark_link_html'] = None
            if request.user.valid:
                d['bookmark_link_html'] = wikiutil.link_tag(
                    request,
                        pagename + "?action=bookmark&time=%d" % (pages[0][0].ed_time,),
                        _("set bookmark")
                        )
            d['date'] = request.user.getFormattedDateWords(pages[0][0].ed_time)
            request.write(request.theme.recentchanges_daybreak(d))
            
            for page in pages:
                request.write(format_page_edits(macro, page, showComments, bookmark, formatter))
            day_count += 1
            pages = {}
            if max_days and (day_count >= max_days):
                break

        elif this_day != day:
            # new day but no changes
            this_day = day

        if ignore_pages.has_key(line.pagename):
            continue
        
        # end listing by default if user has a bookmark and we reached it
        if not max_days and not hilite:
            msg = _('<h5>Bookmark reached</h5>')
            break

        if pages.has_key(line.pagename):
            pages[line.pagename].append(line)
        else:
            pages[line.pagename] = [line]
    else:
        if len(pages) > 0:
            # end of loop reached: print out stuff 
            # XXX duplicated code from above
            # but above does not trigger if have the first day in wiki history
            for page in pages:
                ignore_pages[page] = None
            pages = pages.values()
            pages.sort(cmp_lines)
            pages.reverse()
            
            d['bookmark_link_html'] = None
            if request.user.valid:
                d['bookmark_link_html'] = wikiutil.link_tag(
                    request,
                        "%s?action=bookmark&time=%d" % (pagename, pages[0][0].ed_time),
                        _("set bookmark")
                        )
            d['date'] = request.user.getFormattedDateWords(pages[0][0].ed_time)
            request.write(request.theme.recentchanges_daybreak(d))
            
            for page in pages:
                request.write(format_page_edits(macro, page, showComments, bookmark, formatter))
    

    d['rc_msg'] = msg
    request.write(request.theme.recentchanges_footer(d))

    return ''


