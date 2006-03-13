# -*- coding: iso-8859-1 -*-

"""
    Sycamore - Action Handlers

    Actions are triggered by the user clicking on special links on the page
    (like the icons in the title, or the "Edit" link). The
    name of the action is passed in the "action" CGI parameter.

    The sub-package "Sycamore.action" contains external actions, you can
    place your own extensions there (similar to extension macros). User
    actions that start with a capital letter will be displayed in a list
    at the bottom of each page.

    User actions starting with a lowercase letter can be used to work
    together with a user macro; those actions a likely to work only if
    invoked BY that macro, and are thus hidden from the user interface.

    @copyright: 2000-2004 by J?rgen Hermann <jh@web.de>, 2005-2006 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, re, string, time, urllib
from Sycamore import config, util, wikiutil, user, search
from Sycamore.Page import Page
from Sycamore.util import SycamoreNoFooter, pysupport

#############################################################################
### Search
#############################################################################

def do_search(pagename, request, fieldname='inline_string', inc_title=1, pstart=0, tstart=0, twith=10, pwith=10):
    _ = request.getText
    start = time.clock()

    # send http headers
    request.http_headers()

    # get parameters
    if request.form.has_key(fieldname):
        needle = request.form[fieldname][0]
    elif request.form.has_key('string'):
        needle = urllib.unquote_plus(request.form['string'][0])
    elif request.form.has_key('text_new'):
        needle = urllib.unquote_plus(request.form['text_new'][0])
    else: needle = ''

    try:
        case = int(request.form['case'][0])
    except (KeyError, ValueError):
        case = 0

    context = 40
    max_context = 10 # only show first `max_context` contexts

    # check for sensible search term
    if len(needle) < 1:
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

    if needle[0] == needle[-1] == '"': printable_needle = needle[1:-1]
    else: printable_needle = needle
    # send title
    wikiutil.send_title(request, _('Search results for "%s"') % (printable_needle,))
    
    searchlog = open(config.data_dir + '/search.log','a')
    searchlog.write(needle + '\n')
    searchlog.close()

    this_search = search.Search(search.prepare_search_needle(needle), request, p_start_loc=pstart, t_start_loc=tstart, num_results=pwith+1) #, start_lock=)
    this_search.process()
    # don't display results they can't read
    title_hits = [title for title in this_search.title_results if request.user.may.read(title.page)]
    full_hits = [text for text in this_search.text_results if request.user.may.read(text.page)]
    if len(title_hits) < 1:
            request.write('<h3>&nbsp;No title matches</h3>')
            request.write('<table class="dialogBox"><tr><td>\n') # start content div
            request.write('The %s does not have any entries with the exact title "' % config.sitename+ printable_needle + '" <br />')
            request.write('Would you like to %s?' % (Page(printable_needle, request).link_to(text="create a new page with this title", know_status=True, know_status_exists=False)))
            request.write('</td></tr></table>\n')
    else:
            request.write('<h3>&nbsp;Title matches</h3>')
            if not title_hits[0].title.lower() == printable_needle.lower():
                    request.write('<table class="dialogBox"><tr><td>The %s does not have any entries with the exact title "' % config.sitename + printable_needle + '". <br />')
                    request.write('Would you like to %s?</td></tr></table>' % (Page(printable_needle, request).link_to(text="create a new page with this title", know_status=True, know_status_exists=False)))
    request.write('<div id="content">\n') # start content div
    request.write('<ul>')
    if len(title_hits) > twith:
            for t_hit in title_hits[0:twith]:
                    request.write('<li>%s</li>' % t_hit.page.link_to())
            request.write('</ul>')
            request.write('<p>(<a href="%s?action=search&string=%s&tstart=%s">next %s matches</a>)'
                    % (request.getScriptname(), needle, tstart+twith, twith))
            request.write('</div>\n') # end content div
    else:
            for t_hit in title_hits:
                    request.write('<li>%s</li>' % t_hit.page.link_to())
            request.write('</ul>')
            request.write('</div>\n') # end content div
    if len(full_hits) < 1:
      request.write('<h3>&nbsp;No full text matches</h3>')
    else:
      request.write('<h3>&nbsp;Full text matches</h3>')
      request.write('<div id="content">\n') # start content div
      request.write('<dl class="searchresult">')

      
      for full_hit in full_hits[0:pwith]:
        color = "#ff3333"
        if full_hit.percentage > 65:
          color = "#55ff55"
        elif full_hit.percentage > 32:
          color = "#ffee55"
        request.write('<p><table><tr><td width="40" valign="middle"><table id="progbar" cellspacing="0" cellpadding="0"><tr><td height="7" width="%d" bgcolor="%s"></td><td width="%d" bgcolor="#eeeeee"></td></tr></table></td><td>' % (full_hit.percentage/3, color, 33 - full_hit.percentage/3))
        request.write(full_hit.page.link_to())
        request.write('</td></tr></table>\n')

        if context:
	  print_context(this_search.terms, full_hit.data, request, context=context, max_context=max_context)
          
      if len(full_hits) > pwith:
         request.write('<p>&nbsp;(<a href="%s?action=search&string=%s&pstart=%s">next %s matches</a>)</div></dl>'
                        % (request.getScriptname(), urllib.quote_plus(needle), pstart+pwith, pwith))
      else:
         request.write('</div></dl>')

    wikiutil.send_footer(request, pagename, editable=0, showactions=0, form=request.form)

do_inlinesearch = do_search # for comptability to not break old urls in firefox extensions, etc.

def print_context(terms, text, request, context=40, max_context=10):
 """ Prints the search context surrounding a search result.  Makes found terms strong and shows some snippets."""
 padding = 10 # how much context goes around matched areas
 fragments = []
 out = []
 pos = 0
 fixed_text = text.lower()
 terms_with_location = []
 for term in terms:
   if type(term) == type([]): term_string = ' '.join(term) # means this is "exact match yo"
   else: term_string = term
   found_loc = fixed_text.find(term_string)
   while True:
     if found_loc == -1: break
     terms_with_location.append((term_string, found_loc))
     rel_position = fixed_text[found_loc+len(term_string):].find(term_string)
     if rel_position == -1:
       break
     found_loc += rel_position + len(term_string)
 
 terms_with_location.sort(lambda x,y: cmp(x[1],y[1]))
 i = 0
 text_with_context = []
 skip = False
 while i < len(terms_with_location):
   if not skip:
     term = terms_with_location[i][0]
     location = terms_with_location[i][1]
     # first context
     if not text_with_context:
       if location > padding:
         text_with_context.append(text[location-padding:location])
     text_with_context.append('<strong>%s</strong>' % text[location:location+len(term)])
   if i+1 < len(terms_with_location):
     next_term = terms_with_location[i+1][0]
     next_location = terms_with_location[i+1][1]
     if next_location - location < context - padding:
       text_with_context.append('%s<strong>%s</strong>' % (text[location+len(term):next_location], text[next_location:next_location+len(next_term)]))
       i += 1
       skip = True
       continue
     else:
       text_with_context.append('%s...%s' % (text[location+len(term):location+len(term)+padding], text[next_location-len(next_term)-padding:next_location]))
   else: # we are at the end of the list of terms
     text_with_context.append('%s' % text[location+len(term):location+len(term)+context])
   i += 1
   skip = False

 if location + padding + 1 < len(text):
   text_with_context.append('...')

 text_context = []

 # pad the text with context with more context to the left and right, if needed
       
 request.write('<div class="textSearchResult">%s</div>' % ''.join(text_with_context))

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
    all_pages = wikiutil.getPageList(request, alphabetize=True)
    hits = filter(needle_re.search, all_pages)

    hits = [Page(hit, request) for hit in hits]
    hits = filter(request.user.may.read, hits)

    request.write('<div id="content">\n') # start content div
    request.write('<ul>')
    for page in hits:
        request.write('<li>%s</li>' % page.link_to())
    request.write('</ul>')

    print_search_stats(request, len(hits), len(all_pages), start)
    request.write('</div>\n') # end content div
    wikiutil.send_footer(request, pagename, editable=0, showactions=0, form=request.form)


def do_highlight(pagename, request):
    if request.form.has_key('value'):
        needle = request.form["value"][0]
    else:
        needle = ''

    needle_re = search.build_regexp(search.prepare_search_needle(needle))

    #try:
    #    needle_re = re.compile(needle, re.IGNORECASE)
    #except re.error:
    #    needle = re.escape(needle)
    #    needle_re = re.compile(needle, re.IGNORECASE)

    Page(pagename, request).send_page(hilite_re=needle_re)


#############################################################################
### Misc Actions
#############################################################################

def do_diff(pagename, request, in_wiki_interface=True, text_mode=False, version1=None, version2=None, diff1_date='', diff2_date=''):
    """ Handle "action=diff"
        checking for either a "date=backupdate" parameter
        or date1 and date2 parameters
    """
    l = []
    page = Page(pagename, request)
    if not request.user.may.read(page):
        page.send_page()
        return

    # version numbers
    try:
        if version1 is None: version1 = request.form['version1'][0]
        try:
            version1 = int(version1)
        except StandardError:
            version1 = None
    except KeyError:
        version1 = None

    try:
        if version2 is None: version2 = request.form['version2'][0]
        try:
            version2 = int(version2)
        except StandardError:
            version2 = None
    except KeyError:
        version2 = None 

    
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

	if diff1_date > 0:
	  version1 = page.date_to_version_number(diff1_date)

    if not version1 and not version2:
      # we are pressing 'diff' in the recent changes/etc
      page = Page(pagename, request)
      current_mtime = page.mtime()
      current_version = page.date_to_version_number(current_mtime)
      version2 = current_version
      version1 = current_version - 1

  
    # spacing flag?
    try:
        ignorews = int(request.form['ignorews'][0])
    except (KeyError, ValueError, TypeError):
        ignorews = 0

    _ = request.getText
    
    if in_wiki_interface:
      request.http_headers()
      wikiutil.send_title(request, _('Differences for "%s"') % (pagename,), pagename=pagename)
    else:
      l.append("Differences for %s" % (pagename))
  
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
    elif diff1_date is None:
        oldpage = Page(pagename, request)
        # oldcount1 is still on init value 0
    else:
        if olddate1:
            oldpage = Page(pagename, request, prev_date=olddate1)
        else:
            oldpage = Page("$EmptyPage$", request) # XXX: ugly hack
            oldpage.set_raw_body("")    # avoid loading from db
            
    if diff2_date is None:
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

    old_mtime = oldpage.mtime()
    new_mtime = newpage.mtime()
    if version2 == 1: old_version = 1
    else: old_version = oldpage.get_version()
    new_version = newpage.get_version()
    max_mtime = max(old_mtime, new_mtime)
    if version1:
      min_version = min(old_version, new_version)
      is_oldest = False
    else: is_oldest = True

    max_version = max(old_version, new_version)
    previous_edit = []
    this_edit = []

    if version1:
      previous_user_link = user.getUserLink(request, user.User(request, id=oldpage.edit_info()[1]))
      previous_edit.append('<div>version %s (%s by %s)</div>' % (old_version, oldpage.mtime_printable(old_mtime), previous_user_link))
      this_user_link = user.getUserLink(request, user.User(request, id=newpage.edit_info()[1]))
      this_edit.append('<div>version %s (%s by %s)</div>' % (new_version, newpage.mtime_printable(new_mtime), this_user_link))
    else:
      previous_edit.append('<div>version 0</div>')
      this_user_link = user.getUserLink(request, user.User(request, id=newpage.edit_info()[1]))
      this_edit.append('<div>version %s (%s by %s)</div>' % (1, newpage.mtime_printable(), this_user_link))
  
    if edit_count > 1:
        l.append(' ' + _('(spanning %d versions)') % (edit_count,))
    l.append('</strong></p>')

    if in_wiki_interface:
      current_mtime = Page(pagename, request).mtime()
      is_current = (current_mtime == max_mtime)
      
      if not is_current:
	this_edit.append('<div align="right" style="margin: 2pt 0 0 0;">%s</div>' % newpage.link_to(text="next edit&rarr;", querystr="action=diff&amp;version2=%s&amp;version1=%s" % (max_version+1, max_version)))
      if not is_oldest:
        previous_edit.append('<div align="left" style="margin: 2pt 0 0 0;">%s</div>' % newpage.link_to(text="&larr;previous edit", querystr="action=diff&amp;version2=%s&amp;version1=%s" % (min_version, min_version-1)))
        
      l.append('<div style="float:left;">%s</div><div style="float:right;">%s</div><div style="clear:both; padding: 3pt;"></div>' % (''.join(previous_edit), ''.join(this_edit)))
	
  
    from Sycamore.util.diff import diff
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

    if not request.user.may.read(page):
    	request.http_headers()
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
            request.write('<p>%s<br>' % _('This page links to the following pages:'))
            for linkedpage in links_from_page:
                request.write("%s%s " % (Page(linkedpage, request).link_to(), ",."[linkedpage == links_from_page[-1]]))
            request.write("</p>")
	else: request.write('<p>This page links to <b>no pages</b>.</p>')

	links_to_page = page.getPageLinksTo()
        if links_to_page:
            request.write('<p>%s<br>' % _('The following pages link to this page:'))
            for linkingpage in links_to_page:
                request.write("%s%s " % (Page(linkingpage, request).link_to(), ",."[linkingpage == links_to_page[-1]]))
            request.write("</p>")
	else: request.write('<p><b>No pages</b> link to this page.</p>')


    def history(page, pagename, request):
	def printNextPrev(request, pagename, last_version, offset_given):
	  #prints the next and previous links, if they're needed
	  html = '<p>'
	  if last_version != 1:
	    html += '[<a href="%s/%s?action=info&offset=%s">&larr;previous edits</a> | ' % (request.getBaseURL(), pagename, offset_given+1)
	  else:
	    html += '[&larr;previous edits | '
	  if offset_given:
	    html += '<a href="%s/%s?action=info&offset=%s">next edits&rarr;</a>]' % (request.getBaseURL(), pagename, offset_given-1) 
	  else:
	    html += 'next edits&rarr;]'
	  html += '</p>'
	  request.write(html)



        # show history as default
        from stat import ST_MTIME, ST_SIZE
        _ = request.getText

        request.write('<h2>%s</h2>\n' % _('Revision History'))

        from Sycamore.util.dataset import TupleDataset, Column

	has_history = False

        history = TupleDataset()
        history.columns = [
            Column('count', label='#', align='right'),
            Column('mtime', label=_('Date'), align='right'),
            Column('diff', label='<input type="submit" value="%s">' % (_("Compare"))),
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
        may_revert = request.user.may.revert(page)
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
	    from Sycamore.widget.comments import Comment
	    comment = Comment(request, comment, editType, pagename).render()
   	    
	    if entry[2]:
	    	editUser = user.User(request, entry[2])
            	editUser_text = user.getUserLink(request, editUser)
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
        from Sycamore.widget.browser import DataBrowserWidget
        from Sycamore.formatter.text_html import Formatter

        request.write('<form method="GET" action="%s">\n' % (page.url()))
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
	  request.write('<p>This page has no revision history.  This is probably because the page was never created.</p></div>')


    _ = request.getText
    qpagename = wikiutil.quoteWikiname(pagename)

    request.http_headers()

    wikiutil.simple_send_title(request, pagename, strict_title='Info for "%s"' % pagename)

    request.write('<div id="content">\n') # start content div

    show_general = int(request.form.get('general', [0])[0]) != 0
    
    from Sycamore.widget.infobar import InfoBar
    InfoBar(request, pagename).render()

    if show_general:
	general(page, pagename, request)
    else:
	history(page, pagename, request)

    request.write('</div>\n') # end content div
    wikiutil.send_footer(request, pagename, showpage=1, noedit=True)


def do_recall(pagename, request):
    # We must check if the current page has different ACLs.
    page = Page(pagename, request)
    if not request.user.may.read(page):
        page.send_page()
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
#        from Sycamore import caching
#        cache = caching.CacheEntry(request.form["key"][0])
#        cache.clear()
#    do_show(pagename, request)


def do_print(pagename, request):
    do_show(pagename, request)


def do_content(pagename, request):
    request.http_headers()
    page = Page(pagename, request)
    request.write('<!-- Transclusion of %s -->' % request.getQualifiedURL(page.url()))
    page.send_page(count_hit=0, content_only=1)
    raise SycamoreNoFooter


def do_edit(pagename, request):
    page = Page(pagename, request)
    if not request.user.may.edit(page):
        _ = request.getText
        page.send_page(
            msg = _('You are not allowed to edit this page.'))
        return
    from Sycamore.PageEditor import PageEditor
    if isValidPageName(pagename):
        PageEditor(pagename, request).sendEditor()
    else:
        _ = request.getText
        Page(pagename, request).send_page(msg = _('Invalid pagename: Only the characters A-Z, a-z, 0-9, "$", "&", ",", ".", "!", "\'", ":", ";", " ", "/", "-", "(", ")" are allowed in page names.'))

def isValidPageName(name):
    return not re.search('[^A-Za-z\-0-9 $&\.\,:;/\'\!\(\)]',name)

def do_savepage(pagename, request):
    from Sycamore.PageEditor import PageEditor

    _ = request.getText

    page = Page(pagename, request)
    if not request.user.may.edit(page):
        page.send_page(
            msg = _('You are not allowed to edit this page.'))
        return

    pg = PageEditor(pagename, request)
    savetext = request.form.get('savetext', [''])[0]
    datestamp = float(request.form.get('datestamp', [''])[0])
    comment = request.form.get('comment', [''])[0]
    category = request.form.get('category', [None])[0]
    rstrip = True
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
            from Sycamore.util import diff3
            original_text = Page(pg.page_name, request, prev_date=datestamp).get_raw_body()
            saved_text = pg.get_raw_body()
            verynewtext, had_conflict = diff3.text_merge(original_text, saved_text, savetext, 
                 marker1='----- /!\ Edit conflict! Other version: -----\n',
                 marker2='----- /!\ Edit conflict! Your version: -----\n',
                 marker3='----- /!\ End of edit conflict -----\n')
            if had_conflict:
                msg = _("""Someone else changed this page while you were editing.
