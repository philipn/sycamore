# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Page class

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import cStringIO, os, re, urllib, os.path, random
from LocalWiki import caching, config, user, util, wikiutil, wikidb 
import cPickle
#import LocalWiki.util.web
from LocalWiki.logfile import eventlog

class Page:
    """Page - Manage an (immutable) page associated with a WikiName.
       To change a page's content, use the PageEditor class.
    """

    _SPLIT_RE = re.compile('([%s])([%s])' % (config.lowerletters, config.upperletters))

    def __init__(self, page_name, **keywords):
        """
        Create page object.

        Note that this is a 'lean' operation, since the text for the page
        is loaded on demand. Thus, things like `Page(name).link_to()` are
        efficient.

        @param page_name: WikiName of the page
        @keyword date: date of older revision
        @keyword formatter: formatter instance
        """
        self.page_name = page_name
        self.prev_date = keywords.get('date')
	if self.prev_date: self.prev_date = float(self.prev_date)
        self._raw_body = None
        self._raw_body_modified = 0
        self.hilite_re = None
        
        if keywords.has_key('formatter'):
            self.formatter = keywords.get('formatter')
            self.default_formatter = 0
        else:
            self.default_formatter = 1

    def split_title(self, request, force=0):
        """
        Return a string with the page name split by spaces, if
        the user wants that.
        
        @param request: the request object
        @param force: if != 0, then force splitting the page_name
        @rtype: string
        @return: pagename of this page, splitted into space separated words
        """
        if not force: return self.page_name
    
        # look for the end of words and the start of a new word,
        # and insert a space there
        splitted = self._SPLIT_RE.sub(r'\1 \2', self.page_name)
        # also split at subpage separator
        return splitted.replace("/", "/ ")


    def _tmp_filename(self):
        """
        The name of the temporary file used while saving.
        
        @rtype: string
        @return: temporary filename (complete path + filename)
        """
        rnd = random.randint(0,1000000000)
        return os.path.join(config.text_dir, ('#%s.%d#' % (wikiutil.quoteFilename(self.page_name), rnd)))


    def _last_modified(self, request):
        """
        Return the last modified info.
        
        @param request: the request object
        @rtype: string
        @return: timestamp and editor information
        """
        if not self.exists():
            return None

        _ = request.getText
	db = wikidb.connect()
	cursor = db.cursor()
	cursor.execute("SELECT editTime, userEdited from curPages where name=%s", (self.page_name))
	result = cursor.fetchone()
	cursor.close()
	db.close()
	editTimeUnix = result[0]
	editTime = request.user.getFormattedDateTime(editTimeUnix)
	userEditedID = result[1]
	editUser = user.User(request, userEditedID)
	editUser_text = Page(editUser.name).link_to(request)
	
        
        result = _("(last edited %(time)s by %(editor)s)") % {
                'time': editTime,
                'editor': editUser_text,
            }

        return result


    def isWritable(self):
        """
        Can this page be changed?
        
        @rtype: bool
        @return: true, if this page is writable or does not exist
        """
	return True #for now...


    def exists(self):
        """
        Does this page exist?
        
        @rtype: bool
        @return: true, if page exists
        """
	db = wikidb.connect()
	cursor = db.cursor()
	cursor.execute("SELECT name from curPages where name=%s", (self.page_name))
	result = cursor.fetchone()
	cursor.close()
	db.close()

        return result


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
        db = wikidb.connect()
        cursor = db.cursor()
	if not self.prev_date:
          cursor.execute("SELECT editTime from curPages where name=%s", (self.page_name))
        else:
	  cursor.execute("SELECT editTime from allPages where name=%s and editTime <= %s order by editTime desc limit 1;", (self.page_name, self.prev_date))
        result = cursor.fetchone()
        cursor.close()
        db.close()	
	if result:
          if result[0]: return int(result[0])
	else: return 0

    def mtime_printable(self, request):
        """
        Get printable modification timestamp of this page.
        
        @rtype: string
        @return: formatted string with mtime of page
        """
        t = self.mtime()
        if not t:
            result = "0" # TODO: i18n, "Ever", "Beginning of time"...?
        else:
            result = request.user.getFormattedDateTime(t)
        return result
    
    def get_raw_body(self):
        """
        Load the raw markup from the page file.
        
        @rtype: string
        @return: raw page contents of this page
        """
        if self._raw_body is None:
		db = wikidb.connect()
		cursor = db.cursor()
		if not self.prev_date:
			cursor.execute("SELECT text from curPages where name=%s", (self.page_name))
			result = cursor.fetchone()
			cursor.close()
			db.close()
			if result: text = result[0]
			else: text = ''
		else:
			cursor.execute("SELECT text, editTime from allPages where (name=%s and editTime<=%s) order by editTime desc limit 1", (self.page_name, self.prev_date))
			result = cursor.fetchone()
			cursor.close()
			db.close()
			if result: text = result[0]
			else: text = ''

		#if self.prev_date:  self.prev_date = result[1]
		if not result:
			return ""
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

    def url(self, request, querystr=None):
        """
        Return an URL for this page.

        @param request: the request object
        @param querystr: the query string to add after a "?" after the url
        @rtype: string
        @return: complete url of this page (including query string if specified)
        """
        url = "%s/%s" % (request.getScriptname(), wikiutil.quoteWikiname(self.page_name))
        if querystr:
            querystr = util.web.makeQueryString(querystr)
            url = "%s?%s" % (url, querystr)
        return url


    def link_to(self, request, text=None, querystr=None, anchor=None, **kw):
        """
        Return HTML markup that links to this page.
        See wikiutil.link_tag() for possible keyword parameters.

        @param request: the request object
        @param text: inner text of the link
        @param querystr: the query string to add after a "?" after the url
        @param anchor: if specified, make a link to this anchor
        @keyword attachment_indicator: if 1, add attachment indicator after link tag
        @keyword css_class: css class to use
        @rtype: string
        @return: formatted link
        """
        text = text or self.split_title(request)
        fmt = getattr(self, 'formatter', None)

        if self.exists():
		db = wikidb.connect()
		cursor = db.cursor()
		cursor.execute("SELECT name from curPages where name=%s", (self.page_name))
		result = cursor.fetchone()
		cursor.close()
		db.close()
                url =   wikiutil.quoteWikiname(result[0])
        else:
                url = wikiutil.quoteWikiname(self.page_name)
 
        if querystr:
            querystr = util.web.makeQueryString(querystr)
            url = "%s?%s" % (url, querystr)
        if anchor: url = "%s#%s" % (url, urllib.quote_plus(anchor))

        # create a link to attachments if any exist
        attach_link = ''
        if kw.get('attachment_indicator', 0):
            from LocalWiki.action import AttachFile
            attach_link = AttachFile.getIndicator(request, self.page_name)

        
        if self.exists():
            return wikiutil.link_tag(request, url, text, formatter=fmt, **kw) + attach_link
        else:
            kw['css_class'] = 'nonexistent'
            return wikiutil.link_tag(request, url, text, formatter=fmt, **kw) + attach_link


    def send_page(self, request, msg=None, **keywords):
        """
        Output the formatted page.

        @param request: the request object
        @param msg: if given, display message in header area
        @keyword content_only: if 1, omit page header and footer
        @keyword count_hit: if 1, add an event to the log
        @keyword hilite_re: a regular expression for highlighting e.g. search results
        """
        request.clock.start('send_page')
        _ = request.getText

        # determine modes
        if request.form:
	  print_mode = request.form.has_key('action') and request.form['action'][0] == 'print'
	else: print_mode = False
        content_only = keywords.get('content_only', 0)
        content_id = keywords.get('content_id', 'content')
        self.hilite_re = keywords.get('hilite_re', None)
	self.preview = keywords.get('preview', 0)
        if msg is None: msg = ""
	polite_msg = ""

        # count hit?
        #if keywords.get('count_hit', 0):
        #     eventlog.EventLog().add(request, 'VIEWPAGE', {'pagename': self.page_name})

        # load the text
        body = self.get_raw_body()

        # if necessary, load the default formatter
        if self.default_formatter:
            from LocalWiki.formatter.text_html import Formatter
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
        while body and body[0] == '#':
            # extract first line
            try:
                line, body = body.split('\n', 1)
            except ValueError:
                line = body
                body = ''

            # end parsing on empty (invalid) PI
            if line == "#":
                body = line + '\n' + body
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
                            url = Page(target).url(request)
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
                    urllib.quote_plus(self.page_name, ''),))
                return
            elif verb == "deprecated":
                # deprecated page, append last backup version to current contents
                # (which should be a short reason why the page is deprecated)
                msg = '%s<strong>%s</strong><br>%s' % (
                    wikiutil.getSmiley('/!\\', self.formatter),
                    _('The backupped content of this page is deprecated and will not be included in search results!'),
                    msg)

                oldversions = wikiutil.getBackupList(config.backup_dir, self.page_name)
                if oldversions:
                    oldfile = oldversions[0]
                    olddate = os.path.basename(oldfile)[len(wikiutil.quoteFilename(self.page_name))+1:]
                    oldpage = Page(self.page_name, date=olddate)
                    body = body + oldpage.get_raw_body()
                    del oldfile
                    del olddate
                    del oldpage
            elif verb == "pragma":
                # store a list of name/value pairs for general use
                try:
                    key, val = args.split(' ', 1)
                except (ValueError, TypeError):
                    pass
                else:
                    request.setPragma(key, val)
            elif verb == "form":
                # ignore form PIs on non-form pages
                if not wikiutil.isFormPage(self.page_name):
                    continue

                # collect form definitions
                if not wikiform:
                    from LocalWiki import wikiform
                    pi_formtext.append('<table border="1" cellspacing="1" cellpadding="3">\n'
                        '<form method="POST" action="%s">\n'
                        '<input type="hidden" name="action" value="formtest">\n' % self.url(request))
                pi_formtext.append(wikiform.parseDefinition(request, args, pi_formfields))
            elif verb == "acl":
                # We could build it here, but there's no request.
                pass
            else:
                # unknown PI ==> end PI parsing, and show invalid PI as text
                body = line + '\n' + body
                break

        # start document output
        doc_leader = self.formatter.startDocument(self.page_name)
        if not content_only:
            # send the document leader
            request.http_headers()
            request.write(doc_leader)

            # send the page header
            if self.default_formatter:
                page_needle = self.page_name
                if config.allow_subpages and page_needle.count('/'):
                    page_needle = '/' + page_needle.split('/')[-1]
                link = '%s/%s?action=fullsearch&amp;value=%s&amp;literal=1&amp;case=1&amp;context=40' % (
                    request.getScriptname(),
                    wikiutil.quoteWikiname(self.page_name),
                    urllib.quote_plus(page_needle, ''))
                title = self.split_title(request)
                if self.prev_date:
                    msg = "<strong>%s</strong><br>%s" % (
                        _('Version as of %(date)s') % {'date':
                            request.user.getFormattedDateTime(self.prev_date)  },
                        msg)
                
                if request.form.has_key('redirect'):
                    redir = request.form['redirect'][0]
                    polite_msg = 'Redirected from ' + wikiutil.link_tag(request, wikiutil.quoteWikiname(redir) + '?action=show', redir)
                if pi_redirect:
                    msg = '%s<strong>%s</strong><br>%s' % (
                        wikiutil.getSmiley('<!>', self.formatter),
                        _('This page redirects to page "%(page)s"') % {'page': pi_redirect},
                        msg)

                
                # Page trail
                trail = None
                #if not print_mode and request.user.valid and request.user.show_page_trail:
                #    request.user.addTrail(self.page_name)
                #    trail = request.user.getTrail()

                wikiutil.send_title(request, title, link=link, msg=msg,
                    pagename=self.page_name, print_mode=print_mode, pi_refresh=pi_refresh,
                    allow_doubleclick=1, trail=trail, polite_msg=polite_msg)

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
		request.write('<table width="100%%"><tr><td align="right">[<strong class="highlight">%s</strong>]</td></tr></table>' % self.link_to(request, text="highlighting off"))
        request.write('<div id="%s" %s>\n' % (content_id, lang_attr))
        
        # new page?
        if not self.exists() and self.default_formatter and not content_only:
            self._emptyPageText(request)
        elif not request.user.may.read(self.page_name):
            request.write("<strong>%s</strong><br>" % _("You are not allowed to view this page."))
        else:
            # parse the text and send the page content
            self.send_page_content(request, Parser, body)

            # check for pending footnotes
            if getattr(request, 'footnotes', None):
                from LocalWiki.macro.FootNote import emit_footnotes
                request.write(emit_footnotes(request, self.formatter))

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

        request.clock.stop('send_page')


    def send_page_content(self, request, Parser, body, needsupdate=0):
        """
        Output the formatted wiki page, using caching, if possible.

        @param request: the request object
        @param Parser: the Parser
        @param body: text of the wiki page
        @param needsupdate: if 1, force update of the cached compiled page
        """
        formatter_name = str(self.formatter.__class__).\
                         replace('LocalWiki.formatter.', '').\
                         replace('.Formatter', '')

        # if no caching
        if  (self.prev_date or self.hilite_re or self._raw_body_modified or
            (not getattr(Parser, 'caching', None)) or
            (not formatter_name in config.caching_formats)):
            # parse the text and send the page content
            Parser(body, request).format(self.formatter)
            return

        #try cache
        _ = request.getText
        from LocalWiki import wikimacro
        arena = 'Page.py'
        key = self.page_name
        cache = caching.CacheEntry(arena, key)
        code = None

        if cache.needsUpdate():
            needsupdate = 1

        # load cache
        if not needsupdate:
            try:
		import marshal
                code = marshal.loads(cache.content())
            except ValueError: #bad marshal data
                needsupdate = 1

        # render page
        if needsupdate:
            from LocalWiki.formatter.text_python import Formatter
            formatter = Formatter(request, ["page"], self.formatter)

	    # need to do HTML parsing to get the pagelinks
	    from LocalWiki.formatter.text_html import Formatter
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
            links = html_formatter.pagelinks
            src = formatter.assemble_code(text)
            #request.write(src) # debug 
            code = compile(src, self.page_name, 'exec')
            cache.update(marshal.dumps(code), links)
            
        # send page
        formatter = self.formatter
        parser = Parser(body, request)
        macro_obj = wikimacro.Macro(parser)

        try:
            exec code
        except 'CacheNeedsUpdate': # if something goes wrong, try without caching
           self.send_page_content(request, Parser, body, needsupdate=1)
           cache = caching.CacheEntry(arena, key)
            
        refresh = wikiutil.link_tag(request,
            wikiutil.quoteWikiname(self.page_name) +
            "?action=refresh&amp;arena=%s&amp;key=%s" % (arena, key),
            _("RefreshCache")
        ) + ' %s<br>' % _('for this page (cached %(date)s)') % {
                'date': self.formatter.request.user.getFormattedDateTime(cache.mtime())
        }
        self.formatter.request.add2footer('RefreshCache', refresh)


    def _emptyPageText(self, request):
        """
        Output the default page content for new pages.
        
        @param request: the request object
        """
        from LocalWiki.action import LikePages
        _ = request.getText
  
        request.write(self.formatter.paragraph(1))
        request.write(wikiutil.link_tag(request,
            wikiutil.quoteWikiname(self.page_name)+'?action=edit',
            _("Create this page")))
        request.write(self.formatter.paragraph(0))
  
        # look for template pages
        templates = filter(lambda page, u = wikiutil: u.isTemplatePage(page),
            wikiutil.getPageList())
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
        start, end, matches = LikePages.findMatches(self.page_name, request)
        if matches and not isinstance(matches, type('')):
            request.write(self.formatter.rule() + '<p>' +
                _('The following pages with similar names already exist...') + '</p>')
            LikePages.showMatches(self.page_name, request, start, end, matches)


    def getPageLinks(self, request, docache=True):
        """
        Get a list of the links on this page.
        
        @param request: the request object
	@param docache:  set to False to make this fast for macro functions, otherwise it might create the cache on a whole number of pages, redirecting the request object and causing trouble
        @rtype: list
        @return: page names this page links to
        """
        if not self.exists(): return []

        arena = "Page.py"
        key   = self.page_name
        cache = caching.CacheEntry(arena, key)
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
                    Page(self.page_name).send_page(request, content_only=1)
                except:
                    import traceback
                    traceback.print_exc()
                    cache.clear()
            finally:
                request.mode_getpagelinks = 0
                request.redirect()
                if hasattr(request, '_fmt_hd_counters'):
                    del request._fmt_hd_counters
        # XXX UNICODE fix needed? decode from utf-8

	# !!!! DB FIX DBFIX need to use LINK TABLE here
	links = []
	db = wikidb.connect()
        cursor = db.cursor()
        cursor.execute("SELECT destination_pagename from links where source_pagename=%s", (self.page_name))
        result = cursor.fetchone()
	while result:
   	  links.append(result[0])
	  result = cursor.fetchone()
        cursor.close()
        db.close()
	
	return links

    def getPageLinksTo(self, request):
	"""
	Returns a list of page names of pages that link to this page.
	"""
	links = []
	db = wikidb.connect()
        cursor = db.cursor()
        cursor.execute("SELECT source_pagename from links where destination_pagename=%s", (self.page_name))
        result = cursor.fetchone()
	while result:
   	  links.append(result[0])
	  result = cursor.fetchone()
        cursor.close()
        db.close()

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
            body = ''
            if self.exists():
                body = self.get_raw_body()

            acl = wikiacl.parseACL(body)
            self._acl_cache[self.page_name] = (mtime, acl)
        return acl
