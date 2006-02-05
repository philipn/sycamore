# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Action Handlers

    Actions are triggered by the user clicking on special links on the page
    (like the icons in the title, or the "EditText" link at the bottom). The
    name of the action is passed in the "action" CGI parameter.

    The sub-package "LocalWiki.action" contains external actions, you can
    place your own extensions there (similar to extension macros). User
    actions that start with a capital letter will be displayed in a list
    at the bottom of each page.

    User actions starting with a lowercase letter can be used to work
    together with a user macro; those actions a likely to work only if
    invoked BY that macro, and are thus hidden from the user interface.

    @copyright: 2000-2004 by J?rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, re, string, time, urllib
from LocalWiki import config, util, wikiutil, user
from LocalWiki.Page import Page
from LocalWiki.util import LocalWikiNoFooter, pysupport

#############################################################################
### Search
#############################################################################

"""
def do_fullsearch(pagename, request, fieldname='value'):
    _ = request.getText
    start = time.clock()

    # send http headers
    request.http_headers()

    # get parameters
    if request.form.has_key(fieldname):
        needle = request.form[fieldname][0]
    else:
        needle = ''
    try:
        case = int(request.form['case'][0])
    except (KeyError, ValueError):
        case = 0
    try:
        context = int(request.form['context'][0])
    except (KeyError, ValueError):
        context = 0
    max_context = 10 # only show first `max_context` contexts

    # check for sensible search term
    if len(needle) < 1:
        Page(pagename).send_page(request,
             msg=_("Please use a more selective search term instead of '%(needle)s'!") % {'needle': needle})
        return

    # send title
    wikiutil.send_title(request, _('Full text search for "%s"') % (needle,))

    # search the pages
    pagecount, hits = wikiutil.searchPages(needle,
        literal=request.form.has_key('literal'),
        context=context, case=case)

    # print the result
    request.write('<div id="content">\n') # start content div
    request.write('<dl class="searchresult">')
    hiddenhits = 0
    for (count, page_name, fragments) in hits:
        if not request.user.may.read(page_name):
            hiddenhits += 1
            continue
        request.write('<dt>' + Page(page_name).link_to(querystr=
            'action=highlight&amp;value=%s' % urllib.quote_plus(needle)))
        request.write(' . . . . ' + `count`)
        request.write(' ' + (_('match'), _('matches'))[count != 1])
        request.write('</dt><dd><p>\n')
        if context:
            out = []
            for hit in fragments[:max_context]:
                out.append('...%s<span>%s</span>%s...' % tuple(map(wikiutil.escape, hit)))
            request.write('<br>\n'.join(out))
            if len(fragments) > max_context:
                request.write('...')
        request.write('</p></dd>\n')
    request.write('</dl>')

    print_search_stats(request, len(hits)-hiddenhits, pagecount, start)
    request.write('</div>\n') # end content div
    wikiutil.send_footer(request, pagename, editable=0, showactions=0, form=request.form)
"""
def do_fullsearch(pagename, request, fieldname='value'):
    do_newsearch(pagename, request, fieldname, 0)


def page_exists_slut(pagename):
    """
    This method is slutty because we don't bother to create a Page object to see if the page exists.
    Making a page object ties you down.  You have to worry about memory and processor time. . shesh. .
    We're slutty so we just see if the text file associated with the page exists or not.
    """
    return os.path.exists(config.data_dir + "/text/" + wikiutil.quoteFilename(pagename))

