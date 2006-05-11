# coding: iso-8859-1 -*-
"""
    Sycamore - Page class

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import cStringIO, os, re, urllib, os.path, random
from Sycamore import config, user, util, wikiutil, wikidb 
import cPickle
#import Sycamore.util.web

class Page(object):
    """Page - Manage an (immutable) page associated with a WikiName.
       To change a page's content, use the PageEditor class.
    """

    def __init__(self, page_name, request, **keywords):
        """
        Create page object.

        Note that this is a 'lean' operation, since the text for the page
        is loaded on demand. Thus, things like `Page(name).link_to()` are
        efficient.

        @param page_name: Wiki name of the page
	@param cursor: db cursor 
        @keyword prev_date: date of older revision
	@keyword revision: revision number of older revision
        @keyword formatter: formatter instance
	@keyword req_cache: per-req cache of some information
        """
        self.page_name = page_name.lower()
	self.given_name = page_name
	self.request = request
        self.cursor = request.cursor
	self.date = None

        self.prev_date = keywords.get('prev_date')
	if self.prev_date:
	  self.prev_date = float(self.prev_date)
	  self.version = self.date_to_version_number(self.prev_date)
	  self.date = self.prev_date
	else:
	  # see if they gave revision info 
	  self.version = keywords.get('version')
	  if self.version:
	    self.version = int(self.version)
	    self.prev_date = self.version_number_to_date(self.version)
	    self.date = self.prev_date

        self._raw_body = None
        self._raw_body_modified = 0
        self.hilite_re = None
        
        if keywords.has_key('formatter'):
            self.formatter = keywords.get('formatter')
            self.default_formatter = 0
        else:
            self.default_formatter = 1

    def get_date(self):
      # returns date this page/verison was created
      if self.version and not self.date:
        self.date = self.version_number_to_date(self.version)
	return self.date
      elif not self.date:
        self.date = self.last_edit_info()[0]
      return self.date

    def get_version(self):
      # returns date this page/verison was created
      if self.date and not self.version:
        self.version = self.date_to_version_number(self.date)
	return self.version
      elif not self.version:
        self.date = self.last_edit_info()[0]
	self.version = self.date_to_version_number(self.date)
      return self.version


    def version_number_to_date(self, version_number):
        # Returns the unix timestamp of the editTime of this version of the page.
        self.cursor.execute("SELECT editTime from allPages where name=%(page_name)s order by editTime asc limit 1 offset %(version)s;", {'page_name':self.page_name, 'version':version_number-1})
        result = self.cursor.fetchone()
        return result[0]

    def date_to_version_number(self, date):
        # Returns the version number of a given date of this page
        self.cursor.execute("SELECT count(editTime) from allPages where name=%(page_name)s and editTime<=%(date)s;", {'page_name':self.page_name, 'date':date})
        result = self.cursor.fetchone()
        return result[0]


    def edit_info(self):
      # Returns returns user edited and mtime for the page's version
      edit_info = None

      if not self.request.generating_cache:
        # get page info from cache or database
        from Sycamore import caching
        return caching.pageInfo(self).edit_info
      else:
        # We're generating the cache, so let's just get the edit info manually from the DB
	self.request.cursor.execute("SELECT editTime, userEdited from curPages where name=%(pagename)s", {'pagename':self.page_name})
	return self.request.cursor.fetchone()

      
    def last_edit_info(self):
       """
       Returns info about the last edit on the page.
       Returns tuple of editTime(double), userEdited(id)
       """
       return self.edit_info()


    def last_modified_str(self):
        """
        Return the last modified info.
        
        @param request: the request object
        @rtype: string
        @return: timestamp and editor information
        """
	request = self.request
        if not self.exists():
            return None

	editTimeUnix, userEditedID = self.last_edit_info()
	editTime = request.user.getFormattedDateTime(editTimeUnix)
	result = "(last edited %(time)s)" % {
                'time': editTime,
            }

        return result

    def proper_name(self):
      """
      Gets the properly cased pagename.
      """
      proper_name_exists = self.exists()
      if proper_name_exists: return proper_name_exists
      else: return self.given_name

    def make_exact_prev_date(self):
      """
      Some functions, such as diff, like to use an inexact previous date.  We convert this to a real previous date of a page, or return False.
      """
      if self.prev_date:
        self.request.cursor.execute("SELECT editTime from allPages where name=%(pagename)s and editTime<=%(date)s order by editTime desc limit 1", {'date':self.prev_date, 'pagename':self.page_name})
	result = self.request.cursor.fetchone()
	if not result: return False
	self.prev_date = result[0]
	return self.prev_date


    def exists(self):
        """
        Does this page exist?
        
        @rtype: bool or string
        @return: false, if page doesn't exist. otherwise returns proper pagename
        """
	proper_pagename = False
	memcache_hit = False
	if self.request.req_cache['pagenames'].has_key(self.page_name):
	  return self.request.req_cache['pagenames'][self.page_name]
	if config.memcache:
	  proper_pagename = self.request.mc.get("pagename:%s" % wikiutil.quoteFilename(self.page_name))
	  if proper_pagename is not None:
	    memcache_hit = True
	  else: proper_pagename = False
	if not proper_pagename and not memcache_hit:
	  self.cursor.execute("SELECT propercased_name from curPages where name=%(pagename)s", {'pagename': self.page_name})
	  result = self.cursor.fetchone()
	  if result: proper_pagename = result[0]
	  if config.memcache:
	    self.request.mc.add("pagename:%s" % wikiutil.quoteFilename(self.page_name), proper_pagename)

        self.request.req_cache['pagenames'][self.page_name] = proper_pagename
	return proper_pagename


    def size(self):
        """
        Get Page size.
        
        @rtype: int
        @return: page size, 0 for non-existent pages.
        """
	if not self._raw_body:
	  body = self.get_raw_body()
	else: body = self._raw_body
        if body is not None:
            return len(body)
	else: return 0

    def isRedirect(self):
        """
        If the page is a redirect this returns True.  If not it returns False.
        """
        body = self.get_meta_text()
        if body[0:9] == '#redirect': return True
        return False

    def hasMapPoints(self):
      from Sycamore import caching
      if not self.prev_date:
        return caching.pageInfo(self).has_map
      else: 
        return caching.pageInfo(Page(self.page_name, self.request)).has_map


    def human_size(self):
	"""
	Human-readable (in 'words') size of the page.
	"""
	if not self._raw_body:
	  body = self.get_raw_body()
	else: body = self._raw_body
	if body is not None:
	    return len(body.split())
	else: return 0

    def mtime(self):
        """
        Get modification timestamp of this page.
        
        @rtype: int
        @return: mtime of page (or 0 if page does not exist)
        """
	if not self.prev_date:
	   if self.last_edit_info(): return self.last_edit_info()[0]
	   return 0
        else:
	  self.cursor.execute("SELECT editTime from allPages where name=%(page_name)s and editTime <= %(prev_date)s order by editTime desc limit 1;", {'page_name':self.page_name, 'prev_date':self.prev_date})
        result = self.cursor.fetchone()
	if result:
          if result[0]: return result[0]
	else: return 0

    def ctime(self):
        """
	Gets the cached time of the page.
	"""
	from Sycamore import caching
	cache = caching.CacheEntry(self.page_name, self.request)
	return cache.mtime()

    def mtime_printable(self, t=None):
        """
        Get printable modification timestamp of this page.

       	@ optional param t: unix mtime 
        @rtype: string
        @return: formatted string with mtime of page
        """
        if not t: t = self.mtime()
        if not t:
            result = "0" # TODO: i18n, "Ever", "Beginning of time"...?
        else:
            result = self.request.user.getFormattedDateTime(t)
        return result

    def get_meta_text(self):
      """
      Returns the meta text of a page.  This includes things that start iwth # at the beginning of page's text, such as #acl and #redirect.
      """
      if self.exists():
        from Sycamore import caching
	if not self.request.generating_cache:
          return caching.pageInfo(self).meta_text
	else:
	  # we are generating the cache so we need to get this directly
	  return caching.find_meta_text(self)
	  
      else: return ''
              
    
    def get_raw_body(self):
        """
        Load the raw markup from the page file.
        
        @rtype: string
        @return: raw page contents of this page
        """
	text = None
        if self._raw_body is None:
	  if not self.prev_date:
	    if config.memcache:
	      text = self.request.mc.get("page_text:%s" % (wikiutil.quoteFilename(self.page_name.lower())))

	    if text is None:
	      self.cursor.execute("SELECT text from curPages where name=%(page_name)s", {'page_name':self.page_name})
	      result = self.cursor.fetchone()
	      if result: text = result[0]
	      else: text = ''
	      if config.memcache:
	        self.request.mc.add("page_text:%s" % wikiutil.quoteFilename(self.page_name.lower()), text)
	  else:
	    if config.memcache:
	      text = self.request.mc.get("page_text:%s,%s" % (wikiutil.quoteFilename(self.page_name.lower()), repr(self.prev_date)))
	    if not text:
	      self.cursor.execute("SELECT text, editTime from allPages where (name=%(page_name)s and editTime<=%(prev_date)s) order by editTime desc limit 1", {'page_name':self.page_name, 'prev_date':self.prev_date})
	      result = self.cursor.fetchone()
	      if result: text = result[0]
	      else: text = ''
	      if config.memcache:
	        self.request.mc.add("page_text:%s,%s" % (wikiutil.quoteFilename(self.page_name.lower()), repr(self.prev_date)), text)
            
          self.set_raw_body(text)

        return self._raw_body


    def set_raw_body(self, body, modified=0):
        """
        Set the raw body text (prevents loading from disk).

        @param body: raw body text
        @param modified: 1 means that we internally modified the raw text and
                         that it is not in sync with the page file on disk.
                         This is used e.g. by PageEditor when previewing the page.
        """
        self._raw_body = body
        self._raw_body_modified = modified

    def url(self, querystr=None):
        """
        Return an URL for this page.

        @param request: the request object
        @param querystr: the query string to add after a "?" after the url
        @rtype: string
        @return: complete url of this page (including query string if specified)
        """
        url = "%s/%s" % (self.request.getScriptname(), wikiutil.quoteWikiname(self.proper_name()))
        if querystr:
            querystr = util.web.makeQueryString(querystr)
            url = "%s?%s" % (url, querystr)
        return url

    def link_to(self, text=None, querystr=None, anchor=None, know_status=False, know_status_exists=False, guess_case=False, **kw):
        """
        Return HTML markup that links to this page.
        See wikiutil.link_tag() for possible keyword parameters.

        @param request: the request object
        @param text: inner text of the link
        @param querystr: the query string to add after a "?" after the url
        @param anchor: if specified, make a link to this anchor
        @keyword attachment_indicator: if 1, add attachment indicator after link tag
        @keyword css_class: css class to use
	@keyword know_status: for slight optimization.  if True that means we know whether the page exists or not
	   (saves a query)
	  @ keyword know_status exists: if True that means the page exists, if False that means it doesn't
        @rtype: string
        @return: formatted link
        """
	request = self.request
	if know_status_exists and know_status: know_exists = True
	else: know_exists = False
        text = text
        fmt = getattr(self, 'formatter', None)
        if not know_status:
          if self.exists():
	  	know_exists = True
		url_name = self.proper_name()
          else:
		if self.given_name and not guess_case:  # did we give Page(a name of a page here..) ?
		  url_name = self.given_name
	        elif guess_case:
		  self.request.cursor.execute("SELECT propercased_name from allPages where name=%(name)s and editTime=%(latest_mtime)s", {'name':self.page_name, 'latest_mtime':self.mtime()})
	          result = self.request.cursor.fetchone()
	          if result: url_name = result[0]
		else:
		  url_name = self.given_name
	    
        else:
	  url_name = self.given_name
          
	url = wikiutil.quoteWikiname(url_name)

	if not text:
	  text = url_name
 
        if querystr:
            querystr = util.web.makeQueryString(querystr)
            url = "%s?%s" % (url, querystr)
        if anchor: url = "%s#%s" % (url, urllib.quote_plus(anchor))

        # create a link to attachments if any exist
        attach_link = ''
        if kw.get('attachment_indicator', 0):
            from Sycamore.action import AttachFile
            attach_link = AttachFile.getIndicator(request, self.page_name)

        if know_exists:
            return '%s%s' % (wikiutil.link_tag(request, url, text, formatter=fmt, **kw),  attach_link)
        else:
            kw['css_class'] = 'nonexistent'
            return '%s%s' % (wikiutil.link_tag(request, url, text, formatter=fmt, **kw), attach_link)

    def send_page(self, msg=None, **keywords):
        """
        Output the formatted page.

        @param request: the request object
        @param msg: if given, display message in header area
        @keyword content_only: if 1, omit page header and footer
        @keyword count_hit: if 1, add an event to the log
        @keyword hilite_re: a regular expression for highlighting e.g. search results
        """
	request = self.request
        _ = request.getText

        # determine modes
        if request.form:
	  print_mode = request.form.has_key('action') and request.form['action'][0] == 'print'
	else: print_mode = False
        content_only = keywords.get('content_only', 0)
        content_id = keywords.get('content_id', 'content')
        self.hilite_re = keywords.get('hilite_re', None)
	self.preview = keywords.get('preview', 0)
	if self.preview: self.request.previewing_page = True
        if msg is None: msg = ""
	polite_msg = ""

        # load the meta-text
        meta_text = self.get_meta_text()

        # if necessary, load the default formatter
        if self.default_formatter:
            from Sycamore.formatter.text_html import Formatter
            self.formatter = Formatter(request, store_pagelinks=1, preview=self.preview)
        self.formatter.setPage(self)
        request.formatter = self.formatter

        # default is wiki markup
        pi_format = config.default_markup or "wiki"
        pi_redirect = None
        pi_refresh = None
        pi_formtext = []
        pi_formfields = []
        wikiform = None

        # check for XML content
        #if body and body[:5] == '<?xml':
        #    pi_format = "xslt"

        # check processing instructions
        while meta_text:
            # extract first line
            try:
                line, meta_text = meta_text.split('\n', 1)
            except ValueError:
                line = meta_text
                meta_text = ''

            # end parsing on empty (invalid) PI
            if line == "#":
                meta_text = line + '\n' + meta_text
                break

            # skip comments (lines with two hash marks)
            if line[1] == '#': continue

            # parse the PI
            verb, args = (line[1:]+' ').split(' ', 1)
            verb = verb.lower()
            args = args.strip()

            # check the PIs
            if verb == "format":
                # markup format
                pi_format = args.lower()
            elif verb == "refresh":
                if config.refresh:
                    try:
                        mindelay, targetallowed = config.refresh
                        args = args.split()
                        if len(args) >= 1:
                            delay = max(int(args[0]), mindelay)
                        if len(args) >= 2:
                            target = args[1]
                        else:
                            target = self.page_name
                        if target.find('://') >= 0:
                            if targetallowed == 'internal':
                                raise ValueError
                            elif targetallowed == 'external':
                                url = target
                        else:
                            url = Page(target, request).url()
                        pi_refresh = {'delay': delay, 'url': url, }
                    except (ValueError,):
                        pi_refresh = None
            elif verb == "redirect":
                # redirect to another page
                # note that by including "action=show", we prevent
                # endless looping (see code in "request") or any
                # cascaded redirection
                pi_redirect = args
                if request.form.has_key('action') or request.form.has_key('redirect') or content_only: continue

                request.http_redirect('%s/%s?action=show&redirect=%s' % (
                    request.getScriptname(),
                    wikiutil.quoteWikiname(pi_redirect),
                    urllib.quote_plus(self.proper_name(), ''),))
                return
            elif verb == "acl":
                # We could build it here, but there's no request.
                pass
            else:
                # unknown PI ==> end PI parsing, and show invalid PI as text
                meta_text = line + '\n' + meta_text
                break

        # start document output
        doc_leader = self.formatter.startDocument(self.page_name)
        if not content_only:
            if self.request.user.valid: self.request.user.checkFavorites(self.page_name)

            # send the document leader
            request.http_headers()
            request.write(doc_leader)

            # send the page header
	    proper_name = self.proper_name()
            if self.default_formatter:
                page_needle = self.page_name
                if config.allow_subpages and page_needle.count('/'):
                    page_needle = '/' + page_needle.split('/')[-1]
                link = '%s/%s?action=info&links=1' % (
                    request.getScriptname(),
                    wikiutil.quoteWikiname(proper_name))

                title = proper_name
                if self.prev_date:
                    msg = "<strong>%s</strong><br>%s" % (
                        _('Version %(version)s (%(date)s)') % {'version': self.get_version(),
			'date': request.user.getFormattedDateTime(self.prev_date) },
                            
                        msg)
                
                if request.form.has_key('redirect'):
                    redir = request.form['redirect'][0]
                    polite_msg = 'Redirected from ' + wikiutil.link_tag(request, wikiutil.quoteWikiname(redir) + '?action=show', redir)
                if pi_redirect and not msg:
                    msg = '<strong>%s</strong><br>' % (_('This page redirects to page %(page)s') % {'page': Page(pi_redirect, request).link_to()})
                        
                
                # Page trail
                trail = None
                #if not print_mode and request.user.valid and request.user.show_page_trail:
                #    request.user.addTrail(self.page_name)
                #    trail = request.user.getTrail()
                wikiutil.send_title(request, title, link=link, msg=msg,
                    pagename=proper_name, print_mode=print_mode, pi_refresh=pi_refresh,
                    allow_doubleclick=1, trail=trail, polite_msg=polite_msg, body_onload="highlighter.highlight();")

                # user-defined form preview?
                # Todo: check if this is also an RTL form - then add ui_lang_attr
                if pi_formtext:
                    pi_formtext.append('<input type="hidden" name="fieldlist" value="%s">\n' %
                        "|".join(pi_formfields))
                    pi_formtext.append('</form></table>\n')
                    pi_formtext.append(_(
                        '<p><small>If you submit this form, the submitted values'
                        ' will be displayed.\nTo use this form on other pages, insert a\n'
                        '<br><br><strong><tt>&nbsp;&nbsp;&nbsp;&nbsp;'
                        '[[Form("%(pagename)s")]]'
                        '</tt></strong><br><br>\n'
                        'macro call.</small></p>\n'
                    ) % {'pagename': self.page_name})
                    request.write(''.join(pi_formtext))

        # try to load the parser
        Parser = wikiutil.importPlugin("parser", pi_format, "Parser")
        if Parser is None:
            # default to plain text formatter (i.e. show the page source)
            del Parser
            from parser.plain import Parser
        
        # start wiki content div
        # Content language and direction is set by the theme
        lang_attr = request.theme.content_lang_attr()
	if self.hilite_re:
		request.write('<table width="100%%"><tr><td align="right">[<strong class="highlight">%s</strong>]</td></tr></table>' % self.link_to(text="highlighting off"))
        if not self.preview:
          request.write('<div id="%s" class="%s wikipage" %s>\n' % (content_id, content_id, lang_attr))
        else:
          request.write('<div class="%s wikipage" %s>\n' % (content_id, lang_attr))
        
        # new page?
        if not self.exists() and not content_only and not self.prev_date:
            self._emptyPageText()
        elif not request.user.may.read(self):
            request.write("<strong>%s</strong><br>" % _("You are not allowed to view this page."))
        else:
            # parse the text and send the page content
            self.send_page_content(Parser)

            
        # end wiki content div
        request.write('<div style="clear: both;"></div></div>\n')
        
        # end document output
        doc_trailer = self.formatter.endDocument()
        if not content_only:
            # send the page footer
            if self.default_formatter and not print_mode:
                wikiutil.send_footer(request, self.page_name, print_mode=print_mode)

            request.write(doc_trailer)
        
        #if self.default_formatter and self.exists():
        #    arena = "Page.py"
        #    key   = self.page_name
        #    cache = caching.CacheEntry(arena, key)
        #    if cache.needsUpdate():
	#	#links is a list of strings
        #        links = self.formatter.pagelinks
	#	db = wikidb.connect()
	#	cursor = db.cursor()
	#	cursor.execute("start transaction;")
	#	cursor.execute("DELETE from links where source_pagename=%s", (key))
	#	for link in links:
	#	  cursor.execute("INSERT into links set source_pagename=%s, destination_pagename=%s", (key, link))
	#	cursor.execute("commit;")
	#	cursor.close()
	#	db.close()


    def send_page_content(self, Parser, needsupdate=0):
        """
        Output the formatted wiki page, using caching, if possible.

        @param request: the request object
        @param Parser: the Parser
        @param body: text of the wiki page
        @param needsupdate: if 1, force update of the cached compiled page
        """
	body = ''
	request = self.request
        formatter_name = str(self.formatter.__class__).\
                         replace('Sycamore.formatter.', '').\
                         replace('.Formatter', '')

        # if no caching
        if  (self.prev_date or self.hilite_re or self._raw_body_modified or
            (not getattr(Parser, 'caching', None)) or
            (not formatter_name in config.caching_formats)) or self.request.generating_cache:
            # parse the text and send the page content
	    body = self.get_raw_body()
            Parser(body, request).format(self.formatter)
            return

        #try cache
        _ = request.getText
        from Sycamore import wikimacro, caching
        key = self.page_name
        cache = caching.CacheEntry(key, request)
        code = None
        if cache.needsUpdate():
            needsupdate = 1

        # load cache
        if not needsupdate:
            try:
		import marshal
                code = marshal.loads(cache.content())
            except ValueError: #bad marshal data
	    	print 'bad marshal'
                needsupdate = 1

        # render page
        if needsupdate:
	    body = self.get_raw_body()
            from Sycamore.formatter.text_python import Formatter
            formatter = Formatter(request, ["page"], self.formatter, preview=True)

	    # clear the page's dependencies
	    caching.clear_dependencies(self.page_name, request)

	    # need to do HTML parsing to get the pagelinks
	    from Sycamore.formatter.text_html import Formatter
            html_formatter = Formatter(request, store_pagelinks=1)
            html_formatter.setPage(self)
	    buffer = cStringIO.StringIO()
	    request.redirect(buffer)
	    html_parser = Parser(body, request)
	    html_parser.format(html_formatter)
	    request.redirect()
            
            import marshal
            buffer = cStringIO.StringIO()
            request.redirect(buffer)
            parser = Parser(body, request)
            parser.format(formatter)
            request.redirect()
            text = buffer.getvalue()
            buffer.close()
            links = html_formatter.pagelinks_propercased
            src = formatter.assemble_code(text)
	    #request.write(src) # debug 
            code = compile(src, self.page_name, 'exec')
	    code_string = marshal.dumps(code)
            cache.update(code_string, links)
        else:
           parser = Parser(body, request)
            
        # send page
        formatter = self.formatter
        macro_obj = wikimacro.Macro(parser)
        try:
 	    # figure out the link status' all at once to improve performance on pages w/lots of links
  	    caching.getPageLinks(self.page_name, self.request)

	    # execute the python code we serialized -- this prints the page content and macros/etc
            exec code
        except 'CacheNeedsUpdate': # if something goes wrong, try without caching
	    body = self.get_raw_body()
            self.send_page_content(Parser, body, needsupdate=1)
            cache = caching.CacheEntry(key, request)
            

    def _emptyPageText(self):
        """
        Output the default page content for new pages.
        
        @param request: the request object
        """
        from Sycamore.action import LikePages
	request = self.request
        _ = request.getText
  
        request.write(self.formatter.paragraph(1))
        request.write(wikiutil.link_tag(request,
            wikiutil.quoteWikiname(self.proper_name())+'?action=edit',
            _("Create this page")))
        request.write(self.formatter.paragraph(0))
  
        # look for template pages
        templates = filter(lambda page, u = wikiutil: u.isTemplatePage(page),
            wikiutil.getPageList(request))
        if templates:
            templates.sort()

            request.write(self.formatter.paragraph(1) +
                self.formatter.text(_('Whenever appropriate, please use one of these templates:')) +
                self.formatter.paragraph(0))

            # send list of template pages
            request.write(self.formatter.bullet_list(1))
            for page in templates:
                request.write(self.formatter.listitem(1) +
                    wikiutil.link_tag(request, "%s?action=edit&amp;template=%s" % (
                        wikiutil.quoteWikiname(self.page_name),
                        wikiutil.quoteWikiname(page)),
                    page) +
                    self.formatter.listitem(0))
            request.write(self.formatter.bullet_list(0))

        request.write(self.formatter.paragraph(1) +
            self.formatter.text('To create your own templates, ' 
                'add a page with a name ending with "Template," such as Business Template.') +
            self.formatter.paragraph(0))

        # list similar pages that already exist
        start, end, matches = LikePages.findMatches(self.proper_name(), request)
        if matches and not isinstance(matches, type('')):
            request.write(self.formatter.rule() + '<p>' +
                _('The following pages with similar names already exist...') + '</p>')
            LikePages.showMatches(self.proper_name(), request, start, end, matches)

    def buildCache(self):
        """
	builds the page's cache.
	"""
        # this is normally never called, but is here to fill the cache
        # in existing wikis; thus, we do a "null" send_page here, which
        # is not efficient, but reduces code duplication
        # !!! it is also an evil hack, and needs to be removed
        # !!! by refactoring Page to separate body parsing & send_page
	from Sycamore import caching
	request = self.request
	buffer = cStringIO.StringIO()
        request.redirect(buffer)
	request.generating_cache = True
        try:
            try:
                request.mode_getpagelinks = 1
                Page(self.page_name, request).send_page(content_only=1)
            except:
	        print "ERROR"
                import traceback
                traceback.print_exc()
        	cache = caching.CacheEntry(self.page_name, request)
                cache.clear()
        finally:
            request.mode_getpagelinks = 0
            request.redirect()
	    buffer.close()
            if hasattr(request, '_fmt_hd_counters'):
                del request._fmt_hd_counters

        request.generating_cache = False

    def getPageLinks(self, docache=True):
        """
        Get a list of the links on this page.
        
        @param request: the request object
	@param docache:  set to False to make this fast for macro functions, otherwise it might create the cache on a whole number of pages, redirecting the request object and causing trouble.
        @rtype: list
        @return: page names this page links to
        """
	from Sycamore import caching
	request = self.request
        if not self.exists(): return []

        key = self.page_name
        cache = caching.CacheEntry(key, request)
        if cache.needsUpdate() and docache:
            # this is normally never called, but is here to fill the cache
            # in existing wikis; thus, we do a "null" send_page here, which
            # is not efficient, but reduces code duplication
            # !!! it is also an evil hack, and needs to be removed
            # !!! by refactoring Page to separate body parsing & send_page
            request.redirect(cStringIO.StringIO())
            try:
                try:
                    request.mode_getpagelinks = 1
                    Page(self.page_name, request).send_page(content_only=1)
                except:
                    import traceback
                    traceback.print_exc()
                    cache.clear()
            finally:
                request.mode_getpagelinks = 0
                request.redirect()
                if hasattr(request, '_fmt_hd_counters'):
                    del request._fmt_hd_counters

	return caching.getPageLinks(self.page_name, request)

    def isTalkPage(self):
       pagename = self.proper_name()
       if len(pagename) >= 5:
         if pagename[len(pagename)-5:] == '/Talk':
           return True
       return False

    def getPageLinksTo(self):
	"""
	Returns a list of page names of pages that link to this page.
	"""
	links = []
        self.cursor.execute("SELECT curPages.propercased_name from links, curPages where destination_pagename=%(page_name)s and source_pagename=curPages.name", {'page_name':self.page_name})
        result = self.cursor.fetchone()
	while result:
   	  links.append(result[0])
	  result = self.cursor.fetchone()

	return links

    #def getCategories(self, request):
    #    """
    #    Get categories this page belongs to.

    #    @param request: the request object
    #    @rtype: list
    #    @return: categories this page belongs to
    #    """
    #    return wikiutil.filterCategoryPages(self.getPageLinks(request))

    # There are many places accessing ACLs even without actually sending
    # the page. This cache ensures that we don't have to parse ACLs for
    # some page twice.
    _acl_cache = {}

    def getACL(self):
        """
        Get ACLs of this page.

        @param request: the request object
        @rtype: dict
        @return: ACLs of this page
        """
        if self.request.req_cache['acls'].has_key(self.page_name): return self.request.req_cache['acls'][self.page_name]

        if not config.acl_enabled:
            import wikiacl
            return wikiacl.AccessControlList()
        # mtime check for forked long running processes
        acl = None
        if self.exists():
            mtime = self.mtime()
        else:
            mtime = 0
        if self._acl_cache.has_key(self.page_name):
            (omtime, acl) = self._acl_cache[self.page_name]
            if omtime < mtime:
                acl = None
        if acl is None:
            import wikiacl
            meta_text = ''
            if self.exists():
              meta_text = self.get_meta_text()

            acl = wikiacl.parseACL(meta_text)
            self._acl_cache[self.page_name] = (mtime, acl)

        self.request.req_cache['acls'][self.page_name] = acl
        return acl

