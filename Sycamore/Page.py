# -*- coding: utf-8 -*-
"""
    Sycamore - Page class and associated methods

    @copyright: 2005-2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import cStringIO
import os
import re
import urllib
import random
import cPickle
from copy import copy

from Sycamore import config
from Sycamore import user
from Sycamore import util
from Sycamore import wikiutil
from Sycamore import wikidb 

MAX_PAGENAME_LENGTH = 106
DISPLAYED_MAX_PAGENAME_LENGTH = MAX_PAGENAME_LENGTH - len("Talk")

class Page(object):
    """
        Page - Manage an (immutable) page associated with a page name
            (and wiki name).
       To change a page's content, use the PageEditor class.
    """
    class ExcessiveLength(Exception):
        pass
    class InvalidPageName(Exception):
        pass

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
        @keyword wiki_name: name of a wiki to switch to for this page
            (wiki farms only)
        """
        from wikiaction import isValidPageName
        if type(page_name) == str:
            page_name = page_name.decode(config.charset)

        if len(page_name) > MAX_PAGENAME_LENGTH:
            msg = "Page names must be less than %s characters!" % (
                DISPLAYED_MAX_PAGENAME_LENGTH)
            raise self.ExcessiveLength, msg
        if not isValidPageName(page_name):
            raise self.InvalidPageName, page_name
        self.on_wiki_name = request.config.wiki_name  # wiki _we are_ on
        wiki_name = keywords.get('wiki_name')
        if wiki_name and request.config.wiki_name != wiki_name:
            request = _copy_wiki_request(wiki_name, request)
        if not wiki_name:
            wiki_name = request.config.wiki_name
        self.wiki_name = wiki_name
        self.wiki_id = request.config.wiki_id

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
            self.formatter.request = self.request
        else:
            self.default_formatter = 1

    def get_date(self):
        # returns date this page/version was created
        if self.version and not self.date:
          self.date = self.version_number_to_date(self.version)
          return self.date
        elif not self.date:
          self.date = self.last_edit_info()[0]
        return self.date

    def get_version(self):
        # returns date this page/version was created
        if self.date and not self.version:
          self.version = self.date_to_version_number(self.date)
          return self.version
        elif not self.version:
          self.date = self.last_edit_info()[0]
          self.version = self.date_to_version_number(self.date)
        return self.version

    def version_number_to_date(self, version_number):
        """
        Returns the unix timestamp of the editTime of this version of the page.
        """
        if self.request.req_cache['pageVersionDate'].has_key((self.page_name,
           version_number, self.request.config.wiki_id)):
            return self.request.req_cache['pageVersionDate'][(self.page_name,
              version_number, self.request.config.wiki_id)]

        self.cursor.execute("""SELECT editTime from allPages
            where name=%(page_name)s and wiki_id=%(wiki_id)s
            order by editTime asc limit 1 offset %(version)s""",
            {'page_name':self.page_name, 'version':version_number-1,
             'wiki_id': self.request.config.wiki_id})
        result = self.cursor.fetchone()
        self.request.req_cache['pageVersionDate'][(self.page_name,
          version_number, self.request.config.wiki_id)] = result[0]
        return result[0]

    def date_to_version_number(self, date):
        """
        Returns the version number of a given date of this page.
        """
        if self.request.req_cache['pageDateVersion'].has_key((self.page_name,
           date, self.request.config.wiki_id)):
            return self.request.req_cache['pageDateVersion'][(self.page_name,
              date, self.request.config.wiki_id)]

        self.cursor.execute("""SELECT count(editTime) from allPages
            where name=%(page_name)s and editTime<=%(date)s and
                  wiki_id=%(wiki_id)s""",
            {'page_name':self.page_name, 'date':date,
             'wiki_id': self.request.config.wiki_id})

        result = self.cursor.fetchone()
        self.request.req_cache['pageDateVersion'][(self.page_name,
            date, self.request.config.wiki_id)] = result[0]
        return result[0]

    def edit_info(self):
        """
        Returns returns user edited and mtime for the page's version.
        """
        edit_info = None

        if not self.request.generating_cache:
            # get page info from cache or database
            from Sycamore import caching
            return caching.pageInfo(self).edit_info
        else:
            # We're generating the cache, so let's
            # just get the edit info manually from the DB
            if not self.prev_date:
                self.request.cursor.execute("""SELECT editTime, userEdited
                    from curPages where name=%(pagename)s and
                                        wiki_id=%(wiki_id)s""",
                    {'pagename':self.page_name,
                     'wiki_id':self.request.config.wiki_id})
            else:
                self.request.cursor.execute("""SELECT editTime, userEdited
                    from allPages where name=%(pagename)s and
                                        wiki_id=%(wiki_id)s and
                                        editTime=%(prev_date)s""",
                    {'pagename':self.page_name,
                     'prev_date':self.prev_date,
                     'wiki_id':self.request.config.wiki_id})
            result = self.request.cursor.fetchone()
            if result:
                return (result[0], result[1].strip())

        return None
      
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

        last_edit_info = self.last_edit_info()
        result = None
        if last_edit_info:
            editTimeUnix, userEditedID = last_edit_info
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
        if proper_name_exists:
            return proper_name_exists
        else:
            return self.given_name

    def make_exact_prev_date(self):
        """
        Some functions, such as diff, like to use an inexact previous date.
        We convert this to a real previous date of a page, or return False.
        """
        if self.prev_date:
            self.request.cursor.execute("""SELECT editTime from allPages
               where name=%(pagename)s and editTime<=%(date)s and
                     wiki_id=%(wiki_id)s
               order by editTime desc limit 1""",
               {'date':self.prev_date, 'pagename':self.page_name,
                'wiki_id':self.request.config.wiki_id})
            result = self.request.cursor.fetchone()
            if not result:
                return False
            self.prev_date = result[0]
            return self.prev_date

    def exists(self, fresh=False):
        """
        Does this page exist?
        
        @rtype: bool or string
        @return: False, if page doesn't exist.
                 Otherwise returns proper pagename
        """
        proper_pagename = False
        memcache_hit = False
        if not fresh:
            if self.request.req_cache['pagenames'].has_key((self.page_name,
                    self.wiki_name)):
                return self.request.req_cache['pagenames'][(self.page_name,
                    self.wiki_name)]
            if config.memcache:
                proper_pagename = self.request.mc.get("pagename:%s" % 
                    (wikiutil.mc_quote(self.page_name)))
                if proper_pagename is not None:
                    memcache_hit = True
                else:
                    proper_pagename = False

        if not proper_pagename and not memcache_hit:
            self.cursor.execute("""SELECT propercased_name from curPages
                where name=%(pagename)s and wiki_id=%(wiki_id)s""",
                {'pagename': self.page_name,
                 'wiki_id': self.request.config.wiki_id})
            result = self.cursor.fetchone()
            if result:
                proper_pagename = result[0]
            if config.memcache:
                self.request.mc.add("pagename:%s" % 
                    (wikiutil.mc_quote(self.page_name)), proper_pagename)

        self.request.req_cache['pagenames'][(self.page_name,
            self.wiki_name)] = proper_pagename
        return proper_pagename

    def size(self):
        """
        Get Page size (number of characters).
        
        @rtype: int
        @return: page size, 0 for non-existent pages.
        """
        if not self._raw_body:
            body = self.get_raw_body()
        else:
            body = self._raw_body

        if body is not None:
            # TODO: len(body) only after converting to a byte string
            return len(body)
        return ''

    def isRedirect(self):
        """
        If the page is a redirect this returns True.  If not it returns False.
        """
        body = self.get_meta_text()
        if body[0:9] == '#redirect':
            return True
        return False

    def hasMapPoints(self):
        from Sycamore import caching
        if not self.prev_date:
            return caching.pageInfo(self).has_map
        else: 
            return caching.pageInfo(Page(self.page_name,
                self.request)).has_map

    def human_size(self):
        """
        Human-readable (in 'words') size of the page.
        """
        if not self._raw_body:
            body = self.get_raw_body()
        else:
            body = self._raw_body
        if body is not None:
            return len(body.split())
        return 0

    def mtime(self):
        """
        Get modification timestamp of this page.
        
        @rtype: int
        @return: mtime of page (or 0 if page does not exist)
        """
        info = self.edit_info()
        if info and info[0]:
           return info[0]
        return 0

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
        if not t:
            t = self.mtime()
            result = "0" # TODO: i18n, "Ever", "Beginning of time"...?
        else:
            result = self.request.user.getFormattedDateTime(t)
        return result

    def get_meta_text(self):
        """
        Returns the meta text of a page.
        This includes things that start with # at the beginning of page's
        text.
        """
        if self.exists():
            from Sycamore import caching
            if not self.request.generating_cache:
                return caching.pageInfo(self).meta_text
            else:
                # we are generating the cache so we need to get this directly
                return caching.find_meta_text(self)
            
        return ''
    
    def get_raw_body(self, fresh=False):
        """
        Load the raw markup from the page file.
        
        @optional param fresh: determines if we should get the cached raw body
         or not.
        @rtype: string.
        @return: raw page contents of this page.
        """
        text = None
        if self._raw_body is None:
            if not self.prev_date:
                if config.memcache and not fresh:
                    text = self.request.mc.get("page_text:%s" % 
                        (wikiutil.mc_quote(self.page_name.lower())))

                if text is None:
                    self.cursor.execute("""SELECT text from curPages
                        where name=%(page_name)s and wiki_id=%(wiki_id)s""",
                        {'page_name':self.page_name,
                         'wiki_id':self.request.config.wiki_id})
                    result = self.cursor.fetchone()
                    if result:
                        text = result[0]
                    else:
                        text = ''
                    if config.memcache and not fresh:
                        self.request.mc.add("page_text:%s" % 
                            (wikiutil.mc_quote(self.page_name.lower())), text)
            else:
                if config.memcache and not fresh:
                    text = self.request.mc.get("page_text:%s,%s" % 
                        (wikiutil.mc_quote(self.page_name.lower()),
                         repr(self.prev_date)))
                if text is None:
                    self.cursor.execute("""SELECT text, editTime from allPages
                        where name=%(page_name)s and
                              editTime<=%(prev_date)s and wiki_id=%(wiki_id)s
                        order by editTime desc limit 1""",
                        {'page_name':self.page_name,
                         'prev_date':self.prev_date,
                         'wiki_id':self.request.config.wiki_id})
                    result = self.cursor.fetchone()
                    if result:
                        text = result[0]
                    else:
                        text = ''
                    if config.memcache and not fresh:
                        self.request.mc.add("page_text:%s,%s" % 
                            (wikiutil.mc_quote(self.page_name.lower()),
                             repr(self.prev_date)),
                            text)
              
            if text is None:
                text = ''
            self.set_raw_body(text)

        return self._raw_body

    def set_raw_body(self, body, modified=0, set_cache=False):
        """
        Set the raw body text (prevents loading from disk).

        @param body: raw body text
        @param modified: 1 means that we internally modified the raw text and
                         that it is not in sync with the page file on disk.
                         This is used e.g. by PageEditor when previewing the
                         page.
        """
        self._raw_body = body
        self._raw_body_modified = modified
        if not modified and config.memcache:
            if set_cache or self.request.set_cache:
                if not self.prev_date:
                    self.request.mc.set('page_text:%s' % 
                      (wikiutil.mc_quote(self.page_name.lower())),
                      body)
                else:
                    self.request.mc.set('page_text:%s,%s' % 
                        (wikiutil.mc_quote(self.page_name.lower()),
                         repr(self.prev_date)),
                        body)

    def url(self, querystr=None, relative=True):
        """
        Return an URL for this page.

        @param request: the request object
        @param querystr: the query string to add after a "?" after the url
        @rtype: string
        @return: complete url of this page
                 (including query string if specified)
        """
        from Sycamore import farm
        url = "%s/%s" % (self.request.getScriptname(),
                         wikiutil.quoteWikiname(self.proper_name()))

        if not relative:
            base_url = farm.getWikiURL(self.request.config.wiki_name,
                                       self.request)
            url = '%s%s' % (base_url, url[1:])

        if querystr:
            querystr = util.web.makeQueryString(querystr)
            url = "%s?%s" % (url, querystr)

        return url

    def link_to(self, text=None, querystr=None, anchor=None,
                know_status=False, know_status_exists=False, guess_case=False,
                **kw):
        """
        Return HTML markup that links to this page.
        See wikiutil.link_tag() for possible keyword parameters.

        @param request: the request object
        @param text: inner text of the link
        @param querystr: the query string to add after a "?" after the url
        @param anchor: if specified, make a link to this anchor
        @keyword attachment_indicator: if 1, add attachment indicator after
                                       link tag
        @keyword css_class: css class to use
        @keyword know_status: for slight optimization.  If True that means
                              we know whether the page exists or not
                              (saves an often-used query)
          @ keyword know_status_exists: if True that means the page exists,
                                        if False that means it doesn't
        @keyword show_title: if False, don't show title attribute (below).
        @keyword title: html title to use.  If not given then we default
                        to the page name.
        @rtype: string
        @return: formatted link
        """
        url_name = ''
        request = self.request
        if know_status_exists and know_status:
            know_exists = True
        else:
            know_exists = False
        text = text
        fmt = getattr(self, 'formatter', None)
        if not know_status:
            if self.exists():
                know_exists = True
                url_name = self.proper_name()
            else:
                # did we give Page(a name of a page here..) ?
                if self.given_name and not guess_case:
                    url_name = self.given_name
                elif guess_case:
                    self.request.cursor.execute("""SELECT propercased_name
                        from allPages where
                        name=%(name)s and editTime=%(latest_mtime)s and
                        wiki_id=%(wiki_id)s""",
                        {'name':self.page_name, 'latest_mtime':self.mtime(),
                         'wiki_id':self.request.config.wiki_id})
                    result = self.request.cursor.fetchone()
                    if result:
                        url_name = result[0]
                    else:
                        url_name = self.given_name
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
        if anchor:
            url = "%s#%s" % (url, urllib.quote_plus(anchor))

        # create a link to attachments if any exist
        attach_link = ''
        if kw.get('attachment_indicator', 0):
            from Sycamore.action import AttachFile
            attach_link = AttachFile.getIndicator(request, self.page_name)

        if self.wiki_name != self.on_wiki_name:
            kw['absolute'] = True

        if kw.get('show_title', True):
            title = kw.get('title')
            if not title:
                title = url_name
            kw['attrs'] = 'title="%s"' % title
        if know_exists:
            return '%s%s' % (wikiutil.link_tag(request, url,
                                               text, formatter=fmt, **kw),
                             attach_link)
        else:
            kw['css_class'] = 'nonexistent'
            return '%s%s' % (wikiutil.link_tag(request, url,
                                               text, formatter=fmt, **kw),
                             attach_link)
        
    def send_page(self, msg=None, **keywords):
        """
        Output the formatted page.

        @param request: the request object
        @param msg: if given, display message in header area
        @keyword content_only: if 1, omit page header and footer
        @keyword count_hit: if 1, add an event to the log
        @keyword hilite_re: a regular expression for highlighting
                            e.g. search results
        @keyword force_regenerate_content: if true, re-parse the page content
        """
        from Sycamore import farm
        request = self.request
        _ = request.getText

        # determine modes
        if request.form:
            print_mode = (request.form.has_key('action') and
                          request.form['action'][0] == 'print')
        else:
            print_mode = False
        content_only = keywords.get('content_only', 0)
        content_id = keywords.get('content_id', 'content')
        self.hilite_re = keywords.get('hilite_re', None)
        self.preview = keywords.get('preview', 0)
        if self.preview:
            self.request.previewing_page = True
        if msg is None:
            msg = ""
        polite_msg = ""

        # load the meta-text
        meta_text = self.get_meta_text()

        # if necessary, load the default formatter
        if self.default_formatter:
            from Sycamore.formatter.text_html import Formatter
            self.formatter = Formatter(request, store_pagelinks=1,
                                       preview=self.preview)
        self.formatter.setPage(self)
        request.formatter = self.formatter

        # default is wiki markup
        pi_format = config.default_markup or "wiki"
        pi_redirect = None
        pi_refresh = None
        pi_formtext = []
        pi_formfields = []

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
            if line[1] == '#':
                continue

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
                wikitag_bad = True
                if args.startswith('wiki:'):
                    # grab the url that points to this page on this wiki.
                    # cuts out 'wiki:' and removes "quotes" from wiki url
                    possible_wiki_url = wikiutil.format_interwiki_words(
                        args.split(), in_farm=True)[0][5:]
                    wikitag, wikiurl, wikitail, wikitag_bad, wikitype = \
                        wikiutil.resolve_wiki(request, possible_wiki_url)
                if wikitag_bad:
                    pi_redirect = args

                    if self.request.user.valid:
                        self.request.user.checkFavorites(self)

                    if (request.form.has_key('action') or
                        request.form.has_key('redirect') or content_only):
                        continue
                    request.http_redirect('%s/%s?action=show&redirect=%s' % (
                        request.getScriptname(),
                        wikiutil.quoteWikiname(pi_redirect),
                        urllib.quote_plus(self.proper_name().encode(
                            config.charset),
                                          ''),))
                else:
                    pi_redirect = args
                    # we are redirecting to a different wiki.
                    wikiurl = wikiutil.mapURL(wikiurl)
                    if wikitype == wikiutil.INTERWIKI_FARM_TYPE:
                        # it only makes sense to do redirection within the farm
                        # (at least for now)
                        if Page(wikitail, request, wiki_name=wikitag).exists():
                            # only want to quote if page name is sane..
                            wikitail = wikiutil.quoteWikiname(wikitail)
                        redirect_url = wikiutil.join_wiki(wikiurl, wikitail)
                        if (request.form.has_key('action') or
                            request.form.has_key('redirect') or content_only):
                            continue
                        request.http_redirect('%s?action=show&redirect=%s&wiki=%s' % (
                            redirect_url,
                            urllib.quote_plus(self.proper_name().encode(
                                config.charset),
                                             ''),
                            self.request.config.wiki_name))
                        return
            else:
                # unknown PI ==> end PI parsing, and show invalid PI as text
                meta_text = line + '\n' + meta_text
                break

        # start document output
        doc_leader = self.formatter.startDocument(self.page_name)
        if not content_only:
            if self.request.user.valid:
                self.request.user.checkFavorites(self)

            # send the document leader
            if not self.exists() and not request.status:
                request.status = '404 Not Found'
            request.http_headers()
            request.write(doc_leader)

            # send the page header
            proper_name = self.proper_name()
            if self.default_formatter:
                page_needle = self.page_name
                if (self.request.config.allow_subpages and
                    page_needle.count('/')):
                    page_needle = '/' + page_needle.split('/')[-1]
                has_link = True

                title = proper_name
                if self.prev_date and not msg:
                    msg = "<strong>%s</strong>" % (
                        _('Version %(version)s (%(date)s)') % {
                            'version': self.get_version(),
                            'date': request.user.getFormattedDateTime(
                                self.prev_date) },
                        )
                
                if request.form.has_key('redirect'):
                    redir = request.form['redirect'][0]
                    if not request.form.has_key('wiki'):
                        # local redirect
                        polite_msg = 'Redirected from %s' % (
                            wikiutil.link_tag(request,
                                              wikiutil.quoteWikiname(redir) +
                                                '?action=show',
                                              redir))
                    else:
                        # interwiki redirect
                        wiki_name = request.form['wiki'][0]
                        redir_page = Page(redir, request, wiki_name=wiki_name)
                        redir_from = redir_page.link_to(know_status=True,
                            know_status_exists=True, querystr="action=show")
                        # we don't use farm.link_to_page() here b/c we always
                        # want to link in-farm rather than risk linking
                        # out-farm, because that won't make any sense in this
                        # context. (wikis can over-ride wiki:namehere to go,
                        # instead, out-farm)
                        # their front page can be called something else
                        orig_wiki = request.config.wiki_name
                        request.switch_wiki(wiki_name)
                        front_page = request.config.page_front_page
                        request.switch_wiki(orig_wiki)

                        on_wiki = farm.link_to_page(wiki_name,
                            front_page, self.formatter, force_farm=True,
                            text=wiki_name)
                        polite_msg = 'Redirected from %s on %s' % (
                            redir_from, on_wiki)
                if pi_redirect and not msg:
                    if wikitag_bad:
                        # internal redirect
                        page_link = Page(pi_redirect, request).link_to()
                        msg = '<strong>%s</strong><br>' % (
                            _('This page redirects to page %(page)s') % {
                                'page': page_link})
                    elif wikitype == wikiutil.INTERWIKI_FARM_TYPE:
                        # redirect to wiki in farm
                        page_link = farm.link_to_page(wikitag,
                            wikiutil.unquoteWikiname(wikitail),
                            self.formatter, no_icon=False)
                        msg = '<strong>%s</strong><br>' % (
                            _('This page redirects to page %(page)s') % {
                                'page': page_link})

                position_screen = ''
                if (self.request.form.has_key('screenposy') and
                    self.request.form['screenposy'][0]):
                    try:
                        screen_pos_y = int(self.request.form['screenposy'][0])
                        position_screen = 'window.scrollTo(0, %s);' % (
                            screen_pos_y)
                    except:
                        pass # we just won't set screen position

                if self.request.user.may.edit(self):
                    onload = "setTimeout('createClickProperties(1)', 100);createEditSubmit();%s" % position_screen
                else:
                    onload = ''

                wikiutil.send_title(request, title, has_link=has_link,
                    msg=msg, body_onload=onload, page=self,
                    pagename=proper_name, print_mode=print_mode,
                    pi_refresh=pi_refresh, allow_doubleclick=1,
                    polite_msg=polite_msg)

                # user-defined form preview?
                # Todo: check if this is also an RTL form
                # then add ui_lang_attr
                if pi_formtext:
                    pi_formtext.append('<input type="hidden" name="fieldlist"'
                                       ' value="%s">\n' %
                                       "|".join(pi_formfields))
                    pi_formtext.append('</form></table>\n')
                    pi_formtext.append(_(
                        '<p><small>If you submit this form, the submitted '
                        'values will be displayed.\n'
                        'To use this form on other pages, insert a\n'
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
                request.write("""<table width="100%%"><tr>
                <td align="right">[<strong class="highlight">%s</strong>]</td>
                </tr></table>""" % self.link_to(text="highlighting off"))

        # new page or a deleted page?
        if not self.exists() and not content_only and not self.prev_date:
            request.write('<div class="%s wikipage" %s>\n' % (
                content_id, lang_attr))
            self._emptyPageText()
        elif (self.request.sent_page_content and not
              keywords.get('force_regenerate_content')):
            self.request.write(self.request.sent_page_content)
        else:
            if not self.preview:
              request.write('<div id="%s" class="%s wikipage" %s>\n' % (
                content_id, content_id, lang_attr))
            else:
              request.write('<div class="%s wikipage" %s>\n' % (
                content_id, lang_attr))
            
            if not request.user.may.read(self):
                request.write("<strong>%s</strong><br>" % _(
                    "You are not allowed to view this page."))
            else:
                # parse the text and send the page content
                self.send_page_content(Parser,
                    needsupdate=keywords.get('force_regenerate_content'))

        # end wiki content div
        request.write('<div style="clear: both;"></div></div>\n')
        
        # end document output
        doc_trailer = self.formatter.endDocument()
        if not content_only:
            # send the page footer
            if self.default_formatter and not print_mode:
                wikiutil.send_after_content(request)
                wikiutil.send_footer(request, self.page_name,
                                     print_mode=print_mode)

            request.write(doc_trailer)

    def send_page_content(self, Parser, needsupdate=0):
        """
        Output the formatted wiki page, using caching, if possible.

        @param Parser: the Parser
        @param body: text of the wiki page
        @param needsupdate: if 1, force update of the cached compiled page
        """
        
        body = ''
        request = self.request
        formatter_name = str(self.formatter.__class__).\
                         replace('Sycamore.formatter.', '').\
                         replace('.Formatter', '')

        self.formatter.setPage(self)
        # if no caching
        if  (self.prev_date or self.hilite_re or self._raw_body_modified or
            (not getattr(Parser, 'caching', None)) or
            (not formatter_name in config.caching_formats) or
            self.preview): 
            # parse the text and send the page content
            body = self.get_raw_body()
            Parser(body, request).format(self.formatter)
            return

        elif self.request.generating_cache and not request.set_cache:
            body = self.get_raw_body(fresh=True)
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
                needsupdate = 1
            except EOFError: #bad marshal data
                needsupdate = 1

        # render page
        if needsupdate:
            request.set_cache = True
            body = self.get_raw_body(fresh=True)

            from Sycamore.formatter.text_python import Formatter
            formatter = Formatter(request, ["page"],
                                  self.formatter, preview=True,
                                  store_pagelinks=1)
            formatter.setPage(self)

            # clear the page's dependencies
            caching.clear_dependencies(self.page_name, request)

            # need to do HTML parsing to get the pagelinks
            from Sycamore.formatter.text_html import Formatter as HTMLFormatter
            html_formatter = HTMLFormatter(request, store_pagelinks=1)
            html_formatter.setPage(self)
            buffer = cStringIO.StringIO()
            request.redirect(buffer)
            html_parser = Parser(body, request)
            html_parser.format(html_formatter)
            request.redirect()
            
            import marshal
            formatter.setPage(self)
            buffer = cStringIO.StringIO()
            request.redirect(buffer)
            parser = Parser(body, request)
            parser.format(formatter)
            request.redirect()
            text = buffer.getvalue()
            buffer.close()
            links = html_formatter.pagelinks_propercased
            src = formatter.assemble_code(text)
            #print src # debug 
            code = compile(src, self.page_name.encode(config.charset), 'exec')
            code_string = marshal.dumps(code)
            cache.update(code_string, links)
            update_links = True
            request.set_cache = True
        else:
           parser = Parser(body, request)
           update_links = False
            
        # send page
        formatter = self.formatter
        macro_obj = wikimacro.Macro(parser)
        try:
            # figure out the link status' all at once to improve
            # performance on pages w/lots of links
            caching.getPageLinks(self.page_name, self.request,
                                 update=update_links)
            # execute the python code we serialized,
            # this prints the page content and macros/etc
            exec code
        # if something goes wrong, try without caching
        except 'CacheNeedsUpdate':
            body = self.get_raw_body()
            self.send_page_content(Parser, body, needsupdate=1)
            cache = caching.CacheEntry(key, request)

    def _emptyUserPageText(self):
        """
        Output the default page content for new user pages.
        
        @param request: the request object
        """
        from Sycamore import farm
        request = self.request
        _ = request.getText
        username = self.proper_name()[len(config.user_page_prefix):]

        request.write(self.formatter.paragraph(1))
        create_page_link = wikiutil.link_tag(request,
            wikiutil.quoteWikiname(self.proper_name())+'?action=edit',
            _("please create one!"))
        request.write("%s doesn't have a page yet &mdash; %s" %
                      (username, create_page_link))
        request.write(self.formatter.paragraph(0))

        the_user = user.User(request, name=username)
        page_name = config.user_page_prefix + the_user.propercased_name
        user_pages = the_user.getUserPages()
        if user_pages:
            request.write(self.formatter.heading(
                3, "%s has profiles on these wikis:" % username))
            request.write(self.formatter.bullet_list(1))
            for wiki_name in user_pages:
                request.write(self.formatter.listitem(1))
                link = farm.link_to_page(wiki_name, page_name, self.formatter,
                                         no_icon=False, text=wiki_name)
                request.write(link)
                request.write(self.formatter.listitem(0))
            request.write(self.formatter.bullet_list(0))

        user_info_link = self.link_to(know_status=True,
                                      know_status_exists=True,
                                      querystr="action=userinfo",
                                      text="%s's user info" %
                                           the_user.propercased_name)
        request.write("You might be interested in %s, too." % user_info_link)
            
    def _emptyPageText(self):
        """
        Output the default page content for new pages.
        
        @param request: the request object
        """
        request = self.request
        _ = request.getText
  
        is_user_page = (self.page_name.startswith(
            config.user_page_prefix.lower()) and
            user.User(self.request,
                      name=self.page_name[
                        len(config.user_page_prefix):]
                     ).exists())

        if is_user_page:
            self._emptyUserPageText() 
            return

        request.write(self.formatter.paragraph(1))
        request.write(wikiutil.link_tag(request,
            wikiutil.quoteWikiname(self.proper_name())+'?action=edit',
            _("Create this page")))
        request.write(self.formatter.paragraph(0))
  
        templates = wikiutil.getTemplatePages(request)

        if templates:
            templates.sort()

            request.write(self.formatter.paragraph(1) +
                self.formatter.text(_('Or use one of these templates:')) +
                self.formatter.paragraph(0))

            # send list of template pages
            request.write(self.formatter.bullet_list(1))
            for page in templates:
                pagename = page[len('Templates/'):]
                request.write(self.formatter.listitem(1) +
                    wikiutil.link_tag(request,
                        "%s?action=edit&amp;template=%s" % (
                            wikiutil.quoteWikiname(self.proper_name()),
                            wikiutil.quoteWikiname(page)),
                        "Create as " + pagename) +
                        self.formatter.listitem(0))
            request.write(self.formatter.bullet_list(0))

        template_msg = ('To create your own %s, add a page with a name '
                        'starting with Templates/, such as '
                        'Templates/Business.') % (
                            Page('Templates', self.request).link_to(
                                text="templates"))
        request.write(self.formatter.paragraph(1) + template_msg + 
            self.formatter.paragraph(0))

        search_string = ('<a href="%s?action=search&string=%s">'
                         'do a search for %s</a>') % (
                            request.getScriptname(),
                            urllib.quote_plus(
                                self.proper_name().encode(config.charset)),
                            self.proper_name())
        request.write(self.formatter.rule() + 
                      "<p>It's a good idea to %s on the wiki to see what "
                      "else is out there.</p>" %
                        search_string)

    def buildCache(self, type=None):
        """
        Builds the page's cache.
        """
        # We do a "null" send_page here, which
        # is not efficient, but reduces code duplication
        # !!! it is also an evil hack, and needs to be removed
        # !!! by refactoring Page to separate body parsing & send_page
        from Sycamore import caching, wikidicts
        request = self.request
        buffer = cStringIO.StringIO()
        request.redirect(buffer)
        request.generating_cache = True
        request.set_cache = True
        request.mode_getpagelinks = 1

        # set the page name / page exists
        self.request.req_cache['pagenames'][(self.page_name,
            self.wiki_name)] = self.proper_name()

        try:
            # set trigger for clearing possible dependencies (e.g. [[Include]])
            # we want this to be a post-commit trigger so that
            # we don't have stale data
            for pagename in caching.depend_on_me(self.page_name,
                                                 request, self.exists()):
                request.postCommitActions.append(
                    (caching.CacheEntry(pagename, request).clear, ))
            try:
                request.mode_getpagelinks = 1
                page = Page(self.page_name, request)
                page.set_raw_body(self.get_raw_body(fresh=True))
                page.send_page(content_only=1, force_regenerate_content=True)
            except:
                #print "ERROR"
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

        if config.memcache:
            key = wikiutil.mc_quote(self.page_name.lower())
            #clears the content of the cache regardless of whether or not
            # the page needs an update
            self.request.mc.delete("links:%s" % key)
            if type == 'page save new':
                self.request.mc.set("pagename:%s" % key, self.proper_name())
                if wikiutil.isTemplatePage(self.proper_name()):
                    # dirty the cache
                    self.request.mc.set("templates", None)
            elif type == 'page save delete':
                 self.request.mc.set("pagename:%s" % key, False)
                 if wikiutil.isTemplatePage(self.proper_name()):
                    # dirty the cache
                    self.request.mc.set("templates", None)
            else:
                if self.exists():
                    self.request.mc.set("pagename:%s" % key,
                                        self.proper_name())

            if self.page_name.lower() == \
                self.request.config.interwikimap.lower():
                self.request.req_cache['interwiki'][
                    self.request.config.wiki_id] = wikidicts.Dict(
                        self.page_name, self.request,
                        case_insensitive=True, fresh=True)
                self.request.mc.set('interwiki',
                    self.request.req_cache['interwiki'][
                        self.request.config.wiki_id])

        request.mode_getpagelinks = 0
        request.generating_cache = False
        request.set_cache = False

    def getPageLinks(self, docache=True):
        """
        Get a list of the links on this page.
        
        @param request: the request object
        @param docache:  set to False to make this fast for macro functions,
                         otherwise it might create the cache on a whole number
                         of pages, redirecting the request object and causing
                         trouble.
        @rtype: list
        @return: page names this page links to
        """
        from Sycamore import caching
        request = self.request
        if not self.exists():
            return []

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
       return ( len(pagename) >= 5 and pagename[len(pagename)-5:] == '/Talk' )

    def getPageLinksTo(self):
        """
        Returns a list of page names of pages that link to this page.
        """
        links = []
        self.cursor.execute("""SELECT curPages.propercased_name
            from links, curPages
            where destination_pagename=%(page_name)s and
                  source_pagename=curPages.name and
                  curPages.wiki_id=%(wiki_id)s and
                  links.wiki_id=%(wiki_id)s
            group by propercased_name""",
            {'page_name':self.page_name,
             'wiki_id':self.request.config.wiki_id})
        result = self.cursor.fetchone()
        while result:
            links.append(result[0])
            result = self.cursor.fetchone()

        return links

    def getACL(self, **kw):
        """
        Get ACLs of this page.

        @param request: the request object
        @rtype: dict
        @return: ACLs of this page
        """
        import wikiacl
        acl = wikiacl.getACL(self.page_name, self.request, **kw)

        return acl

def _copy_wiki_request(wiki_name, request):
        """
        Returns a copy of request, except with
        request.config = Config(wiki_name, request)
        Hackish because we don't want to copy certain things.
        """
        from Sycamore.request import postCommitMC
        req_copy = copy(request)
        if config.memcache:
            req_copy._mc = copy(request._mc)
            req_copy.mc = postCommitMC(req_copy)
        req_copy.switch_wiki(wiki_name)
        req_copy.req_cache = request.req_cache
        return req_copy