def do_newsearch(pagename, request, fieldname='value', inc_title=1, pstart=0, pwith=10, tstart=0, twith=10):
    _ = request.getText
    start = time.clock()

    # send http headers
    request.http_headers()

    # get parameters
    if request.form.has_key(fieldname):
        needle = request.form[fieldname][0]
    else:
        needle = ''
    try:
        case = int(request.form['case'][0])
    except (KeyError, ValueError):
        case = 0
    try:
        context = int(request.form['context'][0])
    except (KeyError, ValueError):
        context = 0
    max_context = 10 # only show first `max_context` contexts

    # check for sensible search term
    if len(needle) < 1 and not request.form.get('string'):
      Page(pagename, request).send_page(msg=_("Please enter a search string"))
      return
    elif request.form.get('string'):
        needle = request.form.get('string')[0]
        context = 40
        if request.form.get('tstart'):
                tstart = int(request.form.get('tstart')[0])
        if request.form.get('pstart'):
                pstart = int(request.form.get('pstart')[0])
        if request.form.get('twith'):
                twith = int(request.form.get('twith')[0])
        if request.form.get('pwith'):
                pwith = int(request.form.get('pwith')[0])
    # send title
    wikiutil.send_title(request, _('Search results for "%s"') % (needle,))
    
    flex_needle = needle.lower()
    flex_needle = re.sub(r"\"|\'", "", flex_needle)
    flex_needle = re.sub("\-", " ", flex_needle)
    searchlog = open(config.app_dir + '/search.log','a')
    searchlog.write(needle + '\n')
    searchlog.close()
    
    #try:
        #needle_re = re.compile(needle, re.IGNORECASE)
    # The regexp on the sides of the regexp string in needle_re are so that we ignore strings occuring inside of words in our display of the matches  -- this doesn't affect the searching at all, just the display.  So we display only where "hey" occurs, not where "hey" occurs inside of the word "they".  This is sort of a hack.
    subbed_needle = re.sub("\+|\\\\|\*|\?|\(|\)|\[|\]", " ", needle)
    if subbed_needle == needle:
        needle_re = re.compile("[^A-Za-z]" + subbed_needle + "[^A-Za-z]", re.IGNORECASE)
    else:
        needle_re = re.compile(subbed_needle, re.IGNORECASE)
    #except re.error:
    #   needle_re = re.compile(re.escape(needle), re.IGNORECASE)

    #all_pages = wikiutil.getPageList(config.text_dir)
    #title_hits = filter(needle_re.search, all_pages)
    if inc_title:
        title_hits = []
        tcount = 0
        t = os.popen(config.app_dir + '/search' + ' ' + config.app_dir + '/title_search_db %s %s %s' % (tstart, twith,flex_needle),'r')
        percent_line = t.readline()
        pagename_line = t.readline()
        data_line = (t.readline()).strip('\n')
        j = 0
        while (len(title_hits) != twith+1 and percent_line and data_line):
                if request.user.may.read(data_line) and Page(data_line, request).exists():
                        title_hits.append(data_line)
                else:
                        tcount = tcount + 1
                percent_line = t.readline()
                pagename_line = t.readline()
                data_line = (t.readline()).strip('\n')
                if (j + len(title_hits)) >= (twith):
                        t = os.popen(config.app_dir + '/search' + ' ' + config.app_dir + '/title_search_db %s %s %s' % (tstart+len(title_hits)+tcount, 1,flex_needle),'r')
                        percent_line = t.readline()
                        pagename_line = t.readline()
                        data_line = (t.readline()).strip('\n')


    full_hits = []
    count = 0
    s = os.popen(config.app_dir + '/search' + ' ' + config.app_dir + '/search_db %s %s %s' % (pstart, pwith,flex_needle),'r')
    percent_line = s.readline()
    pagename_line = s.readline()
    data_line = s.readline()
    full_hits = []
    i = 0
    readable = 0
    while (len(full_hits) != pwith+1 and percent_line and pagename_line and data_line):
        name = pagename_line.strip('\n')
        if request.user.may.read(wikiutil.unquoteWikiname(name)) and Page(wikiutil.unquoteWikiname(name), request).exists():
                full_hits.append((name,int(string.replace(percent_line, "%", " ").strip()), data_line))
        else:
                count = count + 1
        if (count + len(full_hits)) >= (pwith):
                s = os.popen(config.app_dir + '/search' + ' ' +  config.app_dir + '/search_db %s %s %s' % (pstart+len(full_hits)+count, 1,flex_needle),'r')
                percent_line = s.readline()
                pagename_line = s.readline()
                data_line = s.readline()
                continue

        percent_line = s.readline()
        pagename_line = s.readline()
        data_line = s.readline()

    relative_dir = ''
    if config.relative_dir:
        relative_dir = '/' + config.relative_dir 
    if inc_title:
        if len(title_hits) < 1:
                request.write('<h3>&nbsp;No title matches</h3>')
                request.write('<table id="footer" cellpadding="8"><tr><td>\n') # start content div
                request.write('The %s does not have any entries with the exact title "' % config.sitename+ needle + '" <br />')
                request.write('Would you like to <a href="%s/' % relative_dir + needle + '">create a new page with this title</a>?')
                request.write('</td></tr></table>\n')
        else:
                request.write('<h3>&nbsp;Title matches</h3>')
                if not title_hits[0].lower() == needle.lower():
                        request.write('<table id="footer" cellpadding="8"><tr><td>The %s does not have any entries with the exact title "' % config.sitename + needle + '". <br />')
                        request.write('Would you like to <a href="%s/' % relative_dir + needle + '">create a new page with this title</a>?</td></tr></table>')
        request.write('<div id="content">\n') # start content div
        request.write('<ul>')
        if len(title_hits) > twith:
                for t_hit in title_hits[0:twith]:
                        request.write('<li>%s</li>' % Page(wikiutil.unquoteWikiname(t_hit), request).link_to())
                request.write('</ul>')
                request.write('<p>(<a href="%s/?action=newsearch&string=%s&tstart=%s">next %s matches</a>)'
                        % (relative_dir, needle, tstart+twith+tcount, twith))
                request.write('</div>\n') # end content div
        else:
                for t_hit in title_hits:
                        request.write('<li>%s</li>' % Page(wikiutil.unquoteWikiname(t_hit), request).link_to())
                request.write('</ul>')
                request.write('</div>\n') # end content div
    if len(full_hits) < 1:
      request.write('<h3>&nbsp;No full text matches</h3>')
    else:
      request.write('<h3>&nbsp;Full text matches</h3>')
      request.write('<div id="content">\n') # start content div
      request.write('<dl class="searchresult">')
      for (page_name, percent, text) in full_hits[0:pwith]:
              color = "#ff3333"
              if percent > 65:
                color = "#55ff55"
              elif percent > 32:
                color = "#ffee55"
              request.write('<p><table><tr><td width="40" valign="middle"><table id="progbar" cellspacing="0" cellpadding="0"><tr><td height="7" width="%d" bgcolor="%s"></td><td width="%d" bgcolor="#eeeeee"></td></tr></table></td><td>' % (percent/3, color, 33 - percent/3))
              request.write(Page(wikiutil.unquoteWikiname(page_name), request).link_to(querystr=
                  'action=highlight&amp;value=%s' % urllib.quote_plus(needle)))
              request.write('</td></tr></table>\n')
              if context:
                        fragments = []
                        out = []
                        pos = 0
                        # make the fragments so we can return intelligent looking results
                        #match = needle_re.search(text, pos) 
                        #pos = match.end()
                        k = 0
                        match = needle_re.search(text, pos)
                        while (match and k <= max_context):
                                pos = match.end()
                                fragments.append((
                                        text[match.start()-context:match.start()],
                                        text[match.start():match.end()],
                                        text[match.end():match.end()+context],
                                        ))
                                k = k + 1
                                match = needle_re.search(text, pos)
          
                        for hit in fragments[0:max_context]:
                                #out.append('...%s<span>%s</span>%s...' % tuple(map(wikiutil.escape, hit)))
                                out.append('...%s<strong>%s</strong>%s...<br>' % (hit[0], hit[1], hit[2]))
                                request.write('\n'.join(out))
                                out = []
                        if k > max_context:
                                request.write('...')
                        request.write('</p>\n')

      if len(full_hits) > pwith:
         request.write('<p>&nbsp;(<a href="%s/?action=newsearch&string=%s&pstart=%s">next %s matches</a>)</div></dl>'
                        % (relative_dir, urllib.quote_plus(needle), pstart+pwith+count, pwith))
      else:
         request.write('</div></dl>')
    wikiutil.send_footer(request, pagename, editable=0, showactions=0, form=request.form)


