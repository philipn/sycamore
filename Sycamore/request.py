# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Data associated with a single Request

    @copyright: 2001-2003 by Jürgen Hermann <jh@web.de>
    @copyright: 2003-2004 by Thomas Waldmann
    @license: GNU GPL, see COPYING for details.
"""

import os, time, sys
from Sycamore import config, wikiutil, wikidb, user, i18n
from Sycamore.util import SycamoreNoFooter, web
import cPickle, cStringIO, gzip
if config.memcache:
  from Sycamore.support import MemcachePool

#############################################################################
### Misc
#############################################################################

class Clock:
    """ Helper class for code profiling
        we do not use time.clock() as this does not work across threads
    """

    def __init__(self):
        self.timings = {'total': time.time()}

    def start(self, timer):
        self.timings[timer] = time.time() - self.timings.get(timer, 0)

    def stop(self, timer):
        self.timings[timer] = time.time() - self.timings[timer]

    def value(self, timer):
        return "%.3f" % (self.timings[timer],)

    def dump(self):
        outlist = []
        for timing in self.timings.items():
            outlist.append("%s = %.3fs" % timing)
        return outlist



#############################################################################
### Request Data
#############################################################################
class RequestBase(object):
    """ A collection for all data associated with ONE request. """

    # Header set to force misbehaved proxies and browsers to keep their
    # hands off a page
    # Details: http://support.microsoft.com/support/kb/articles/Q234/0/67.ASP
    nocache = [
        ("Pragma", "no-cache"),
        ("Cache-Control", "no-cache"),
        ("Expires", "-1")
    ]

    def __init__(self, properties={}, process_dicts=True):
        self.writestack = []
	self.filestack = []
	self.getText = None

	self.generating_cache = False
	self.set_cache = False
        self.postCommitActions = []  # list of things to do after committing data to the database
        if config.memcache:
          self.mc = MemcachePool.getMC()
	#if not properties: properties = wikiutil.prepareAllProperties()
        #self.__dict__.update(properties)
	self.req_cache = {'pagenames': {},'users': {}, 'users_id': {}, 'userFavs': {}, 'page_info': {}, 'random': {}, 'links': {}, 'acls': {}, 'interwiki': None, 'file_dict': {}} # per-request cache

	self.db_connect()
        
        self.user = user.User(self)
        if process_dicts:
          self.dicts = self.initdicts()

        if config.theme_force:
            theme_name = config.theme_default
        else:
            theme_name = self.user.theme_name
        try:
            self.theme = wikiutil.importPlugin('theme', theme_name)(self)
        except TypeError:
            theme_name = config.theme_default
            self.theme = wikiutil.importPlugin('theme', theme_name)(self)

        self.args = None
        self.form = {}
        self.logger = None
        self.pragma = {}
        self.mode_getpagelinks = 0
        self.no_closing_html_code = 0

        self.sent_headers = False
        self.user_headers = []
	self.status = ''
	self.output_buffer = []

        self.i18n = i18n
        self.lang = i18n.requestLanguage(self) 
        self.getText = lambda text, i18n=self.i18n, request=self, lang=self.lang: i18n.getText(text, request, lang)
	self.pagename = None
	self.pagename_propercased = None

        # XXX Removed call to i18n.adaptcharset()
  
	self.previewing_page = False

        self.reset()

    def _setup_vars_from_std_env(self, env):
        """ Sets the common Request members by parsing a standard
            HTTPD environment (as created as environment by most common
            webservers. To be used by derived classes.

            @param env: the environment to use
        """
        self.http_accept_language = env.get('HTTP_ACCEPT_LANGUAGE', 'en')
        self.http_accept_encoding = env.get('HTTP_ACCEPT_ENCODING', '')
        self.server_name = env.get('SERVER_NAME', 'localhost')
        self.server_port = env.get('SERVER_PORT', '80')
        self.http_host = env.get('HTTP_HOST','localhost')
        self.http_referer = env.get('HTTP_REFERER', '')
        self.saved_cookie = env.get('HTTP_COOKIE', '')
        self.script_name = env.get('SCRIPT_NAME', '')
        self.path_info = env.get('PATH_INFO', '')
        self.query_string = env.get('QUERY_STRING', '')
        self.request_method = env.get('REQUEST_METHOD', None)
        
	self.remote_addr = env.get('REMOTE_ADDR')
	self.proxy_addr = None

        if env.has_key('HTTP_X_FORWARDED_FOR') and config.trust_x_forwarded_for:
            xff = env.get('HTTP_X_FORWARDED_FOR')
            if web.isIpAddress(xff):
                self.remote_addr = env.get('HTTP_X_FORWARDED_FOR')
                self.proxy_addr = env.get('REMOTE_ADDR')

        self.http_user_agent = env.get('HTTP_USER_AGENT', '')
        self.is_ssl = env.get('SSL_PROTOCOL', '') != '' \
            or env.get('SSL_PROTOCOL_VERSION', '') != '' \
            or env.get('HTTPS', 'off') == 'on'

        self.auth_username = None
        if config.auth_http_enabled and env.get('AUTH_TYPE','') == 'Basic':
            self.auth_username = env.get('REMOTE_USER','')

        # should we compress output?
	self.do_gzip = False
	if config.do_gzip:
	  for encoding in self.http_accept_encoding.split(','):
	    if encoding.lower() == 'gzip':
	      self.do_gzip = True
	      break

    def reset(self):
        """ Reset request state.

        Called after saving a page, before serving the updated
        page. Solves some practical problems with request state
        modified during saving.

        """
        # This is the content language and has nothing to do with
        # The user interface language. The content language can change
        # during the rendering of a page by lang macros
        self.current_lang = config.default_lang
        self._footer_fragments = {}
        self._all_pages = None

        if hasattr(self, "_fmt_hd_counters"):
            del self._fmt_hd_counters


    def add2footer(self, key, htmlcode):
        """ Add a named HTML fragment to the footer, after the default links
        """
        self._footer_fragments[key] = htmlcode


    def getPragma(self, key, defval=None):
        """ Query a pragma value (#pragma processing instruction)

            Keys are not case-sensitive.
        """
        return self.pragma.get(key.lower(), defval)


    def setPragma(self, key, value):
        """ Set a pragma value (#pragma processing instruction)

            Keys are not case-sensitive.
        """
        self.pragma[key.lower()] = value


    def getPageList(self, alphabetize=True, lowercase=False, objects=False):
        """ A cached version of wikiutil.getPageList().
            Also, this list is always sorted.
        """
        if self._all_pages is None:
            self._all_pages = wikiutil.getPageList(self, alphabetize=alphabetize, lowercase=lowercase, objects=objects)
        return self._all_pages

    def redirect(self, file=None):
        if file: # redirect output to "file"
            self.writestack.append(self.write)
            self.filestack.append(file)
        else: # restore saved output file
            self.write = self.writestack.pop()
	    self.filestack.pop()

    def reset_output(self):
        """ restore default output method
            destroy output stack
            (useful for error messages)
        """
        if self.writestack:
            self.write = self.writestack[0]
            self.writestack = []

    def write(self, *data):
        """ Write to output stream.
        """
        raise "NotImplementedError"

    def read(self, n):
        """ Read n bytes from input stream.
        """
        raise "NotImplementedError"

    def flush(self):
        """ Flush output stream.
        """
        raise "NotImplementedError"

    def initdicts(self, force_update=False, update_pagename=None):
        from Sycamore import wikidicts
        dicts = wikidicts.GroupDict(self)
        dicts.scandicts(force_update=force_update, update_pagename=update_pagename)
        return dicts
        
    def isForbidden(self):
        """ check for web spiders and refuse anything except viewing """
        forbidden = 0
        if ((self.query_string != '' or self.request_method != 'GET')
            and not self.query_string.startswith('action=rss_rc') and self.query_string != 'action=events&rss=1' and self.query_string != 'rss=1&action=events'):
            from Sycamore.util import web
            forbidden = web.isSpiderAgent(request=self)

        if not forbidden and config.hosts_deny:
            ip = self.remote_addr
            for host in config.hosts_deny:
                if ip == host or host[-1] == '.' and ip.startswith(host):
                    forbidden = 1
                    break
        return forbidden


    def setup_args(self):
        return {}

    def _setup_args_from_cgi_form(self, form=None):
        """ A method to create the args from a standart cgi.FieldStorage
            to be used be derived classes.

            @keyword form: a cgi.FieldStorage list. default is to call
                           cgi.FieldStorage().
        """
        import types, cgi
        
        if form is None:
            form = cgi.FieldStorage()

        args = {}
        for key in form.keys():
            values = form[key]
            if not isinstance(values, types.ListType):
                values = [values]
            fixedResult = []
            for i in values:
                if isinstance(i, cgi.MiniFieldStorage):
		    if type(i.value) == str:
		      fixedResult.append(i.value.decode(config.charset))
	 	    else:
                      fixedResult.append(i.value)
                elif isinstance(i, cgi.FieldStorage):
                    fixedResult.append(i.value)
                    # multiple uploads to same form field are stupid!
                    if i.filename:
                        args[key+'__filename__']=i.filename

            args[key] = fixedResult
        return args

    def recodePageName(self, pagename):
        # XXX TODO check for non-URI characters and then handle them according to
        # http://www.w3.org/TR/REC-html40/appendix/notes.html#h-B.2.1
        if pagename:
            try:
		pagename = unicode(pagename, 'utf-8')
            except UnicodeError:
		pagename = None  # will send to front page
        return pagename

    def getBaseURL(self):
        """ Return a fully qualified URL to this script. """
        return self.getQualifiedURL(self.getScriptname())


    def getQualifiedURL(self, uri=None):
        """ Return a full URL starting with schema, servername and port.

            *uri* -- append this server-rooted uri (must start with a slash)
        """
        if uri and uri[:4] == "http":
            return uri

        schema, stdport = (('http', '80'), ('https', '443'))[self.is_ssl]
        host = self.http_host
        if not host:
            host = self.server_name
            port = self.server_port
            if port != stdport:
                host = "%s:%s" % (host, port)

        result = "%s://%s" % (schema, host)
        if uri:
            result = result + uri

        return result

    def getUserAgent(self):
        """ Get the user agent. """
        return self.http_user_agent

    def compress(self, data):
      """Return gzip'ed data."""
      zbuf = cStringIO.StringIO()
      zfile = gzip.GzipFile(mode='wb', fileobj=zbuf, compresslevel=9)
      if type(data) == unicode:
	data = data.encode('utf-8')
      else:
        data = data.decode(config.db_charset).encode('utf-8')
      zfile.write(data)
      zfile.close()

      return zbuf.getvalue()

    def db_connect(self):
      self.db = wikidb.connect()
      self.cursor = self.db.cursor()

    def processPostCommitActions(self):
      # open a new db transaction because we may need the database
      self.db_connect()

      actions = self.postCommitActions

      self.postCommitActions = [] # clear it out to prevent infinite loop

      for action in actions:
        f = action[0]
        if len(action) == 2:
          args = action[1]
          f(args) 
        else:
          f()

      self.db_disconnect()

    def db_disconnect(self, had_error=False):
      commited = False
      if not had_error:
        if self.db.do_commit:
          self.db.commit()
          commited = True
	else:
	  self.db.rollback()
      else:
        self.db.rollback()

      self.cursor.close()
      del self.cursor
      del self.db

      if commited:
        self.processPostCommitActions()

    def run(self):
        had_error = False
        _ = self.getText
        #self.open_logs()
        if self.isForbidden():
	    self.status = "403 FORBIDDEN"
            self.http_headers([('Content-Type', 'text/plain')])
            self.write('You are not allowed to access this!\n')
            return self.finish()

        
        # parse request data
        try:
	    from Sycamore.Page import Page
            self.args = self.setup_args()
            self.form = self.args 
            path_info = self.getPathinfo()

            #from pprint import pformat
            #sys.stderr.write(pformat(self.__dict__))
    
            action = self.form.get('action',[None])[0]

            pagename = None
            oldlink = None
            if len(path_info) and path_info[0] == '/':
                pagename = wikiutil.unquoteWikiname(path_info[1:])
                oldlink = wikiutil.unquoteFilename(path_info[1:])

	    pagename = self.recodePageName(pagename)
            oldlink = self.recodePageName(oldlink)
	    self.pagename = pagename

	    pagename_propercased = ''
	    oldlink_propercased = ''
	    if pagename: 
	      pagename_exists_name = Page(pagename, self).exists()
	      if pagename_exists_name: pagename_propercased = pagename_exists_name
	      if oldlink:
                 oldlink_exists_name = Page(oldlink, self).exists()
	         if oldlink_exists_name: oldlink_propercased = oldlink_exists_name

	      if pagename_propercased:
	        self.pagename_propercased = pagename_propercased
	      else:
	        self.pagename = pagename
 
        except Page.ExcessiveLength, msg:
            Page(config.page_front_page, self).send_page(msg=msg)
            return self.finish()

        except: # catch and print any exception
            self.reset_output()
            self.http_headers()
            self.print_exception()
            return self.finish()

        # Imports
        from Sycamore.Page import Page
	if self.query_string.startswith('sendfile=true'):
	  from Sycamore.file import fileSend
	  self.args = self.setup_args()
          self.form = self.args 

	  fileSend(self)
	  return self.finish()
	   

        if self.query_string == 'action=xmlrpc':
            from Sycamore.wikirpc import xmlrpc
            xmlrpc(self)
            return self.finish()
        
        if self.query_string == 'action=xmlrpc2':
            from Sycamore.wikirpc import xmlrpc2
            xmlrpc2(self)
            return self.finish()


        try:
            # possibly jump to page where user left off
            #if not pagename and not action and self.user.remember_last_visit:
            #    pagetrail = self.user.getTrail()
            #    if pagetrail:
            #        self.http_redirect(Page(pagetrail[-1]).url(self))
            #        return self.finish()

            # handle request
            from Sycamore import wikiaction

	    #The following "if" is to deal with the switchover to urls with Page_names_like_this.
            if config.domain and (config.domain == "daviswiki.org" or config.domain == "rocwiki.org") and self.http_referer.find(config.domain) == -1:
                  if oldlink and oldlink_propercased:
                     pagename = oldlink

            #if self.form.has_key('filepath') and self.form.has_key('noredirect'):
            #    # looks like user wants to save a drawing
            #    from Sycamore.action.Files import execute
            #    execute(pagename, self)
            #    raise SycamoreNoFooter

            if action:
                handler = wikiaction.getHandler(action)
                if handler:
                    handler(pagename or
                    wikiutil.getSysPage(self, config.page_front_page).page_name, self)
                else:
                    self.http_headers()
                    self.write("<p>" + _("Unknown action"))
            else:
                if self.form.has_key('goto'):
                    query = self.form['goto'][0].strip()
                elif pagename:
                    query = pagename
                else:
                    query = wikiutil.unquoteWikiname(self.query_string) or \
                        wikiutil.getSysPage(self, config.page_front_page).proper_name()

		#self.http_headers()
                Page(query, self).send_page(count_hit=1)

            # generate page footer
            # (actions that do not want this footer use raise util.SycamoreNoFooter to break out
            # of the default execution path, see the "except SycamoreNoFooter" below)


                if 0: # temporarily disabled - do we need that?
                    import socket
                    from Sycamore import version
                    self.write('<!-- Sycamore %s on %s served this page in %s secs -->' % (
                        version.revision, socket.gethostname(), self.clock.value('total')) +
                               '</body></html>')
                else:
                    self.write('</body>\n</html>\n\n')
            
        except SycamoreNoFooter:
            pass

        except: # catch and print any exception
	    had_error = True
            saved_exc = sys.exc_info()
            self.reset_output()
            self.http_headers()
            self.write("\n<!-- ERROR REPORT FOLLOWS -->\n")
            try:
                from Sycamore.support import cgitb
            except:
                # no cgitb, for whatever reason
                self.print_exception(*saved_exc)
            else:
                try:
                    cgitb.Hook(file=self).handle(saved_exc)
                    # was: cgitb.handler()
                except:
                    self.print_exception(*saved_exc)
                    self.write("\n\n<hr>\n")
                    self.write("<p><strong>Additionally, cgitb raised this exception:</strong></p>\n")
                    self.print_exception()
            del saved_exc

        return self.finish(had_error=had_error)


    def http_redirect(self, url, type="text/html"):
        """ Redirect to a fully qualified, or server-rooted URL """
        if url.find("://") == -1:
            url = self.getQualifiedURL(url)

	self.status = "302 FOUND"
	self.user_headers = [("Location", url)]

    def print_exception(self, type=None, value=None, tb=None, limit=None):
        if type is None:
            type, value, tb = sys.exc_info()
        import traceback
        self.write("<h2>request.print_exception handler</h2>\n")
        self.write("<h3>Traceback (most recent call last):</h3>\n")
        list = traceback.format_tb(tb, limit) + \
               traceback.format_exception_only(type, value)
        self.write("<pre>%s<strong>%s</strong></pre>\n" % (
            wikiutil.escape("".join(list[:-1])),
            wikiutil.escape(list[-1]),))
        del tb


    def open_logs(self):
        pass


    def finish(self, had_error=False, dont_do_db=False):
      if not dont_do_db:
        self.db_disconnect(had_error=had_error)


# CLI ------------------------------------------
class RequestCLI(RequestBase):
    """ specialized on commandline interface requests """

    def __init__(self, pagename='', properties={}):
        self.http_accept_language = ''
        self.saved_cookie = ''
        self.path_info = '/' + pagename
        self.query_string = ''
        self.remote_addr = '127.0.0.127'
        self.is_ssl = 0
        self.auth_username = None
        RequestBase.__init__(self, properties)
        self.http_user_agent = ''
        self.outputlist = []

    def read(self, n=None):
        """ Read from input stream.
        """
        if n is None:
            return sys.stdin.read()
        else:
            return sys.stdin.read(n)

    def write(self, *data):
        """ Write to output stream.
        """
        for piece in data:
            sys.stdout.write(piece)

    def flush(self):
        sys.stdout.flush()
        
    def finish(self, had_error=False, dont_do_db=False):
	RequestBase.finish(self, had_error=had_error, dont_do_db=dont_do_db)
        # flush the output, ignore errors caused by the user closing the socket
        try:
            sys.stdout.flush()
        except IOError, ex:
            import errno
            if ex.errno != errno.EPIPE: raise

    def isForbidden(self):
        """ check for web spiders and refuse anything except viewing """
        return 0


    #############################################################################
    ### Accessors
    #############################################################################

    def getScriptname(self):
        """ Return the scriptname part of the URL ("/path/to/my.cgi"). """
        return '.'

    def getPathinfo(self):
        """ Return the remaining part of the URL. """
        return self.path_info


    def getQualifiedURL(self, uri = None):
        """ Return a full URL starting with schema, servername and port.

            *uri* -- append this server-rooted uri (must start with a slash)
        """
        return uri


    def getBaseURL(self):
        """ Return a fully qualified URL to this script. """
        return self.getQualifiedURL(self.getScriptname())



    #############################################################################
    ### Headers
    #############################################################################

    def setHttpHeader(self, header):
        pass

    def http_headers(self, more_headers=[]):
        pass

    def http_redirect(self, url):
        """ Redirect to a fully qualified, or server-rooted URL """
        raise Exception("Redirect not supported for command line tools!")

class RequestDummy(RequestBase):
  """ A fakeish request object that doesn't actually connect to any interfaces. """
  def __init__(self, process_dicts=True):
    self.output_buffer = []
    self.input_buffer = []
    self.setup_args()
    RequestBase.__init__(self, process_dicts=process_dicts)

  def setup_args(self):
    return self._setup_vars_from_std_env({})

  def write(self, data_string, raw=False):
    if not raw:
      if type(data_string) == str:
        data_string = data_string.decode('utf-8')
      if not self.filestack:
        self.output_buffer.append(data_string.encode('utf-8'))
      else:
        self.filestack[-1].write(data_string.encode('utf-8'))
    else:
      # some sort of raw binary data.  write directly without encoding and hope for the best!
      if not self.filestack:
        self.output_buffer.append(data_string)
      else:
        self.filestack[-1].write(data_string)


  def flush(self):
    pass

  def finish(self, had_error=False, dont_do_db=False):
    RequestBase.finish(self, had_error=had_error, dont_do_db=dont_do_db)
    """ Call finish method of WSGI request to finish handling
        of this request.
    """
    # we return a list as per the WSGI spec
    return self.output_buffer


  #############################################################################
  ### Accessors
  #############################################################################

  def getScriptname(self):
      """ Return the scriptname part of the URL ('/path/to/my.cgi'). """
      if not config.relative_dir: return ''
      return "/%s" % config.relative_dir


  def getPathinfo(self):
      """ Return the remaining part of the URL. """
      pathinfo = self.path_info

      # Fix for bug in IIS/4.0
      if os.name == 'nt':
          scriptname = self.getScriptname()
          if pathinfo.startswith(scriptname):
              pathinfo = pathinfo[len(scriptname):]

      return pathinfo


  #############################################################################
  ### Headers
  #############################################################################

  def setHttpHeader(self, header):
      """ Save header for later send. """
      pass

  def http_headers(self, more_headers=[]):
      """ Send out HTTP headers. Possibly set a default content-type.
      """
      pass

class RequestWSGI(RequestBase):
    """ General interface to Web Server Gateway Interface v1.0 """

    def __init__(self, env, start_response):
        """ Initializes variables from WSGI environment.

            @param env: the standard WSGI environment
            @param start_response: the standard WSGI response-starting function
        """
        self._setup_vars_from_std_env(env)
	self.start_response = start_response
	self.env = env
	properties = {}
        RequestBase.__init__(self, properties=properties)

    def setup_args(self):
      import cgi
      #print "env = ", self.env
      #form = cgi.FieldStorage(self, headers=self.env, environ=self.env)
      self.input_stream = self.env['wsgi.input']
      form = cgi.FieldStorage(self.input_stream, environ=self.env)
        
      return self._setup_args_from_cgi_form(form)

    def write(self, data_string, raw=False):
        """ Write to output stream.
        """
	if not raw:
	  if type(data_string) == str:
	    data_string = data_string.decode('utf-8')

	  if not self.filestack:
	    self.output_buffer.append(data_string.encode('utf-8'))
	  else:
	    self.filestack[-1].write(data_string.encode('utf-8'))
        else:
          # some sort of raw binary data.  write directly without encoding and hope for the best!
          if not self.filestack:
            self.output_buffer.append(data_string)
          else:
            self.filestack[-1].write(data_string)

    def read(self, n=None):
      # read n bytes from input stream
      if n is None:
        return self.input_stream.read()
      else:
        return self.input_stream.read(n)

    def flush(self):
        """ Flush output stream.
        """
	if self.do_gzip:
	  return  # Don't know if it's possible to sent gzip'ed content in chunks
	else:
  	  self.wsgi_output(''.join(self.output_buffer))

	self.output_buffer = []

    def finish(self, had_error=False, dont_do_db=False):
	RequestBase.finish(self, had_error=had_error, dont_do_db=dont_do_db)
        """ Call finish method of WSGI request to finish handling
            of this request.
        """
	if not self.sent_headers: self.http_headers()
	# we return a list as per the WSGI spec
	if self.do_gzip:
	  text = ''.join(self.output_buffer)
	  compressed_content = self.compress(text)
	  return [compressed_content] # WSGI spec wants a list returned
	else:
          return self.output_buffer


    #############################################################################
    ### Accessors
    #############################################################################

    def getScriptname(self):
        """ Return the scriptname part of the URL ('/path/to/my.cgi'). """
	if not config.relative_dir: return ''
	return "/%s" % config.relative_dir


    def getPathinfo(self):
        """ Return the remaining part of the URL. """
        pathinfo = self.path_info

        # Fix for bug in IIS/4.0
        if os.name == 'nt':
            scriptname = self.getScriptname()
            if pathinfo.startswith(scriptname):
                pathinfo = pathinfo[len(scriptname):]

        return pathinfo


    #############################################################################
    ### Headers
    #############################################################################

    def setHttpHeader(self, header):
        """ Save header for later send. """
        self.user_headers.append(header)


    def http_headers(self, more_headers=[]):
        """ Send out HTTP headers. Possibly set a default content-type.
        """
	if not self.sent_headers:
          # send http headers and get the write callable
	  all_headers = more_headers + self.user_headers
	  if not all_headers:
	    all_headers = [("Content-Type", "text/html; charset=%s" % config.charset)]

          if self.do_gzip:
	    all_headers.append(("Content-encoding", "gzip"))
	    all_headers.append(("Vary", "Accept-Encoding"))

	  if not self.status:
	    self.status = '200 OK'

	  self.wsgi_output = self.start_response(self.status, all_headers)
	  self.sent_headers = True

##################################
### Misc methods
#################################
def basic_handle_request(env, start_response):
    if env.get('QUERY_STRING', '') == 'profile':
      import profile
      prof = profile.Profile()
      prof.runctx('RequestWSGI(env,start_response).run()', globals(), locals())
      prof.dump_stats('prof.%s' % time.time())
    return RequestWSGI(env, start_response).run()
