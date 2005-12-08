# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - RecentChanges Macro

    Parameter "ddiffs" by Ralf Zosel <ralf@zosel.com>, 04.12.2003.

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>, 2005 Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, time, cStringIO
from LocalWiki import config, user, util, wikiutil, wikixml, wikidb
from LocalWiki.Page import Page
from LocalWiki.logfile import editlog
from LocalWiki.formatter.text_html import Formatter

_DAYS_SELECTION = [1, 2, 3, 7]
_MAX_DAYS = 2
_MAX_PAGENAME_LENGTH = 15 # 35

#############################################################################
### RecentChanges Macro
#############################################################################

Dependencies = ["time"] # ["user", "pages", "pageparams", "bookmark"]




def format_comment(request, line):
    baseurl = request.getScriptname()
    file_action = 'Files'
    urlpagename = wikiutil.quoteWikiname(line.pagename)
    comment = line.comment
    _ = request.getText
    if line.action[:3] == 'ATT':
        import urllib
        filename = urllib.unquote(comment)
        if line.action == 'ATTNEW':
	    filename_link = '<a href="%s/%s?action=%s&amp;do=view&amp;target=%s">%s</a>' % (baseurl, urlpagename, file_action, filename, filename)
            comment = _("Upload of image '%s'.") % filename_link
	    return comment
        elif line.action == 'ATTDEL':
	    filename_link = '<a href="%s/%s?action=%s&amp;do=view&amp;target=%s">%s</a>' % (baseurl, urlpagename, file_action, filename, filename)
            comment = _("Image '%s' deleted.") % filename_link
	    return comment
        elif line.action == 'ATTDRW':
            comment = _("Drawing '%(filename)s' saved.") % {'filename': filename}
	    return wikiutil.escape(comment)

    elif line.action == 'DELETE':
           if comment: comment = "Page deleted: '%s'" % (comment)
	   else: comment = "Page deleted (no comment)"

    elif line.action == 'NEWEVENT':
	comment = "Event '%s' posted." % line.comment
	return wikiutil.escape(comment)
    elif line.action.find('/REVERT') != -1:
        datestamp = request.user.getFormattedDateTime(float(comment))
        comment = _("Revert to version dated %(datestamp)s.") % {'datestamp': datestamp}
	return wikiutil.escape(comment)
    return wikiutil.escape(comment)

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
    page = Page(line.pagename)

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
                                      wikiutil.quoteWikiname(pagename) + "?action=diff&date=" + str(bookmark),
                                      img, formatter=macro.formatter, pretty_url=1)
    else:
        # show "DIFF" icon else
        img = request.theme.make_icon('diffrc', actionButton=True)
        html_link = wikiutil.link_tag(request,
                                      wikiutil.quoteWikiname(line.pagename) + "?action=diff",
                                      img, formatter=macro.formatter, pretty_url=1)

    # print name of page, with a link to it
    force_split = len(page.page_name) > _MAX_PAGENAME_LENGTH
    
    d['icon_html'] = html_link
    d['pagelink_html'] = page.link_to(request, text=page.page_name)
    
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
               txthrs = str(numhrs) + ' hours'
            txttime = txthrs
            if nummins == 1:
               txttime = str(txthrs) + ' 1 minute'
            if nummins > 1:
               txttime = str(txthrs) + ' ' + str(nummins) + ' minutes' 
            if nummins == 0 and numhrs == 0:
               numsecs = int(tnow - line.ed_time)%60
               txttime = str(numsecs) + ' second'
               if numsecs > 1:
                 txttime = txttime + 's'
            d['time_html'] = '%s ago' % txttime
        else:
            d['time_html'] = time.strftime("at %I:%M %p", line.time_tuple)
    
    # print editor name or IP
    d['editors'] = None
    if config.show_hosts:
        if len(lines) > 1:
            counters = {}
            editorlist = [] 
            for idx in range(len(lines)):
                name = lines[idx].getEditor(request)
		ip = lines[idx].host
                editorlist.append((name,ip))
                #if not counters.has_key(name): counters[name] = []
                #counters[name].append(idx+1)
            #poslist = map(None,  counters.values(), counters.keys())
            #poslist.sort()
            ##request.write(repr(counters.items()))
            d['editors'] = []
            for name, ip in editorlist:
                d['editors'].append((name, ip))
        else:
            d['editors'] = []
            d['editors'].append((line.getEditor(request),line.host))

    comments = []
    for idx in range(len(lines)):
        comment = format_comment(request, lines[idx])
        comments.append(comment)
    
    d['changecount'] = len(lines)
    d['comments'] = comments

    img = request.theme.make_icon('info')
    info_html = wikiutil.link_tag(request,
                                  wikiutil.quoteWikiname(line.pagename) + "?action=info",
                                  img, formatter=macro.formatter, pretty_url=1)
    d['info_html'] = info_html
    
    return request.theme.recentchanges_entry(d)
    