def do_titlesearch(pagename, request, fieldname='value'):
    _ = request.getText
    start = time.clock()

    request.http_headers()

    if request.form.has_key(fieldname):
        needle = request.form[fieldname][0]
    else:
        needle = ''

    # check for sensible search term
    if len(needle) < 1:
        Page(pagename, request).send_page(
             msg=_("Please use a more selective search term instead of '%(needle)s'!") % {'needle': needle})
        return

    wikiutil.send_title(request, _('Title search for "%s"') % (needle,))

    try:
        needle_re = re.compile(needle, re.IGNORECASE)
    except re.error:
        needle_re = re.compile(re.escape(needle), re.IGNORECASE)
    all_pages = wikiutil.getPageList(request)
    hits = filter(needle_re.search, all_pages)
    hits.sort()

    hits = filter(request.user.may.read, hits)

    request.write('<div id="content">\n') # start content div
    request.write('<ul>')
    for filename in hits:
        request.write('<li>%s</li>' % Page(filename, request).link_to())
    request.write('</ul>')

    print_search_stats(request, len(hits), len(all_pages), start)
    request.write('</div>\n') # end content div
    wikiutil.send_footer(request, pagename, editable=0, showactions=0, form=request.form)


def do_inlinesearch(pagename, request):
    text_title = request.form.get('text_title', [''])[0]
    text_full = request.form.get('text_full', [''])[0]
    
    if request.form.has_key('button_title.x'):
        if request.form['button_title.x'][0] == "0" and \
                text_full and not text_title:
            search = 'full'
        else:
            search = 'title'
    elif request.form.has_key('button_full.x'):
        search = 'full'
    elif request.form.has_key('button_new.x'):
        search = 'new'
    elif request.form.has_key('text_full'):
        search = 'full'
    else:
        search = 'title'

    globals()["do_%ssearch" % search](pagename, request, fieldname = "text_" + search)

def print_search_stats(request, hits, start):
    _ = request.getText
    request.write("<p>%s %s</p>" % (
        _("%(hits)d hits.") % {'hits': hits},
        _("Needed %(timer).1f seconds.") % {'timer': time.clock() - start + 0.05}))


def do_highlight(pagename, request):
    if request.form.has_key('value'):
        needle = request.form["value"][0]
    else:
        needle = ''

    try:
        needle_re = re.compile(needle, re.IGNORECASE)
    except re.error:
        needle = re.escape(needle)
        needle_re = re.compile(needle, re.IGNORECASE)

    Page(pagename, request).send_page(hilite_re=needle_re)


#############################################################################
### Misc Actions
#############################################################################

