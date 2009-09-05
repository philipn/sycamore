# -*- coding: utf-8 -*-
"""
    Sycamore - Data associated with a single Request

    @copyright: 2001-2003 by Jürgen Hermann <jh@web.de>
    @copyright: 2003-2004 by Thomas Waldmann
    @copyright: 2005-2007 by Philip Neustrom
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os
import time
import sys
import traceback
import cPickle
import cStringIO
import gzip

from copy import copy

from Sycamore import config
from Sycamore import wikiutil
from Sycamore import wikidb
from Sycamore import user
from Sycamore import i18n
from Sycamore.util import SycamoreNoFooter, web

if config.memcache:
    from Sycamore.support import MemcachePool
    from Sycamore.support import memcache

DO_PROFILE = False

#############################################################################
### Misc
#############################################################################

def setup_wiki_farm(request):
    """
    Setup environment, etc in the case of a wiki farm.
    """
    from Sycamore import farm
    if hasattr(request, 'env'):
        env = request.env
    else:
        return None
    if not config.wiki_farm:
        return None
    if not config.wiki_farm_subdomains:
        if env['PATH_INFO'][1:].startswith(config.wiki_farm_dir):
            rest_path = env['PATH_INFO'][len(config.wiki_farm_dir)+2:]
            wiki_name_location = rest_path.find('/')
            if wiki_name_location == -1:
                wiki_name = rest_path
                env['PATH_INFO'] = '/'
            else:
                wiki_name = rest_path[:wiki_name_location]
                env['PATH_INFO'] = rest_path[wiki_name_location:]
            return wiki_name
    else:
        domain = env.get('HTTP_HOST', '')
        if domain.endswith(config.wiki_base_domain):
            sub_domain = domain[:-len(config.wiki_base_domain)]
            split_sub_domain = sub_domain.split('.')
            if split_sub_domain[0] == 'www': # toss out www
                split_sub_domain = split_sub_domain[1:]
            if len(split_sub_domain) > 1:
                wiki_name = split_sub_domain[-2]
            else:
                wiki_name = split_sub_domain[0]
            return wiki_name
        else:
            wiki_name = farm.get_name_from_domain(domain, request)
            if wiki_name:
                return wiki_name
    return None

def canonical_url(request):
    """
    If we're in a wiki farm, make sure we're at the canonical
    location for this wiki -- e.g. their domain if they have
    one.
    """
    from Sycamore import farm
    if hasattr(request, 'env'):
        env = request.env
    else:
        return False
    domain = env.get('HTTP_HOST', '')
    if request.config.domain and not domain == request.config.domain:
        # we redirect to the canonical location for this wiki:
        # their proper domain name
        wiki_url = farm.getWikiURL(request.config.wiki_name, request)
        query_string = ''
        if request.query_string:
            query_string = '?' + request.query_string
        url = (wiki_url.encode(config.charset) + request.path_info[1:] +
               query_string)
        request.http_redirect(url, status="301 Moved Permanently")
        return True

    return False

def getRelativeDir(request):
    """
    Sets self.relative_dir to properly reflect config.relative_dir,
    which can be in parameter form.
    """
    if type(config.relative_dir) == tuple:
        format_string, items_string  = config.relative_dir
        items = eval(items_string)
        relative_dir = format_string % items
    else:
        relative_dir = config.relative_dir

    return relative_dir

def backward_compatibility(request, pagename, oldlink, oldlink_propercased): 
    """
    Based on whether or not we're an old-school Sycamore we do various
    conversion operations.

    We try to not break old URLs.  Ever.
    """
    # the switchover to urls with Page_names_like_this.
    if (request.config.domain and 
        (request.config.domain == "daviswiki.org" or
         request.config.domain == "rocwiki.org") and
       request.http_referer.find(request.config.domain) == -1):
        if oldlink and oldlink_propercased:
            pagename = oldlink

    return pagename

class postCommitMC(object):
    """
    An interface to the memcache object that intercepts set()
    appending these actions to the postCommit list.  This is safer because it
    is going to give us consistent data -- that which has been committed.
    """
    def __init__(self, request):
        self.request = request
        self.mc = request._mc
        self.postCommitActions = request.postCommitActions

    def _getPrefix(self):
        if hasattr(self.request, 'config'):
            return self.request.config.wiki_id
        return ''

    def set(self, name, value, **kws):
        if not kws.has_key('prefix'): kws['prefix'] = self._getPrefix()
        value = copy(value) 
        value = MemcachePool.fixEncoding(value)
        self.postCommitActions.append((self.mc.set, (name, value), kws))

    def add(self, name, value, **kws):
        if not kws.has_key('prefix'): kws['prefix'] = self._getPrefix()
        value = copy(value) 
        value = MemcachePool.fixEncoding(value)
        self.postCommitActions.append((self.mc.add, (name, value), kws))

    def delete(self, name, **kws):
        if not kws.has_key('prefix'): kws['prefix'] = self._getPrefix()
        self.postCommitActions.append((self.mc.delete, (name, ), kws))

    def get(self, name, **kws):
        if not kws.has_key('prefix'): kws['prefix'] = self._getPrefix()
        return self.mc.get(name, **kws)

    def __getattr__(self, name):
        """ For every thing we have no method/attribute use the mc"""
        if self.__dict__.has_key(name):
            return self.__dict__[name]
        else:
            if self.__dict__.has_key('mc'):
                return getattr(self.__dict__['mc'], name)


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

    class WikiNoExistError(Exception):
        pass

    def __init__(self, properties={}, process_config=True, wiki_name=None):
        self.writestack = []
        self.filestack = []
        self.getText = None
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

        self.html_head = []
        self.generating_cache = False
        self.did_redirect = False
        self.wiki_exists = True
        self.set_cache = False
        # list of things to do after committing data to the database
        self.postCommitActions = []  
        if config.memcache:
            # the 'real' memcache, which will send things as soon as it's
            # called
            self._mc = MemcachePool.getMC() 
            # wrap real memcache so set() and delete() only occur after
            # commits happen
            self.mc = postCommitMC(self) 
        # pre-request cache 
        self.req_cache = {'pagenames':{}, 'users':{}, 'users_id':{},
                          'userFavs': {}, 'page_info': {}, 'random': {},
                          'acls': {}, 'interwiki': {}, 'file_dict': {},
                          'group_dict':{}, 'group_ips':{},
                          'pageDateVersion':{}, 'pageVersionDate':{},
                          'watchedWikis': {}, 'wiki_config':{},
                          'wiki_domains':{}}
        self.db_connect()

        self.previewing_page = False
        self.i18n = i18n
        self.pagename = None
        self.pagename_propercased = None

        self.addresses = {} # for [[address]] macro.
        # the time our current request's save is marked for (if applicable)
        self.save_time = None 
        self.sent_page_content = None

        wiki_name = wiki_name or setup_wiki_farm(self)
        if not wiki_name:
            wiki_name = config.wiki_name

        self.config = config.Config(wiki_name, self,
            process_config=process_config)
        if canonical_url(self):
            # We do an http_redirect, so let's just return
            return
        self.setup_basics()

        self.reset()

    def setup_basics(self):
        if self.config.active:
            self.wiki_exists = True
        else:
            self.wiki_exists = False

        if not self.wiki_exists:
            theme_name = config.theme_default
            try:
                self.theme = wikiutil.importPlugin('theme', theme_name)(self)
            except TypeError:
                theme_name = self.config.theme_default
                self.theme = wikiutil.importPlugin('theme', theme_name)(self)
            return
        else:
            self.relative_dir = getRelativeDir(self)
            self.user = user.User(self, is_login=True)

            self.lang = i18n.requestLanguage(self) 
            self.getText = (lambda text, i18n=self.i18n, request=self,
                lang=self.lang: i18n.getText(text, request, lang))

            # set memcache to act locally to this wiki (prefix)
            if config.memcache:
                self.mc.setPrefix(self.config.wiki_id)

            theme_name = self.config.theme_default
            try:
                self.theme = wikiutil.importPlugin('theme', theme_name)(self)
            except TypeError:
                theme_name = self.config.theme_default
                self.theme = wikiutil.importPlugin('theme', theme_name)(self)
            # XXX Removed call to i18n.adaptcharset()

    def switch_wiki(self, wikiname):
        """
        "be" wiki wikiname.
        """
        if self.config.wiki_name != wikiname:
            self.config = config.Config(wikiname, self)
            if config.memcache:
                self.mc.setPrefix(self.config.wiki_id)

    def _setup_vars_from_std_env(self, env):
        """ Sets the common Request members by parsing a standard
            HTTPD environment (as created as environment by most common
            webservers). To be used by derived classes.

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

        if (env.has_key('HTTP_X_FORWARDED_FOR') and
            config.trust_x_forwarded_for):
            xff = env.get('HTTP_X_FORWARDED_FOR')
            if web.isIpAddress(xff):
                self.remote_addr = env.get('HTTP_X_FORWARDED_FOR')
                self.proxy_addr = env.get('REMOTE_ADDR')

        self.http_user_agent = env.get('HTTP_USER_AGENT', '')
        self.is_ssl = (env.get('SSL_PROTOCOL', '') != '' or
            env.get('SSL_PROTOCOL_VERSION', '') != '' or
            env.get('HTTPS', 'off') == 'on')

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
        """
        Add a named HTML fragment to the footer, after the default links
        """
        self._footer_fragments[key] = htmlcode

    def getPragma(self, key, defval=None):
        """
        Query a pragma value (#pragma processing instruction)
        Keys are not case-sensitive.
        """
        return self.pragma.get(key.lower(), defval)

    def setPragma(self, key, value):
        """
        Set a pragma value (#pragma processing instruction)
        Keys are not case-sensitive.
        """
        self.pragma[key.lower()] = value

    def isPOST(self):
        return self.request_method == 'POST' 

    def isSSL(self):
        return self.is_ssl

    def getPageList(self, alphabetize=True, lowercase=False, objects=False):
        """
        A cached version of wikiutil.getPageList().
        Also, this list is always sorted.
        """
        if self._all_pages is None:
            self._all_pages = wikiutil.getPageList(self,
                alphabetize=alphabetize, lowercase=lowercase, objects=objects)
        return self._all_pages

    def initdicts(self, force_update=False, update_pagename=None):
        from Sycamore import wikidicts
        dicts = wikidicts.GroupDict(self)
        dicts.scandicts(force_update=force_update,
            update_pagename=update_pagename)
        return dicts

    def redirect(self, file=None):
        if file: # redirect output to "file"
            self.writestack.append(self.write)
            self.filestack.append(file)
        else: # restore saved output file
            self.write = self.writestack.pop()
            self.filestack.pop()

    def reset_output(self):
        """
        restore default output method
        destroy output stack
        (useful for error messages)
        """
        if self.writestack:
            self.write = self.writestack[0]
            self.writestack = []

    def write(self, *data):
        """
        Write to output stream.
        """
        raise "NotImplementedError"

    def read(self, n):
        """
        Read n bytes from input stream.
        """
        raise "NotImplementedError"

    def flush(self):
        """
        Flush output stream.
        """
        raise "NotImplementedError"

    def isForbidden(self):
        """
        Check for web spiders and refuse anything except viewing
        """
        forbidden = 0
        if ((self.query_string != '' or self.request_method != 'GET') and not
            self.query_string.startswith('action=rss_rc') and
            self.query_string != 'action=events&rss=1' and
            self.query_string != 'rss=1&action=events'):
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
        """
        A method to create the args from a standart cgi.FieldStorage
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
        # XXX TODO check for non-URI characters and then handle them
        # according to
        # http://www.w3.org/TR/REC-html40/appendix/notes.html#h-B.2.1
        if pagename:
            try:
                pagename = unicode(pagename, 'utf-8')
            except UnicodeError:
                pagename = None  # will send to front page
        return pagename

    def getBaseURL(self):
        """
        Return a fully qualified URL to this script.
        """
        return self.getQualifiedURL(self.getScriptname())

    def getQualifiedURL(self, uri=None, force_ssl=False, force_ssl_off=False):
        """
        Return a full URL starting with schema, servername and port.

        *uri* -- append this server-rooted uri (must start with a slash)
        """
        if uri and uri[:4] == "http":
            return uri

        schema, stdport = (('http', '80'), ('https', '443'))[(self.is_ssl or
            force_ssl) or (self.is_ssl and force_ssl_off)]
        host = self.http_host

        if not host:
            host = self.server_name

        if force_ssl_off and self.is_ssl:
            schema = 'http'

        result = "%s://%s" % (schema, host)
        if uri:
            result = result + uri

        return result

    def getUserAgent(self):
        """
        Get the user agent.
        """
        return self.http_user_agent

    def compress(self, data):
        """
        Return gzip'ed data.
        """
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
            f(*args)
          elif len(action) == 3:
            args = action[1]
            kw_args = action[2]
            f(*args, **kw_args)
          else:
            f()

        self.db_disconnect(process_post=False)

    def db_disconnect(self, had_error=False, process_post=True):
        commited = False
        do_commit = self.db.do_commit
        if not had_error:
          if do_commit:
            self.db.commit()
            commited = True
          else:
            self.db.rollback()
        else:
          self.db.rollback()

        self.cursor.close()
        if not config.db_pool:
            self.db.close()

        if not had_error and process_post:
          self.processPostCommitActions()

    def run(self):
        from Sycamore import wikiacl
        had_error = False
        _ = self.getText
        #self.open_logs()
        if self.isForbidden():
            self.status = "403 FORBIDDEN"
            self.http_headers([('Content-Type', 'text/plain')])
            self.write('You are not allowed to access this!\n')
            return self.finish()

        if not self.wiki_exists:
             self.write('<html><head>'
                '<meta name="robots" content="noindex,follow"></head><body>')
             wiki_name = self.config.name 
             if type(config.wiki_farm_no_exist_msg) == tuple:
                msg, items_string = config.wiki_farm_no_exist_msg
                items = eval(items_string)
                no_exist_msg = msg % items
             else:
                no_exist_msg = config.wiki_farm_no_exist_msg
             self.write(no_exist_msg)
             self.write('</body></html>')
             return self.finish()
        elif (self.config.is_disabled and not
            self.user.name in wikiacl.Group("Admin", self)):
             self.write('<html><head>'
                '<meta name="robots" content="noindex,follow"></head><body>')
             self.write('<p>The wiki %s has been disabled and will be '
                        'permanently deleted in 30 days.</p>' % 
                        self.config.wiki_name)
             self.write('</body></html>')
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

            # if oldlink has control characters when we do an mc_quote -- eep!
            # we want to, then, throw it out because it wasn't going to work
            if (not oldlink or not
                wikiutil.suitable_mc_key(oldlink.encode(config.charset))):
               oldlink = ''

            pagename_propercased = ''
            oldlink_propercased = ''
            if pagename: 
                pagename_exists_name = Page(pagename, self).exists()
                if pagename_exists_name:
                    pagename_propercased = pagename_exists_name
                if oldlink:
                    oldlink_exists_name = Page(oldlink, self).exists()
                    if oldlink_exists_name:
                        oldlink_propercased = oldlink_exists_name

                if pagename_propercased:
                    self.pagename_propercased = pagename_propercased
                else:
                    self.pagename = pagename

                if self.pagename.endswith('/'):
                    pagename = self.pagename[:-1]
                    while pagename.endswith('/'):
                        pagename = pagename[:-1]
                    url = Page(pagename, self).url(relative=False)
                    self.http_redirect(url, status="301 MOVED PERMANENTLY")
 
        except Page.ExcessiveLength, msg:
            Page(self.config.page_front_page, self).send_page(msg=msg)
            return self.finish()
        except Page.InvalidPageName, page_name:
            from wikiaction import NOT_ALLOWED_CHARS
            not_allowed = ' '.join(NOT_ALLOWED_CHARS)
            msg = ('Invalid pagename: the characters %s are not allowed in page'
                   ' names.' % wikiutil.escape(not_allowed))
            Page(self.config.page_front_page, self).send_page(msg=msg)
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

        try:
            # handle request
            from Sycamore import wikiaction

            # The following "if" is to deal with various backward
            # compatability situations
            pagename = backward_compatibility(self, pagename, oldlink,
                                              oldlink_propercased)

            if action:
                handler = wikiaction.getHandler(action)
                if handler:
                    handler(pagename or
                            wikiutil.getSysPage(self,
                                self.config.page_front_page).page_name, self)
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
                        wikiutil.getSysPage(self,
                            self.config.page_front_page).proper_name()

                try:
                    Page(query, self).send_page(count_hit=1)
                except Page.ExcessiveLength, msg:
                    Page(self.config.page_front_page, self).send_page(msg=msg)
                    return self.finish()


            # generate page footer
            # (actions that do not want this footer use raise
            # util.SycamoreNoFooter to break out of the default execution path
            # see the "except SycamoreNoFooter" below)

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
                    self.write("<p><strong>Additionally, cgitb raised this "
                               "exception:</strong></p>\n")
                    self.print_exception()
            del saved_exc

        return self.finish(had_error=had_error)

    def http_redirect(self, url, mimetype="text/html", status="302 FOUND"):
        """
        Redirect to a fully qualified, or server-rooted URL.
        """
        if type(url) == unicode:
            url = url.encode(config.charset)
        if url.find("://") == -1:
            url = self.getQualifiedURL(url)

        self.status = status
        self.user_headers.append(("Location", url))

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


class RequestDummy(RequestBase):
    """
    A fakeish request object that doesn't actually connect to any interfaces.
    """
    def __init__(self, process_config=True, wiki_name=config.wiki_name):
        self.output_buffer = []
        self.input_buffer = []
        self.setup_args()
        RequestBase.__init__(self, process_config=process_config,
                             wiki_name=wiki_name)

    def setup_args(self, env={}):
        return self._setup_vars_from_std_env(env)

    def write(self, data_string, raw=False):
        if not raw:
            if type(data_string) == str:
                data_string = data_string.decode('utf-8')
            if not self.filestack:
                self.output_buffer.append(data_string.encode('utf-8'))
            else:
                self.filestack[-1].write(data_string.encode('utf-8'))
        else:
            # some sort of raw binary data.
            # write directly without encoding and hope for the best!
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


    ###########################################################################
    ### Accessors
    ###########################################################################

    def getScriptname(self):
        """
        Return the scriptname part of the URL ('/path/to/my.cgi').
        """
        if not self.relative_dir:
            return ''
        return "/%s" % self.relative_dir

    def getPathinfo(self):
        """
        Return the remaining part of the URL.
        """
        pathinfo = self.path_info

        # Fix for bug in IIS/4.0
        if os.name == 'nt':
            scriptname = self.getScriptname()
            if pathinfo.startswith(scriptname):
                pathinfo = pathinfo[len(scriptname):]

        return pathinfo

    ###########################################################################
    ### Headers
    ###########################################################################

    def setHttpHeader(self, header):
        """
        Save header for later send.
        """
        pass

    def http_headers(self, more_headers=[], send_headers=True):
        """
        Send out HTTP headers. Possibly set a default content-type.
        """
        pass

class RequestWSGI(RequestBase):
    """
    General interface to Web Server Gateway Interface v1.0
    """

    def __init__(self, env, start_response, wiki_name=None):
        """
        Initializes variables from WSGI environment.

        @param env: the standard WSGI environment
        @param start_response: the standard WSGI response-starting function
        """
        self._setup_vars_from_std_env(env)
        self.start_response = start_response
        self.env = env
        properties = {}
        if wiki_name:
            RequestBase.__init__(self, properties=properties,
                                 wiki_name=wiki_name)
        else:
            RequestBase.__init__(self, properties=properties)

    def setup_args(self):
      import cgi
      self.input_stream = self.env['wsgi.input']
      form = cgi.FieldStorage(self.input_stream, environ=self.env)
        
      return self._setup_args_from_cgi_form(form)

    def write(self, data_string, raw=False):
        """
        Write to output stream.
        """
        if not raw:
            if type(data_string) == str:
                data_string = data_string.decode('utf-8')

            if not self.filestack:
                self.output_buffer.append(data_string.encode('utf-8'))
            else:
                self.filestack[-1].write(data_string.encode('utf-8'))
        else:
            # some sort of raw binary data.
            # write directly without encoding and hope for the best!
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
        """
        Flush output stream.
        """
        if self.do_gzip:
          # Don't know if it's possible to sent gzip'ed content in chunks
          return  
        else:
          self.wsgi_output(''.join(self.output_buffer))

        self.output_buffer = []

    def finish(self, had_error=False, dont_do_db=False):
        """
        Call finish method of WSGI request to finish handling
        of this request.
        """
        RequestBase.finish(self, had_error=had_error, dont_do_db=dont_do_db)
        if not self.sent_headers:
            self.http_headers()
        # we return a list as per the WSGI spec
        if self.do_gzip:
            text = ''.join(self.output_buffer)
            compressed_content = self.compress(text)
            return [compressed_content] # WSGI spec wants a list returned
        else:
            return self.output_buffer


    ###########################################################################
    ### Accessors
    ###########################################################################

    def getScriptname(self):
        """
        Return the scriptname part of the URL ('/path/to/my.cgi').
        """
        if not self.relative_dir:
            return ''
        return "/%s" % self.relative_dir

    def getPathinfo(self):
        """
        Return the remaining part of the URL.
        """
        pathinfo = self.path_info

        # Fix for bug in IIS/4.0
        if os.name == 'nt':
            scriptname = self.getScriptname()
            if pathinfo.startswith(scriptname):
                pathinfo = pathinfo[len(scriptname):]

        return pathinfo

    ###########################################################################
    ### Headers
    ###########################################################################

    def setHttpHeader(self, header):
        """
        Save header for later send.
        """
        h0, h1 = header
        if type(h0) == unicode:
            h0 = h0.encode(config.charset)
        if type(h1) == unicode:
            h1 = h1.encode(config.charset)
        header = (h0, h1)
        self.user_headers.append(header)

    def http_headers(self, more_headers=[], send_headers=True):
        """
        Send out HTTP headers. Possibly set a default content-type.
        """
        if self.sent_headers:
            return

        if send_headers:
            # send http headers and get the write callable
            all_headers = more_headers + self.user_headers
            if not all_headers:
              all_headers = [("Content-Type", "text/html; charset=%s" % (
                config.charset))]
        else:
            all_headers = []

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
    if DO_PROFILE:
        import profile
        prof = profile.Profile()
        req = RequestWSGI(env, start_response)
        prof.runctx('req.run()', globals(), locals())
        prof.dump_stats('prof.%s.%s' % (os.getpid(), time.time()))
        # we return a list as per the WSGI spec
        if req.do_gzip:
            text = ''.join(req.output_buffer)
            compressed_content = req.compress(text)
            return [compressed_content] # WSGI spec wants a list returned
        else:
            return req.output_buffer
    else:
        return RequestWSGI(env, start_response).run()