def cmp_lines(first, second):
    return cmp(first[0].ed_time, second[0].ed_time)

def print_abandoned(macro, args, **kw):
    request = macro.request
    _ = request.getText
    d = {}
    pagename = macro.formatter.page.page_name
    d['q_page_name'] = wikiutil.quoteWikiname(pagename)
    msg = None

    pages = request.getPageList()
    last_edits = []
    for page in pages:
        try:
            last_edits.append(editlog.EditLog(
                wikiutil.getPagePath(page, 'last-edited', check_create=0)).next())
        except StopIteration:
            pass
        #   we don't want all Systempages at hte beginning of the abandoned list
        #    line = editlog.EditLogLine({})
        #    line.pagename = page
        #    line.ed_time = 0
        #    line.comment = 'not edited'
        #    line.action = ''
        #    line.userid = ''
        #    line.hostname = ''
        #    line.addr = ''
        #    last_edits.append(line)
    last_edits.sort()

    # set max size in days
    max_days = min(int(request.form.get('max_days', [0])[0]), _DAYS_SELECTION[-1])
    # default to _MAX_DAYS for useres without bookmark
    if not max_days:
        max_days = _MAX_DAYS
    d['rc_max_days'] = max_days
    
    # give known user the option to extend the normal display
    if request.user.valid:
        d['rc_days'] = _DAYS_SELECTION
    else:
        d['rc_days'] = None
    
    d['rc_update_bookmark'] = d['rc_rss_link'] = None
    request.write(request.theme.recentchanges_header(d))

    length = len(last_edits)
    
    index = 0
    last_index = 0
    day_count = 0
    
    line = last_edits[index]
    line.time_tuple = request.user.getTime(line.ed_time)
    this_day = line.time_tuple[0:3]
    day = this_day

    while 1:

        index += 1

        if (index>length):
            break    

        if index < length:
            line = last_edits[index]
            line.time_tuple = request.user.getTime(line.ed_time)
            day = line.time_tuple[0:3]

        if (day != this_day) or (index==length):
            d['bookmark_link_html'] = None
            d['date'] = request.user.getFormattedDateWords(last_edits[last_index].ed_time)
            request.write(request.theme.recentchanges_daybreak(d))
            
            for page in last_edits[last_index:index]:
                request.write(format_page_edits(macro, [page], showComments, None))
            last_index = index
            day_count += 1
            if (day_count >= max_days):
                break

    d['rc_msg'] = msg
    request.write(request.theme.recentchanges_footer(d))
    