def do_diff(pagename, request, in_wiki_interface=True, text_mode=False, version1=0, version2=0, diff1_date='', diff2_date=''):
    """ Handle "action=diff"
        checking for either a "date=backupdate" parameter
        or date1 and date2 parameters
    """
    l = []
    if not request.user.may.read(pagename):
        Page(pagename, request).send_page()
        return

    # version numbers
    try:
        if not version1: version1 = request.form['version1'][0]
        try:
            version1 = int(version1)
        except StandardError:
            version1 = 0
    except KeyError:
        version1 = 0

    try:
        if not version2: version2 = request.form['version2'][0]
        try:
            version2 = int(version2)
        except StandardError:
            version2 = 0
    except KeyError:
        version2 = 0

    if version1:
      if not diff1_date: diff1_date = repr(Page(pagename, request).version_number_to_date(version1))
    if version2:
      if not diff2_date: diff2_date = repr(Page(pagename, request).version_number_to_date(version2))

    # explicit dates
    if not diff1_date:
      try:
          diff1_date = request.form['date1'][0]
          try:
              diff1_date = diff1_date
          except StandardError:
              diff1_date = '0'
      except KeyError:
          diff1_date = '-1'

    if not diff2_date:
      try:
          diff2_date = request.form['date2'][0]
          try:
              diff2_date = diff2_date
          except StandardError:
              diff2_date = '0'
      except KeyError:
          diff2_date = '0'

    if diff1_date == '-1' and diff2_date == '0':
        try:
            diff1_date = request.form['date'][0]
            try:
                diff1_date = diff1_date
            except StandardError:
                diff1_date = '-1'
        except KeyError:
            diff1_date = '-1'
  
    # spacing flag?
    try:
        ignorews = int(request.form['ignorews'][0])
    except (KeyError, ValueError, TypeError):
        ignorews = 0

    _ = request.getText
    
    if in_wiki_interface:
      request.http_headers()
      wikiutil.send_title(request, _('Diff for "%s"') % (pagename,), pagename=pagename)
    else:
      l.append("Diff for %s" % (pagename))
  
    if (float(diff1_date)>0 and float(diff2_date)>0 and float(diff1_date)>float(diff2_date)) or \
       (float(diff1_date)==0 and float(diff2_date)>0):
        diff1_date,diff2_date = diff2_date,diff1_date
        
    olddate1,oldcount1 = None,0
    olddate2,oldcount2 = None,0

    # get the filename of the version to compare to
    edit_count = 0
    olddate1 = diff1_date
    olddate2 = diff2_date

    if diff1_date == '-1':
	# we want editTime as a string for precision purposes
	request.cursor.execute("SELECT editTime from allPages where name=%(pagename)s order by editTime desc limit 2", {'pagename':pagename})
	result = request.cursor.fetchall()
	if len(result) >= 2:
	   first_olddate = result[1][0]
	else:
           first_olddate = 0
	
        oldpage = Page(pagename, request, prev_date=first_olddate)
        oldcount1 = oldcount1 - 1
    elif diff1_date == 0:
        oldpage = Page(pagename, request)
        # oldcount1 is still on init value 0
    else:
        if olddate1:
            oldpage = Page(pagename, request, prev_date=olddate1)
        else:
            oldpage = Page("$EmptyPage$", request) # XXX: ugly hack
            oldpage.set_raw_body("")    # avoid loading from db
            
    if diff2_date == 0:
        newpage = Page(pagename, request)
        # oldcount2 is still on init value 0
    else:
        if olddate2:
            newpage = Page(pagename, request, prev_date=olddate2)
        else:
            newpage = Page("$EmptyPage$", request) # XXX: ugly hack
            newpage.set_raw_body("")    # avoid loading from db

    edit_count = abs(oldcount1 - oldcount2)

    l.append('<div id="content">\n') # start content div
    l.append('<p><strong>')
    if version1:
      l.append(_('Differences between versions %s (%s) and %s (%s)') % (
        oldpage.get_version(), oldpage.mtime_printable(), newpage.get_version(), newpage.mtime_printable()))
    else:
      l.append(_('Differences between versions 0 and versions %s (%s)') % (1, newpage.mtime_printable()))
  
    if edit_count > 1:
        l.append(' ' + _('(spanning %d versions)') % (edit_count,))
    l.append('</strong></p>')
  
    from LocalWiki.util.diff import diff
    if version1: l.append(diff(request, oldpage.get_raw_body(), newpage.get_raw_body(), text_mode=text_mode))
    else: l.append(diff(request, '', newpage.get_raw_body(), text_mode=text_mode))

    if in_wiki_interface:
      request.write(''.join(l))
      newpage.send_page(count_hit=0, content_only=1, content_id="content-under-diff")
      request.write('</div>\n') # end content div
      wikiutil.send_footer(request, pagename, showpage=1)
    else:
      l.append('</div>\n') #end content div
      return ''.join(l)