There was an <b>edit conflict between your changes!</b> Please review the conflicts and merge the changes.""")
                request.form['datestamp'] = [pg.mtime()]
                pg.sendEditor(msg=msg, comment=request.form.get('comment', [''])[0],
                              preview=verynewtext, staytop=1, had_conflict=True)
	    return
        except pg.SaveError, msg:
            savemsg = msg
        request.reset()
        backto = request.form.get('backto', [None])[0]
        if backto:
            pg = Page(backto, request)

	# clear request cache so that the user sees the page as existing
	request.req_cache['pagenames'][pagename.lower()] = pagename
        pg.send_page(msg=savemsg, send_headers=False)
        #request.http_redirect(pg.url())

def do_favorite(pagename, request):
    """ Add the current wiki page to the favorites list in the user's
        profile file.
    """ 
    _ = request.getText

    page = Page(pagename, request)
    if request.form.has_key('delete'):
       removed_pagename = wikiutil.unquoteWikiname(request.form.get('delete')[0])
       request.user.favorites = request.user.getFavorites()
       request.user.delFavorite(removed_pagename)
       msg = _("Page '%s' removed from Bookmarks" % removed_pagename)

    elif not request.user.may.read(page):
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

    page = Page(pagename, request)
    if not request.user.may.read(page):
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
    from Sycamore import userform
    savemsg = userform.savedata(request) # we end up sending cookie headers here..possibly
    request.setHttpHeader(("Content-Type", "text/html"))
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
    request.http_headers()
    Page(pagename, request).send_page()

def do_showcomments(pagename, request):
    hideshow = 'showcomments'
    if request.form.has_key('hide'):
        hideshow = 'hidecomments'
    request.user.setShowComments(hideshow)
    Page(pagename, request).send_page()

def do_formtest(pagename, request):
    # test a user defined form
    from Sycamore import wikiform
    wikiform.do_formtest(pagename, request)


# def do_macro(pagename, request):
#     """ Execute a helper action within a macro.
#     """

#     from Sycamore import wikimacro
#     from Sycamore.formatter.text_html import Formatter
#     from Sycamore.parser.wiki import Parser
#     from Sycamore.Page import Page
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
    page = Page(pagename, request)
    if not request.user.may.read(page):
        page.send_page()
        return

    request.http_headers([("Content-type", "text/plain;charset=%s" % config.charset)])
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
    raise SycamoreNoFooter


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
    raise SycamoreNoFooter



def do_dumpform(pagename, request):
    data = util.dumpFormData(request.form)

    request.http_headers()
    request.write("<html><body>%s</body></html>" % data)
    raise SycamoreNoFooter



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