def execute(macro, args, **kw):
    
    # betta' with this line object so we can move away from array indexing
    class line:
     def __init__(self, edit_tuple):
      self.pagename = edit_tuple[0]
      self.ed_time = edit_tuple[1]
      self.action = edit_tuple[3]
      self.comment = edit_tuple[4]
      self.userid = edit_tuple[2]
      self.host = edit_tuple[5]

     def getEditor(self, request):
	 if self.userid:
           return formatter.pagelink(user.User(request, self.userid).name)
	 else: return ''

    # handle abandoned keyword
    if kw.get('abandoned', 0):
        print_abandoned(macro, args, **kw)
        return ''

    request = macro.request
    _ = request.getText
    d = {}
    page_path = request.getScriptname() + request.getPathinfo()
    pagename = request.getPathinfo()[1:]
    d['q_page_name'] = wikiutil.quoteWikiname(pagename)


    formatter = Formatter(request)
    #log = editlog.EditLog()
    # we limit recent changes to display at most the last 7 days of edits.
    right_now  = time.gmtime()
    oldest_displayed_time_tuple = (right_now[0], right_now[1], right_now[2]-7, 0, 0, 0, 0, 0, 0)
    seven_days_ago = time.mktime(oldest_displayed_time_tuple)
    
    lines = []
    db = wikidb.connect()
    cursor = db.cursor()
    # b/c oldest_time is the same until it's a new day, this statement caches well
    # so, let's compile all the different types of changes together!
    # note:  we use a select statement on the outside here, though not needed, so that MySQL will cache the statement.  MySQL does not cache non-selects, so we have to do this.
    cursor.execute("""SELECT * from (
     (SELECT name, changeTime as changeTime, id, editType, comment, userIP from pageChanges where pageChanges.changeTime >= %s)
     UNION
     (SELECT name, changeTime as changeTime, id, editType, comment, userIP from currentImageChanges where currentImageChanges.changeTime >= %s)
     UNION
     (SELECT name, changeTime as changeTime, id, editType, comment, userIP from oldImageChanges where oldImageChanges.changeTime >= %s)
     UNION
     (SELECT name, changeTime as changeTime, id, editType, comment, userIP from deletedImageChanges where deletedImageChanges.changeTime >= %s)
     UNION
     (SELECT name, changeTime as changeTime, id, editType, comment, userIP from eventChanges where eventChanges.changeTime >= %s)
     order by changeTime desc
     ) as result;"""
      , (seven_days_ago, seven_days_ago, seven_days_ago, seven_days_ago, seven_days_ago))
    
    edit = cursor.fetchone()
    while edit:
      lines.append(line(edit))
      edit = cursor.fetchone()

    cursor.close()
    db.close()

    tnow = time.time()
    msg = ""

    # get bookmark from valid user
    bookmark = request.user.getBookmark()
    showComments = request.user.getShowComments()
    d['show_comments_html'] = None
    d['show_comments'] = None
    d['show_comments'] = showComments
    if showComments == 1:
        d['show_comments_html'] = '[' + wikiutil.link_tag(request, pagename + "?action=showcomments&hide=1", "Hide comments") + ']'
    else:
        d['show_comments_html'] = '[' + wikiutil.link_tag(request, pagename + "?action=showcomments", "Show comments") + ']'

    # add bookmark link if valid user
    d['rc_curr_bookmark'] = None
    d['rc_update_bookmark'] = None
    if request.user.valid:
        d['rc_curr_bookmark'] = _('(will show you only changes made since you last pressed \'clear\')')
        if bookmark:
            d['rc_curr_bookmark'] = _('(currently set to %s)') % (
                request.user.getFormattedDateTime(bookmark),) + ' [' + wikiutil.link_tag(
                    request,
		    pagename
                    + "?action=bookmark&time=del",
                    "%s" % _("Show all changes")
                    ) + ']'

        d['rc_update_bookmark'] = wikiutil.link_tag(
            request,
	    pagename
                + "?action=bookmark&time=%d" % (tnow,),
            _("Clear observed changes")
            )
    
    # set max size in days
    max_days = min(int(request.form.get('max_days', [0])[0]), _DAYS_SELECTION[-1])
    # default to _MAX_DAYS for useres without bookmark
    if not max_days and not bookmark:
        max_days = _MAX_DAYS
    d['rc_max_days'] = max_days
    
    # give known user the option to extend the normal display
    if request.user.valid:
        d['rc_days'] = _DAYS_SELECTION
    else:
        d['rc_days'] = []

    # add rss link
    d['rc_rss_link'] = None
    if wikixml.ok:
        if config.relative_dir:
            d['rc_rss_link'] = '<link rel=alternate type="application/rss+xml" href="/%s/Recent_Changes?action=rss_rc" title="Recent Changes RSS Feed"><a title="Recent Changes RSS Feed" href="/%s/Recent_Changes?action=rss_rc" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a>' % (config.relative_dir, config.relative_dir)
        else:
            d['rc_rss_link'] = '<link rel=alternate type="application/rss+xml" href="/Recent_Changes?action=rss_rc" title="Recent Changes RSS Feed"><a title="Recent Changes RSS Feed" href="/Recent_Changes?action=rss_rc" style="border:1px solid;border-color:#FC9 #630 #330 #F96;padding:0 3px;font:bold 10px verdana,sans-serif;color:#FFF;background:#F60;text-decoration:none;margin:0;">RSS</a>'
        #img = request.theme.make_icon("rss")
        #d['rc_rss_link'] = macro.formatter.url(
        #    wikiutil.quoteWikiname(macro.formatter.page.page_name) + "?action=rss_rc",
        #    img, unescaped=1)

    request.write(request.theme.recentchanges_header(d))
    
    pages = {}
    ignore_pages = {}

    today = request.user.getTime(tnow)[0:3]
    this_day = today
    day_count = 0

    for line in lines:
        if not request.user.may.read(line.pagename):
            continue

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
                        pagename + "?action=bookmark&time=%d" % (pages[0][0].ed_time,),
                        _("set bookmark")
                        )
            d['date'] = request.user.getFormattedDateWords(pages[0][0].ed_time)
            request.write(request.theme.recentchanges_daybreak(d))
            
            for page in pages:
                request.write(format_page_edits(macro, page, showComments, bookmark, formatter))
    

    d['rc_msg'] = msg
    request.write(request.theme.recentchanges_footer(d))

    return ''