def do_info(pagename, request):
    page = Page(pagename, request)

    if not request.user.may.read(pagename):
        page.send_page()
        return

    def general(page, pagename, request):
        _ = request.getText

        request.write('<h2>%s</h2>\n' % _('General Information'))
        
        # show page size
        request.write(("<p>%s</p>" % _("Page size: %d words (%d characters).")) % (page.human_size(), page.size()))

        # show SHA digest fingerprint
        """
        import sha
        digest = sha.new(page.get_raw_body()).hexdigest().upper()
        request.write('<p>%(label)s <tt>%(value)s</tt></p>' % {
            'label': _("SHA digest of this page's content is:"),
            'value': digest,
            })
        """

        # show attachments (if allowed)
        attachment_info = getHandler('Files', 'info')
        if attachment_info: attachment_info(pagename, request)

        #show people w/it as a favorite
        ## (modify below)

        # show subscribers
        #subscribers = page.getFavorites(request,  include_self=1, return_users=1)
        """
        if subscribers:
            request.write('<p>', _('The following people have this page as a Favorite:'))
            for lang in subscribers.keys():
                request.write('<br>')
                for user in subscribers[lang]:
                    # do NOT disclose email addr, only WikiName
                    userhomepage = Page(user.name)
                    if userhomepage.exists():
                        request.write(userhomepage.link_to(request) + ' ')
                    else:
                        request.write(user.name + ' ')
            request.write('</p>')
        """

        # show links
        links_from_page = page.getPageLinks(request)
        if links_from_page:
            request.write('<p>', _('This page links to the following pages:'), '<br>')
            for linkedpage in links_from_page:
                request.write("%s%s " % (Page(linkedpage, request).link_to(), ",."[linkedpage == links_from_page[-1]]))
            request.write("</p>")
	else: request.write('<p>This page links to <b>no pages</b>.</p>')

	links_to_page = page.getPageLinksTo()
        if links_to_page:
            request.write('<p>', _('The following pages link to this page:'), '<br>')
            for linkingpage in links_to_page:
                request.write("%s%s " % (Page(linkingpage, request).link_to(), ",."[linkingpage == links_to_page[-1]]))
            request.write("</p>")
	else: request.write('<p><b>No pages</b> link to this page.</p>')


    def history(page, pagename, request):
	def printNextPrev(request, pagename, last_version, offset_given):
	  #prints the next and previous links, if they're needed
	  html = '<p>'
	  if last_version != 1:
	    html += '[<a href="%s/%s?action=info&offset=%s">previous edits</a> | ' % (request.getBaseURL(), pagename, offset_given+1)
	  else:
	    html += '[previous edits | '
	  if offset_given:
	    html += '<a href="%s/%s?action=info&offset=%s">next edits</a>]' % (request.getBaseURL(), pagename, offset_given-1) 
	  else:
	    html += 'next edits]'
	  html += '</p>'
	  request.write(html)



        # show history as default
        from stat import ST_MTIME, ST_SIZE
        _ = request.getText

        request.write('<h2>%s</h2>\n' % _('Revision History'))

        from LocalWiki.logfile import editlog
        from LocalWiki.util.dataset import TupleDataset, Column

	has_history = False

        history = TupleDataset()
        history.columns = [
            Column('count', label='#', align='right'),
            Column('mtime', label=_('Date'), align='right'),
            Column('diff', label='<input type="submit"           value="%s">' % (_("Compare"))),
            # entfernt, nicht 4.01 compliant:          href="%s"   % page.url(request)
            Column('editor', label=_('Editor'), hidden=not config.show_hosts),
            Column('comment', label=_('Comment')),
            Column('action', label=_('Action')),
            ]

	versions = 0
	# offset is n . n*100 versions
	offset_given = int(request.form.get('offset', [0])[0])
	if not offset_given: offset = 0
	else:
	   # so they see a consistent version of the page between page forward/back
	   offset = offset_given*100 - offset_given
        may_revert = request.user.may.revert(pagename)
	request.cursor.execute("SELECT count(editTime) from allPages where name=%(pagename)s", {'pagename':pagename})
	count_result = request.cursor.fetchone()
	if count_result: versions = count_result[0]
	request.cursor.execute("SELECT name, editTime, userEdited, editType, comment, userIP from allPages where name=%(pagename)s order by editTime desc limit 100 offset %(offset)s", {'pagename':pagename, 'offset':offset})
	result = request.cursor.fetchall()
	request.cursor.execute("SELECT editTime from curPages where name=%(pagename)s", {'pagename':pagename})
	currentpage_editTime_result = request.cursor.fetchone()
	if currentpage_editTime_result: currentpage_editTime = currentpage_editTime_result[0]
	else: currentpage_editTime = 0
	actions = ""
	if result: has_history = True
	count = 1
	this_version = 0
	for entry in result:
	    actions = ''
	    this_version = 1 + versions - count - offset

	    mtime = entry[1]
	    comment = entry[4]
	    editType = entry[3]
	    userIP = entry[5]

            if currentpage_editTime == mtime:
                actions = '%s&nbsp;%s' % (actions, page.link_to(
                    text=_('view'),
                    querystr=''))
                actions = '%s&nbsp;%s' % (actions, page.link_to(
                    text=_('raw'),
                    querystr='action=raw'))
                actions = '%s&nbsp;%s' % (actions, page.link_to(
                    text=_('print'),
                    querystr='action=print'))
                diff = '<input type="radio" name="version1" value="%s"><input type="radio" name="version2" value="%s" checked="checked">' % (this_version, this_version)
	    else:
	      if count==2:
                checked=' checked="checked"'
              else:
                checked=""

              if editType != 'DELETE':
                  actions = '%s&nbsp;%s' % (actions, page.link_to(
                      text=_('view'),
                      querystr='action=recall&amp;version=%s' % this_version))
                  actions = '%s&nbsp;%s' % (actions, page.link_to(
                      text=_('raw'),
                      querystr='action=raw&amp;version=%s' % this_version))
                  actions = '%s&nbsp;%s' % (actions, page.link_to(
                      text=_('print'),
                      querystr='action=print&amp;version=%s' % this_version))
                  if may_revert:
                      actions = '%s&nbsp;%s' % (actions, page.link_to(
                          text=_('revert'),
                          querystr='action=revert&amp;version=%s' % (this_version)))
                  diff = '<input type="radio" name="version1" value="%s"%s><input type="radio" name="version2" value="%s">' % (this_version,checked,this_version)
	      else:
                  diff = '<input type="radio" name="version1" value="%s"%s><input type="radio" name="version2" value="%s">' % (this_version,checked,this_version)

            
#             if editType.find('/REVERT') != -1:
# 	        if comment[0] == 'v':
# 		  # Given as version so let's display as version
# 		  comment = "Revert to version %s" % comment[1:]
# 		else:
#                   datestamp = request.user.getFormattedDateTime(float(comment))
#                   comment = _("Revert to version dated %(datestamp)s.") % {'datestamp': datestamp}
# 	    elif editType == 'ATTNEW':
# 	    	comment = "Upload of attachment '%s.'" % comment
# 	    elif editType == 'ATTDEL':
# 		comment = "Attachment '%s' deleted." % comment
# 	    elif editType == 'DELETE':
# 	        if comment: comment = "Page deleted: '%s'" % comment
# 		else: comment = "Page deleted (no comment)"
	    from LocalWiki.widget.comments import Comment
	    comment = Comment(request, comment, editType, pagename).render()
   	    
	    if entry[2]:
	    	editUser = user.User(request, entry[2])
            	editUser_text = Page(editUser.name, request).link_to()
		editUser_text = '<span title="%s">' % userIP + editUser_text + '</span>'
	    else: editUser_text = '<i>none</i>'
            history.addRow((
                        this_version,
                        request.user.getFormattedDateTime(mtime),
                        diff,
                        editUser_text,
                        comment or '&nbsp;',
                        actions,
                ))
	    count +=1

	last_version = this_version

        # print version history
        from LocalWiki.widget.browser import DataBrowserWidget
        from LocalWiki.formatter.text_html import Formatter

        request.write('<form method="GET" action="%s">\n' % (page.url(request)))
        request.write('<div id="pageinfo">')
        request.write('<input type="hidden" name="action" value="diff">\n')

	if has_history:
          request.formatter = Formatter(request)
          history_table = DataBrowserWidget(request)
          history_table.setData(history)
          history_table.render()
	  printNextPrev(request, pagename, last_version, offset_given)
          request.write('</div>')
          request.write('\n</form>\n')
	else:
	  request.write('<p>This page has no revision history.  This is probably because the page was never created.</p>')


    _ = request.getText
    qpagename = wikiutil.quoteWikiname(pagename)

    request.http_headers()

    wikiutil.simple_send_title(request, pagename, strict_title='Info for "%s"' % pagename)

    request.write('<div id="content">\n') # start content div

    show_general = int(request.form.get('general', [0])[0]) != 0
    
    from LocalWiki.widget.infobar import InfoBar
    InfoBar(request, pagename).render()

    if show_general:
	general(page, pagename, request)
    else:
	history(page, pagename, request)

    request.write('</div>\n') # end content div
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)


def do_recall(pagename, request):
    # We must check if the current page has different ACLs.
    if not request.user.may.read(pagename):
        Page(pagename, request).send_page()
        return
    if request.form.has_key('date'):
        Page(pagename, request, prev_date=request.form['date'][0]).send_page()
    elif request.form.has_key('version'):
    	Page(pagename, request, version=request.form['version'][0]).send_page()
    else:
        Page(pagename, request).send_page()


def do_show(pagename, request):
    if request.form.has_key('date'):
        Page(pagename, request, prev_date=request.form['date'][0]).send_page(count_hit=1)
    elif request.form.has_key('version'):
    	Page(pagename, request, version=request.form['version'][0]).send_page(count_hit=1)
    else:
        Page(pagename, request).send_page(count_hit=1)


#def do_refresh(pagename, request):
#    if request.form.has_key('key'):
#        from LocalWiki import caching
#        cache = caching.CacheEntry(request.form["key"][0])
#        cache.clear()
#    do_show(pagename, request)


def do_print(pagename, request):
    do_show(pagename, request)


def do_content(pagename, request):
    request.http_headers()
    page = Page(pagename, request)
    request.write('<!-- Transclusion of %s -->' % request.getQualifiedURL(page.url(request)))
    page.send_page(count_hit=0, content_only=1)
    raise LocalWikiNoFooter


def do_edit(pagename, request):
    if not request.user.may.edit(pagename):
        _ = request.getText
        Page(pagename, request).send_page(
            msg = _('You are not allowed to edit this page.'))
        return
    from LocalWiki.PageEditor import PageEditor
    if isValidPageName(pagename):
        PageEditor(pagename, request).sendEditor()
    else:
        _ = request.getText
        Page(pagename, request).send_page(msg = _('Invalid pagename: Only the characters A-Z, a-z, 0-9, "$", "&", ",", ".", "!", "\'", ":", ";", " ", "/", "-", "(", ")" are allowed in page names.'))

def isValidPageName(name):
    return not re.search('[^A-Za-z\-0-9 $&\.\,:;/\'\!\(\)]',name)


def do_revert(pagename, request):
    from LocalWiki.PageEditor import PageEditor
    _ = request.getText

    if not request.user.may.revert(pagename):
        return Page(pagename, request).send_page(
            msg = _('You are not allowed to revert this page!'))

    if request.form.has_key('version'):
      version = int(request.form['version'][0])
      oldpg = Page(pagename, request, version=version)
      date = oldpg.prev_date
      comment = 'v' + str(version)
    elif request.form.has_key('date'):
      date = request.form['date'][0]
      oldpg = Page(pagename, request, prev_date=date)
      version = oldpg.date_to_version_number(date)
      comment = date
    else:
      return
      
    pg = PageEditor(pagename, request)

    try:
        savemsg = pg.saveText(oldpg.get_raw_body(), '0',
            stripspaces=0, notify=1, comment=comment, action="SAVE/REVERT")
    except pg.SaveError:
        savemsg = _("An error occurred while reverting the page.")
    request.reset()
    pg.send_page(msg=savemsg)
    return None

def do_savepage(pagename, request):
    from LocalWiki.PageEditor import PageEditor

    _ = request.getText

    if not request.user.may.edit(pagename):
        Page(pagename, request).send_page(
            msg = _('You are not allowed to edit this page.'))
        return

    pg = PageEditor(pagename, request)
    savetext = request.form.get('savetext', [''])[0]
    datestamp = request.form.get('datestamp', [''])[0]
    comment = request.form.get('comment', [''])[0]
    category = request.form.get('category', [None])[0]
    try:
        rstrip = int(request.form['rstrip'][0])
    except (KeyError, ValueError):
        rstrip = 0
    try:
        notify = int(request.form['notify'][0])
    except (KeyError, ValueError):
        notify = 0

    if category:
        # strip trailing whitespace
        savetext = savetext.rstrip()

        # add category splitter if last non-empty line contains non-categories
        lines = filter(None, savetext.splitlines())
        if lines:
            categories = lines[-1].split()
            if categories and len(wikiutil.filterCategoryPages(categories)) < len(categories):
                savetext += '\n----\n'

        # add new category
        if savetext and savetext[-1] != '\n':
            savetext += ' '
        savetext += category

    # delete any unwanted stuff, replace CR, LF, TAB by whitespace
    control_chars = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f' \
                    '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
    remap_chars = string.maketrans('\t\r\n', '   ')
    comment = comment.translate(remap_chars, control_chars)

    if request.form.has_key('button_preview') or request.form.has_key('button_spellcheck') \
            or request.form.has_key('button_newwords'):
        pg.sendEditor(preview=savetext, comment=comment)
    elif request.form.has_key('button_cancel'):
        pg.sendCancel(savetext, datestamp)
    else:
        savetext = pg._normalize_text(savetext, stripspaces=rstrip)
        try:
            savemsg = pg.saveText(savetext, datestamp,
                                  stripspaces=rstrip, notify=notify,
                                  comment=comment)
        except pg.EditConflict, msg:
            allow_conflicts = 1
            from LocalWiki.util import diff3
            original_text = Page(pg.page_name, request, prev_date=datestamp).get_raw_body()
            saved_text = pg.get_raw_body()
            verynewtext = diff3.text_merge(original_text, saved_text, savetext,
                 allow_conflicts,
                 '----- /!\ Edit conflict! Other version: -----\n',
                 '----- /!\ Edit conflict! Your version: -----\n',
                 '----- /!\ End of edit conflict -----\n')
            if verynewtext:
                msg = _("""Someone else saved this page while you were editing!
Please review the page and save then. Do not save this page as it is!
Have a look at the diff of %(difflink)s to see what has been changed."""
                ) % {'difflink':pg.link_to(querystr='action=diff&amp;date=' + datestamp)}
                request.form['datestamp'] = pg.mtime()                             
                pg.sendEditor(msg=msg, comment=request.form.get('comment', [''])[0],
                              preview=verynewtext, staytop=1)
                return
            else:
                savemsg = msg
        except pg.SaveError, msg:
            savemsg = msg
        request.reset()
        backto = request.form.get('backto', [None])[0]
        if backto:
            pg = Page(backto, request)
        pg.send_page(msg=savemsg)
        request.http_redirect(pg.url())

def do_favorite(pagename, request):
    """ Add the current wiki page to the favorites list in the user's
        profile file.
    """ 
    _ = request.getText

    if request.form.has_key('delete'):
       removed_pagename = wikiutil.unquoteWikiname(request.form.get('delete')[0])
       request.user.favorites = request.user.getFavorites()
       request.user.delFavorite(removed_pagename)
       msg = _("Page '%s' removed from Bookmarks" % removed_pagename)

    elif not request.user.may.read(pagename):
        msg = _("You are not allowed to bookmark a page you can't read.")
        
    # check whether the user has a profile
    elif not request.user.valid: 
        msg = _('''You didn't create an account yet. '''
                '''Click 'New User' in the upper right to make an account.''')
                
    # This should just not display as an option if they've already got it as a favorite
    elif request.user.isFavoritedTo(pagename):
        msg = _('You are already made this page a Bookmark.')
              
    # Favorite current page
    else:
        if request.user.favoritePage(pagename):
            request.user.save()
        msg = _('You have added this page to your wiki Bookmarks!')
              
    Page(pagename, request).send_page(msg=msg)

def do_subscribe(pagename, request):
    """ Add the current wiki page to the subscribed_page property in
        current user profile.
    """
    _ = request.getText

    if not request.user.may.read(pagename):
        msg = _("You are not allowed to subscribe to a page you can't read.")

    # check config
    elif not config.mail_smarthost:
        msg = _('''This wiki is not enabled for mail processing. '''
                '''Contact the owner of the wiki, who can either enable email, or remove the "Subscribe" icon.''')

    # check whether the user has a profile
    elif not request.user.valid:
        msg = _('''You didn't create a user profile yet. '''
                '''Select UserPreferences in the upper right corner to create a profile.''')

    # check whether the user has an email address
    elif not request.user.email:
        msg = _('''You didn't enter an email address in your profile. '''
                '''Select your name (UserPreferences) in the upper right corner and enter a valid email address.''')

    # check whether already subscribed
    elif request.user.isSubscribedTo([pagename]):
        msg = _('You are already subscribed to this page.') + \
              _('To unsubscribe, go to your profile and delete this page from the subscription list.')
        
    # subscribe to current page
    else:
        if request.user.subscribePage(pagename):
            request.user.save()
        msg = _('You have been subscribed to this page.') + \
              _('To unsubscribe, go to your profile and delete this page from the subscription list.')

    Page(pagename, request).send_page(msg=msg)


def do_userform(pagename, request):
    from LocalWiki import userform
    savemsg = userform.savedata(request)
    Page(pagename, request).send_page(msg=savemsg)


def do_bookmark(pagename, request):
    if request.form.has_key('time'):
        if request.form['time'][0] =='del':
            tm=None
        else:
            try:
                tm = int(request.form["time"][0])
            except StandardError:
                tm = time.time()
    else:
        tm = time.time()

    if tm is None:
        request.user.delBookmark()
    else:
        request.user.setBookmark(tm)
    Page(pagename, request).send_page()

def do_showcomments(pagename, request):
    hideshow = 'showcomments'
    if request.form.has_key('hide'):
        hideshow = 'hidecomments'
    request.user.setShowComments(hideshow)
    Page(pagename, request).send_page()

def do_formtest(pagename, request):
    # test a user defined form
    from LocalWiki import wikiform
    wikiform.do_formtest(pagename, request)


# def do_macro(pagename, request):
#     """ Execute a helper action within a macro.
#     """

#     from LocalWiki import wikimacro
#     from LocalWiki.formatter.text_html import Formatter
#     from LocalWiki.parser.wiki import Parser
#     from LocalWiki.Page import Page
#     macro_name = request.form["macro"][0]
#     args = request.form.get('args', [''])[0]
    
#     parser = Parser('', request)
#     parser.formatter = Formatter(request)
#     parser.formatter.page = Page('dummy')
#     request.http_headers()
#     request.write(wikimacro.Macro(parser).execute(macro_name, args))
#     request.finish()
    
#############################################################################
### Special Actions
#############################################################################

def do_raw(pagename, request):
    if not request.user.may.read(pagename):
        Page(pagename, request).send_page()
        return

    request.http_headers(["Content-type: text/plain;charset=%s" % config.charset])
    #request.write('<html><head><meta name="robots" content="noindex,nofollow"></head>')

    try:
        page = Page(pagename, request, version=request.form['version'][0])
    except KeyError:
        try:
	  page = Page(pagename, request, prev_date=request.form['date'][0])
        except KeyError:
          page = Page(pagename, request)

    request.write(page.get_raw_body())
    #request.write('</html>')
    raise LocalWikiNoFooter


def do_format(pagename, request):
    # get the MIME type
    if request.form.has_key('mimetype'):
        mimetype = request.form['mimetype'][0]
    else:
        mimetype = "text/plain"

    # try to load the formatter
    Formatter = wikiutil.importPlugin("formatter",
        mimetype.translate(string.maketrans('/.', '__')), "Formatter")
    if Formatter is None:
        # default to plain text formatter
        del Formatter
        mimetype = "text/plain"
        from formatter.text_plain import Formatter

    #request.http_headers(["Content-Type: " + mimetype])
    request.http_headers(["Content-Type: " + 'text/plain'])

    Page(pagename, request, formatter = Formatter(request)).send_page()
    raise LocalWikiNoFooter


def do_chart(pagename, request):
    if request.user.may.read(pagename):
        chart_type = request.form['type'][0]
        func = pysupport.importName("LocalWiki.stats." + chart_type, "draw")
        func(pagename, request)
    raise LocalWikiNoFooter


def do_dumpform(pagename, request):
    data = util.dumpFormData(request.form)

    request.http_headers()
    request.write("<html><body>%s</body></html>" % data)
    raise LocalWikiNoFooter


def do_export(pagename, request):
    import shutil, cStringIO
    from LocalWiki.wikixml import wikiexport

    # Protect this with ACLs, when ready!

    # get parameters
    compression = request.form.get('compression', None)

    # prepare output stream
    fileid = time.strftime("%Y-%m-%d", request.user.getTime())
    filename = "wiki-export-%s.xml" % fileid 
    outbuff = cStringIO.StringIO()
    mimetype, out = 'text/xml', outbuff
    if compression == "gzip":
        import gzip
        mimetype, out = 'application/x-gzip', gzip.GzipFile(
            filename, "wb", 9, outbuff)
        filename = filename + '.gz'

    # create export document
    export = wikiexport.WikiExport(out, public=1)
    export.run()

    # send http headers
    headers = [
        "Content-Type: %s" % mimetype,
        "Content-Length: %d" % len(outbuff.getvalue()),
    ]
    if mimetype != 'text/xml':
        headers.append("Content-Disposition: attachment; filename=%s" % filename)
    request.http_headers(headers)

    # copy the body
    outbuff.reset()
    shutil.copyfileobj(outbuff, request, 8192)
    raise LocalWikiNoFooter


#############################################################################
### Dispatching
#############################################################################

def getPlugins():
    dir = os.path.join(config.plugin_dir, 'action')
    plugins = []
    if os.path.isdir(dir):
        plugins = pysupport.getPackageModules(os.path.join(dir, 'dummy'))
    return dir, plugins


def getHandler(action, identifier="execute"):
    # check for excluded actions
    if action in config.excluded_actions:
        return None

    # check for and possibly return builtin action
    handler = globals().get('do_' + action, None)
    if handler: return handler

    return wikiutil.importPlugin("action", action, identifier)
