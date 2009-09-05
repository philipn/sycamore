# -*- coding: utf-8 -*-
"""
    Sycamore - User Accounts

    @copyright: 2000-2004 by J?rgen Hermann <jh@web.de>,
    2005-2007 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os
import string
import time
import Cookie
import sha
import locale
import pickle
import urllib
import xml.dom.minidom
from copy import copy

from Sycamore import config
from Sycamore import wikiutil
from Sycamore import wikidb
from Sycamore.util import datetime

#import pytz from support
import sys, os.path
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, 'support'))])
import pytz

#############################################################################
### Helpers
#############################################################################
COOKIE_NOT_LOGGED_IN = 'nologin'

def getUserList(cursor):
    """
    Get a list of all (numerical) user IDs.
    
    @rtype: list
    @return: all user IDs
    """
    all_ids = []
    cursor.execute("SELECT id from users")
    userid = cursor.fetchone()
    while userid:
        all_ids.append(userid[0].strip())
        userid = cursor.fetchone()
    return all_ids

_name2id = None

def getUserId(searchName, request):
    """
    Get the user ID for a specific user NAME.

    @param searchName: the user name to look up
    @rtype: string
    @return: the corresponding user ID or None
    """
    if not searchName:
        return ''
    searchName = searchName.lower()

    cursor = request.cursor
    id = ''
    if request.req_cache['users_id'].has_key(searchName):
        id = request.req_cache['users_id'][searchName]
        return id
    if not id and config.memcache:
        id = request.mc.get('users_id:%s' % wikiutil.mc_quote(searchName),
                            wiki_global=True)
    if not id:
        cursor.execute("SELECT id from users where name=%(username)s",
                       {'username':searchName})
        result = cursor.fetchone()
        if result:
            id = result[0].strip()
            if config.memcache:
                request.mc.add('users_id:%s' % wikiutil.mc_quote(searchName),
                               id, wiki_global=True)

    request.req_cache['users_id'][searchName] = id
    return id

def getUserIdByEmail(email, request):
    request.cursor.execute("SELECT id from users where email=%(email)s",
                           {'email':email})
    result = request.cursor.fetchone()
    if result:
        return result[0].strip()

def getUserLinkURL(request, userObject, wiki_name=None):
    if userObject.anonymous:
        return None
    else:
        from Sycamore import Page
        wiki_name = userObject.wiki_for_userpage or wiki_name
        if wiki_name and wiki_name != request.config.wiki_name:
            return Page.Page(config.user_page_prefix + 
                             userObject.propercased_name, request,
                             wiki_name=wiki_name
                             ).url()
        else:
            return Page.Page(config.user_page_prefix +
                             userObject.propercased_name, request
                             ).url()

def getUserLink(request, userObject, wiki_name=None, text=None,
                show_title=True, absolute=False):
    if userObject.anonymous:
        return userObject.ip
    else:
        from Sycamore import Page
        wiki_name = userObject.wiki_for_userpage or wiki_name
        text = text or userObject.propercased_name
        if wiki_name and wiki_name != request.config.wiki_name:
            return Page.Page(config.user_page_prefix +
                             userObject.propercased_name, request,
                             wiki_name=wiki_name
                             ).link_to(text=text, show_title=show_title,
                                       absolute=absolute)
        else:
            return Page.Page(config.user_page_prefix +
                             userObject.propercased_name, request
                             ).link_to(text=text, show_title=show_title,
                                       absolute=absolute)

def getUserIdentification(request, username=None):
    """ 
    Return user name or IP or '<unknown>' indicator.
    
    @param request: the request object
    @param username: (optional) user name
    @rtype: string
    @return: user name or IP or unknown indicator
    """
    _ = request.getText

    if username is None:
        username = request.user.name

    return username or request.remote_addr or _("<unknown>")

def userPageChangedState(page, action):
    """
    The user page provided was either deleted or created.
    """
    username = page.page_name[len(config.user_page_prefix):]
    the_user = User(page.request, name=username)
    if action == 'DELETE':
        the_user.delUserPage(page.wiki_name)
        # We remove the page from the user's bookmarks.
        the_user.delFavorite(page)
    elif action == 'SAVENEW':
        the_user.addUserPage(page.wiki_name)
        # We add the page to the user's bookmarks.
        the_user.favoritePage(page, by_user=False)

def unify_userpage(request, word, text, prefix=False):
    """
    If this is a userpage, let's link to the one they set as their home.
    """
    if word.lower().startswith(config.user_page_prefix.lower()):
        username = word[len(config.user_page_prefix):]
        theuser = User(request, name=username)
        if theuser.exists():
            if prefix:
                return getUserLink(request, theuser,
                                   text=(config.user_page_prefix + username))
            elif not text:
                return getUserLink(request, theuser, text=username)
            else:
                return getUserLink(request, theuser, text=text)
            
    return False

def getGroupList(request, exclude_special_groups=False):
    """
    Returns a list of the user groups on this wiki.
    """
    import wikiacl
    grouplist = wikiacl.AccessControlList(request).grouplist()
    if exclude_special_groups:
        for entry in wikiacl.special_groups:
            grouplist.remove(entry)
    return grouplist


class WikiInfo(object):
    def __init__(self, user, **kw):
        self.__dict__.update(kw)


def encodePassword(pwd):
    """
    Encode a cleartext password, compatible to Apache htpasswd SHA encoding.

    @param pwd: the cleartext password
    @rtype: string
    @return: the password in apache htpasswd compatible SHA-encoding
    """
    return hash(pwd)

def hash(cleartext):
    """
    SHA hash of cleartext returned
    """
    import base64
    return base64.encodestring(sha.new(cleartext.encode('utf-8')).digest()
                              ).rstrip()

#############################################################################
### User
#############################################################################
DEFAULT_WIKI_INFO_VALUES = [ None, 0, 0, 0, None, None, None ]

class User(object):
    """
    A Sycamore User
    """

    _checkbox_fields = ['remember_me', 'disabled']
    _transient_fields =  ['id', 'valid', 'may', 'auth_username', 'trusted']
    _MAX_TRAIL = config.trail_size

    def __init__(self, request, id=None, name="", password=None,
                 auth_username="", is_login=False):
        """
        Initialize user object
        
        @param request: the request object
        @param id: (optional) user ID
        @param name: (optional) user name
        @param password: (optional) user password
        @param auth_username: (optional) already authenticated user name
                              (e.g. apache basic auth)
        """
        self.request = request
        self.valid = 0
        self.id = id
        
        if auth_username:
            self.auth_username = auth_username
        elif request and hasattr(request, 'auth_username'):
            self.auth_username = request.auth_username
        else:
            self.auth_username = ""

        self.propercased_name = name
        self.name = self.propercased_name.lower()
        if not password:
            self.enc_password = ""
        else:
            self.enc_password = encodePassword(password)
        self.trusted = 0
        self.email = ""
        self.edit_rows = config.edit_rows
        self.edit_cols = 80
        self.last_saved = str(time.time())
        self.css_url = ""
        self.language = ""
        self.theme_name = self.request.config.theme_default
        self.tz = self.request.config.tz
        self.tz_offset = 0
        self.rc_bookmark = 0
        self.rc_showcomments = 1
        self.rc_group_by_wiki = False
        self.wiki_for_userpage = ''
        self.favorites = None
        self.watched_wikis = None
        self.user_pages = None
        self.is_login = is_login
        self.ip = None
        self.anonymous = False
        if self.id:
            if self.id[0:4] == 'anon' and not self.name:
                self.anonymous = True
                self.ip = self.id[5:]
            self.id = self.id.strip()
        not_logged_in = None
        self.cookie_dough = None

        self.wiki_info = {}

        # if an account is disabled, it may be used for looking up
        # id -> username for page info and recent changes, but it
        # is not usabled for the user any more:
        # self.disabled   = 0
        # is handled by checkbox now.
        
        # attrs not saved to profile
        self._trail = []

        # create checkbox fields (with default 0)
        for key in self._checkbox_fields:
            setattr(self, key, 0)

        self.remember_me = 1
        logged_in_via_cookie = False

        if (not self.auth_username and not self.id and not self.name and
            hasattr(request, 'saved_cookie')):
            try:
                cookie = Cookie.SimpleCookie(request.saved_cookie)
            except Cookie.CookieError:
                # ignore invalid cookies, else user can't relogin
                cookie = None
            if cookie:
                if config.wiki_farm:
                    cookie_id = wikiutil.quoteCookiename(
                        config.wiki_base_domain + ',ID')
                else:
                    cookie_id = wikiutil.quoteCookiename(config.sitename +
                        ',ID')

                if cookie.has_key(cookie_id):
                    # does their cookie pass our super elite test?
                    if self.isValidCookieDough(cookie[cookie_id].value):
                            # okay, lets let them in
                            self.id = self.getUserIdDough(
                                cookie[cookie_id].value)
                            self.is_login = True
                            logged_in_via_cookie = True
                            # kill possible old 'COOKIE_NOT_LOGGED_IN' cookies
                            if cookie.has_key(COOKIE_NOT_LOGGED_IN):
                                # clear out this cookie
                                cookie_dir = config.web_dir
                                if not cookie_dir:
                                    cookie_dir = '/'
                                expirestr = time.strftime("%A, %d-%b-%Y %H:%M:%S GMT",
                                                          time.gmtime(0))
                                request.setHttpHeader(('Set-Cookie',
                                     ('%s="%s"; domain=%s; path=%s; '
                                      'expires=%s' % (
                                        COOKIE_NOT_LOGGED_IN,
                                        cookie[COOKIE_NOT_LOGGED_IN].value,
                                        wikiutil.getCookieDomain(request),
                                        cookie_dir, expirestr))))
                    else:
                        # clear out this cookie
                        cookie_dir = config.web_dir
                        if not cookie_dir:
                            cookie_dir = '/'
                        if (config.wiki_base_domain == 'localhost'or
                            config.wiki_base_domain == '127.0.0.1'):
                            # browsers reject domain=localhost or
                            # domain=127.0.0.1
                            domain = '' 
                        else:
                            domain = config.wiki_base_domain
                        expirestr = time.strftime("%A, %d-%b-%Y %H:%M:%S GMT",
                                                  time.gmtime(0))
                        request.setHttpHeader(('Set-Cookie',
                             ('%s="%s"; domain=%s; path=%s; '
                              'expires=%s' % (
                             (cookie_id, cookie[cookie_id].value,
                                domain, cookie_dir, expirestr)))))


                        if (cookie.has_key(COOKIE_NOT_LOGGED_IN) or
                            request.form.has_key('not_logged_in')):
                            # COOKIE_NOT_LOGGED_IN is a shortcut so we
                            # don't redirect the poor user all the time
                            not_logged_in = True 

                elif (cookie.has_key(COOKIE_NOT_LOGGED_IN) or
                      request.form.has_key('not_logged_in')):
                    # COOKIE_NOT_LOGGED_IN is a shortcut so we
                    # don't redirect the poor user all the time
                    not_logged_in = True 
                                
        # we got an already authenticated username:
        if not self.id and self.auth_username:
            self.id = getUserId(self.auth_username, self.request)
        # login via form, entering password
        elif not self.id and self.name and self.is_login:
            self.id = getUserId(self.name, self.request)

        if self.id:
            self.load_from_id(check_pass=(is_login and not
                                          logged_in_via_cookie))
            if self.name == self.auth_username:
                self.trusted = 1
        elif self.name:
            self.load(check_pass=is_login)

        # we want them to be able to sign back in right after they
        # click the 'logout' GET link, hence this test
        is_form_logout = (request.form.has_key('qs') and 
                          urllib.unquote(request.form['qs'][0]) == 
                            'action=userform&logout=Logout')
        if is_login:
            if (not_logged_in is None and request.config.domain and
                request.config.domain != config.wiki_base_domain and 
                config.wiki_farm and not self.id and not is_form_logout):
                  # we try the base farm for authentication
                  page_url = '%s%s' % (request.getBaseURL(),
                                       request.getPathinfo())
                  if request.query_string:
                        qs = '&qs=%s' % urllib.quote(request.query_string)
                  else:
                        qs = ''
                  url = ('http://%s%s/%s?action=userform&login_check=1'
                         '&backto_wiki=%s&backto_page=%s%s') % (
                            config.wiki_base_domain, config.web_dir,
                            config.relative_dir, request.config.wiki_name,
                            urllib.quote(page_url), qs)
                  request.html_head.append('<script type="text/javascript">'
                                           'var authentication_url = \'%s\';'
                                           '</script>' % url)
            else:
                request.html_head.append('<script type="text/javascript">'
                                         'var authentication_url = \'\';'
                                         '</script>')

        if not self.name and not self.id:
            # anonymous user
            self.anonymous = True
            self.id = 'anon:%s' % self.request.remote_addr
            self.ip = self.ip = self.request.remote_addr
            
        # "may" so we can say "if user.may.edit(pagename):"
        if config.SecurityPolicy:
            self.may = config.SecurityPolicy(self)
        else:
            from security import Default
            self.may = Default(self)

        if self.is_login:
            self._init_login()

        self.tz_offset = wikiutil.getTimeOffset(self.tz)

    def exists(self):
        """
        Do we have a user account for this user?
        
        @rtype: bool
        @return: true, if we have a user account
        """
        if not self.id:
            return False
        result = False
        if self.id[0:4] == 'anon':
            return False
        if self.request.req_cache['users'].has_key(self.id):
            result = self.request.req_cache['users'][self.id]
        if not result:
            if config.memcache:
              result = self.request.mc.get('users:%s' % self.id,
                                           wiki_global=True)
            if not result:
              self.request.cursor.execute(
                """SELECT name, email, enc_password, language, remember_me,
                          css_url, disabled, edit_cols, edit_rows, theme_name,
                          last_saved, tz, rc_bookmark, propercased_name,
                          wiki_for_userpage, rc_showcomments, rc_group_by_wiki
                   from users where id=%(userid)s""", {'userid':self.id})
              data = self.request.cursor.fetchone()
              if data:
                    user_data = {'enc_password': ''}
                    user_data['name'] = data[0]
                    user_data['email'] = data[1]
                    user_data['enc_password'] = data[2]
                    user_data['language'] = data[3]
                    user_data['remember_me'] = data[4]
                    user_data['css_url'] = data[5] or ''
                    user_data['disabled'] = data[6]
                    user_data['edit_cols'] = data[7]
                    user_data['edit_rows'] = data[8]
                    user_data['theme_name'] = data[9]
                    user_data['last_saved'] = data[10]
                    user_data['tz'] = data[11] or self.request.config.tz
                    user_data['rc_bookmark'] = data[12]
                    user_data['propercased_name'] = data[13]
                    user_data['wiki_for_userpage'] = data[14] or ''
                    user_data['rc_showcomments'] = data[15]
                    user_data['rc_group_by_wiki'] = data[16]

                    result = user_data
                    if config.memcache:
                        self.request.mc.add('users:%s' % self.id, result,
                                            wiki_global=True)

            self.request.req_cache['users'][self.id] = result
          
        if result:
            return True
        return False

    def load(self, check_pass=True):
        """
        Lookup user ID by user name and load user account.

        Can load user data if the user name is known,
        but only if the password is set correctly.
        """
        self.id = getUserId(self.name, self.request)
        if self.id:
            self.load_from_id(check_pass=check_pass)
        
    def load_from_id(self, check_pass=0):
        """
        Load user account data from disk.

        Can only load user data if the id number is already known.

        This loads all member variables, except "id" and "valid" and
        those starting with an underscore.
        
        @param check_pass: If 1, then self.enc_password must match the
                           password in the user account file.
        """
        if not self.exists():
            return

        # XXX UNICODE fix needed, we want to read utf-8 and decode to unicode
        user_data = False
        if self.request.req_cache['users'].has_key(self.id):
            user_data = self.request.req_cache['users'][self.id]
        if not user_data:
            if config.memcache:
                user_data = self.request.mc.get('users:%s' % self.id,
                                                wiki_global=True)
            if not user_data:
                self.request.cursor.execute(
                    """SELECT name, email, enc_password, language, remember_me,
                              css_url, disabled, edit_cols, edit_rows,
                              theme_name, last_saved, tz, rc_bookmark,
                              rc_showcomments, propercased_name,
                              wiki_for_userpage, rc_group_by_wiki
                       from users where id=%(userid)s""", {'userid':self.id})
                data = self.request.cursor.fetchone()

                user_data = {'enc_password': ''}
                user_data['name'] = data[0] 
                user_data['email'] = data[1]
                user_data['enc_password'] = data[2]
                user_data['language'] = data[3]
                user_data['remember_me'] = data[4]
                user_data['css_url'] = data[5] or ''
                user_data['disabled'] = data[6]
                user_data['edit_cols'] = data[7]
                user_data['edit_rows'] = data[8]
                user_data['theme_name'] = data[9]
                user_data['last_saved'] = data[10]
                user_data['tz'] = data[11] or self.request.config.tz
                user_data['rc_bookmark'] = data[12]
                user_data['rc_showcomments'] = data[13]
                user_data['propercased_name'] = data[14]
                user_data['wiki_for_userpage'] = data[15] or ''
                user_data['rc_group_by_wiki'] = data[16]

                if config.memcache:
                    self.request.mc.add('users:%s' % self.id, user_data,
                                        wiki_global=True)

            self.request.req_cache['users'][self.id] = user_data

        if check_pass:
            # If we have no password set, we don't accept login with username
            if not user_data['enc_password']:
                return
            # Check for a valid password
            elif user_data['enc_password'] != self.enc_password:
                return
            else:
                self.trusted = 1

        # Copy user data into user object
        for key, val in user_data.items():
            vars(self)[key] = val

        # old passwords are untrusted
        if hasattr(self, 'password'):
            del self.password
        if hasattr(self, 'passwd'):
            del self.passwd

        # make sure checkboxes are boolean
        for key in self._checkbox_fields:
            try:
                setattr(self, key, int(getattr(self, key)))
            except ValueError:
                setattr(self, key, 0)

        # clear trail
        self._trail = []

        if not self.disabled:
            self.valid = 1

    def _new_user_id(self):
        """
        Generates a new and unique user id.
        """
        from random import randint
        id = "%s.%d" % (str(time.time()), randint(0,65535))
        # check to make sure the id is unique
        # (we could, after all, change our user id scheme at some point..)
        self.request.cursor.execute("SELECT id from users where id=%(userid)s",
                                    {'userid':id})
        result = self.request.cursor.fetchone()
        while result:
            # means it's not unique, so let's try another
            id = "%s.%d" % (str(time.time()), randint(0,65535))
            self.request.cursor.execute(
                "SELECT id from users where id=%(userid)s", {'userid':id})
            result = self.request.cursor.fetchone()
        return id

    def getUserdict(self):
        """
        Returns dictionary of all relevant user values.
        essentially an entire user's relevant information.
        """
        return {'id':self.id, 'name':self.name, 'email':self.email,
                'enc_password':self.enc_password, 'language':self.language,
                'remember_me':str(self.remember_me), 'css_url':self.css_url,
                'disabled':str(self.disabled), 'edit_cols':self.edit_cols,
                'edit_rows':self.edit_rows, 'theme_name':self.theme_name,
                'last_saved':self.last_saved, 'tz':self.tz,
                'wiki_for_userpage':self.wiki_for_userpage,
                'rc_bookmark':self.rc_bookmark,
                'rc_showcomments':self.rc_showcomments,
                'rc_group_by_wiki':self.rc_group_by_wiki,
                'propercased_name':self.propercased_name,
                'wiki_info':self.wiki_info}

    def save(self, new_user=False):
        """
        Save user account data to user account file on disk.

        This saves all member variables, except "id" and "valid" and
        those starting with an underscore.
        """
        self.last_saved = time.time()

        userdict = self.getUserdict()

        if new_user:
            self.id = self._new_user_id()
            # account doesn't exist yet
            userdict['join_date'] = time.time()
            userdict['id'] = self.id
            self.request.cursor.execute(
                """INSERT into users (id, name, email, enc_password, language,
                                      remember_me, css_url, disabled,
                                      edit_cols, edit_rows, theme_name,
                                      last_saved, join_date, tz,
                                      propercased_name, rc_bookmark,
                                      rc_showcomments, wiki_for_userpage)
                   values (%(id)s, %(name)s, %(email)s, %(enc_password)s,
                           %(language)s, %(remember_me)s, %(css_url)s,
                           %(disabled)s, %(edit_cols)s, %(edit_rows)s,
                           %(theme_name)s, %(last_saved)s, %(join_date)s,
                           %(tz)s, %(propercased_name)s, %(rc_bookmark)s,
                           %(rc_showcomments)s, %(wiki_for_userpage)s)""",
                userdict, isWrite=True)
            if config.memcache:
                self.request.mc.set("users:%s" % self.id, userdict,
                                    wiki_global=True)
        else:
            self.request.cursor.execute(
                """UPDATE users set id=%(id)s, name=%(name)s, email=%(email)s,
                                enc_password=%(enc_password)s,
                                language=%(language)s,
                                remember_me=%(remember_me)s,
                                css_url=%(css_url)s, disabled=%(disabled)s,
                                edit_cols=%(edit_cols)s,
                                edit_rows=%(edit_rows)s,
                                theme_name=%(theme_name)s,
                                last_saved=%(last_saved)s, tz=%(tz)s,
                                propercased_name=%(propercased_name)s,
                                rc_bookmark=%(rc_bookmark)s,
                                rc_showcomments=%(rc_showcomments)s,
                                wiki_for_userpage=%(wiki_for_userpage)s,
                                rc_group_by_wiki=%(rc_group_by_wiki)s
                   where id=%(id)s""", userdict, isWrite=True)
            if config.memcache:
                self.request.mc.set("users:%s" % self.id, userdict,
                                    wiki_global=True)
                
    def makeCookieDict(self, cookie_header):
        return {cookie_header[0]:cookie_header[1]}

    def makeCookieHeader(self, expire=None, sessionid=None, secret=None,
                         id=None):
        """
        Make the Set-Cookie header for this user
            
        uses: config.cookie_lifetime (int) [hours]
            == 0  --> cookie will live forever
                      (no matter what user has configured!)
            > 0   --> cookie will live for n hours
                      (or forever when "remember_me")
            < 0   --> cookie will live for -n hours
                      (forced, ignore "remember_me"!)
        """
        if not expire:
            # 10 years, after this time the polar icecaps
            # will have melted anyway
            forever = 10*365*24*3600 
            lifetime = int(config.cookie_lifetime) * 3600
            now = time.time()
            if not lifetime:
                expire = now + forever
            elif lifetime > 0:
                if self.remember_me:
                    expire = now + forever
                else:
                    expire = now + lifetime
            elif lifetime < 0:
                expire = now + (-lifetime)

        loc=locale.setlocale(locale.LC_TIME, 'C')
        expirestr = time.strftime("%A, %d-%b-%Y %H:%M:%S GMT",
                                  time.gmtime(expire))
        locale.setlocale(locale.LC_TIME, loc)

        cookie = Cookie.SimpleCookie()
        if sessionid is None or secret is None:
            sessionid, secret = self.cookieDough(expire, now)
        if config.wiki_farm:
            cookie_id = wikiutil.quoteCookiename(config.wiki_base_domain +
                                                 ',ID')
        else:
            cookie_id = wikiutil.quoteCookiename(config.sitename + ',ID')
        if not id:
            id = self.id

        cookie_value = id + ',' + sessionid + ',' + secret
        cookie_dir = config.web_dir
        if not cookie_dir: cookie_dir = '/'
        wiki_domain = wikiutil.getCookieDomain(self.request)
        
        domain = " domain=%s;" % wiki_domain

        return ("Set-Cookie", '%s="%s";%s path=%s; expires=%s' %
                (cookie_id, cookie_value, domain, cookie_dir, expirestr))

    def cookieDough(self, expiretime, now):
        """
        Creates a session-specific secret that is stored in the user's cookie.
        Stores a hashed version of of this secret in a session dictionary.
        @return pair:  session id associated with the secret,
                       string containing the secret
        ----
        the session dict is key'd by the session id
        and each node of the list is a (hashed secret, time of creation) pair
        """
        import random
        secret = hash(str(random.random()))

        sessionid = hash(str(time.time()) + str(self.id)).strip()
        # clear possibly old expired sessions
        self.request.cursor.execute(
            """DELETE from userSessions where user_id=%(id)s and
                                              expire_time<=%(timenow)s""",
            {'id':self.id, 'timenow':time.time()}, isWrite=True)
        # add our new session
        hash_secret = hash(secret)
        self.request.cursor.execute(
            """INSERT into userSessions (user_id, session_id, secret,
                                         expire_time)
               values (%(user_id)s, %(session_id)s, %(secret)s,
                       %(expiretime)s)""",
            {'user_id':self.id, 'session_id':sessionid, 'secret':hash_secret,
             'expiretime':expiretime}, isWrite=True)
        if config.memcache:
            key = "userSessions:%s,%s" % (self.id, sessionid)
            if self.remember_me:
                seconds_until_expire = 0
            else:
                seconds_until_expire = int(expiretime - now)
            self.request.mc.set(key, (hash_secret, expiretime),
                                time=seconds_until_expire, wiki_global=True)

        self.cookie_dough = (secret, expiretime, sessionid)

        return (sessionid, secret)
    
    def getUserIdDough(self, cookiestring):
        """
        return the user id from the cookie
        """
        return (cookiestring.split(','))[0]

    def isValidCookieDough(self, cookiestring):
        stored_secret = False
        split_string = cookiestring.split(',')
        if len(split_string) != 3:
            return False
        userid = split_string[0].strip()
        sessionid = split_string[1].strip()
        secret = split_string[2]
        if config.memcache:
            key = "userSessions:%s,%s" % (userid, sessionid)
            obj = self.request.mc.get(key, wiki_global=True)
            if obj:
               stored_secret, stored_expire_time = obj
        if not stored_secret:
            self.request.cursor.execute(
                """SELECT secret, expire_time from userSessions
                   where user_id=%(userid)s and session_id=%(sessionid)s and
                         expire_time>=%(timenow)s""",
                {'userid':userid, 'sessionid':sessionid,
                 'timenow':time.time()})
            result = self.request.cursor.fetchone()
            if result:
                stored_secret = result[0]
                stored_expire_time = result[1]
                if config.memcache:
                    if self.remember_me:
                        seconds_until_expire = 0
                    else:
                        seconds_until_expire = int(stored_expire_time -
                                                   time.time())

                    self.request.mc.add(key, (stored_secret,
                                              stored_expire_time),
                                        time=seconds_until_expire,
                                        wiki_global=True)

        if stored_secret and (stored_secret == hash(secret)):
            self.cookie_dough = (secret, stored_expire_time, sessionid)
            return True

        return False

    def clearNologinCookie(self, request):
        try:
            cookie = Cookie.SimpleCookie(request.saved_cookie)
        except Cookie.CookieError:
            # ignore invalid cookies, else user can't relogin
            cookie = None
        if cookie:
            if config.wiki_farm:
                cookie_id = wikiutil.quoteCookiename(config.wiki_base_domain + ',ID')
            else:
                cookie_id = wikiutil.quoteCookiename(config.sitename + ',ID')

            # kill possible old 'COOKIE_NOT_LOGGED_IN' cookies
            if cookie.has_key(COOKIE_NOT_LOGGED_IN):
                # clear out this cookie
                cookie_dir = config.web_dir
                if not cookie_dir: cookie_dir = '/'
                expirestr = time.strftime("%A, %d-%b-%Y %H:%M:%S GMT",
                                          time.gmtime(0))
                request.setHttpHeader(('Set-Cookie',
                                       '%s="%s"; '
                                       'domain=%s; path=%s; expires=%s' % (
                                            COOKIE_NOT_LOGGED_IN,
                                            cookie[COOKIE_NOT_LOGGED_IN].value,
                                            wikiutil.getCookieDomain(request),
                                            cookie_dir, expirestr)))

    def sendCookie(self, request, expire=None, sessionid=None, secret=None,
                   id=None):
        """
        Send the Set-Cookie header for this user.
        
        @param request: the request object
        """
        # prepare to send cookie
        cookie_header = self.makeCookieHeader(expire=expire,
                                              sessionid=sessionid,
                                              secret=secret, id=id)
        request.setHttpHeader(cookie_header)

        # create a "fake" cookie variable so the rest of the
        # code works as expected
        try:
            cookie = Cookie.SimpleCookie(request.saved_cookie)
        except Cookie.CookieError:
            # ignore invalid cookies, else user can't relogin
            request.saved_cookie = self.makeCookieDict(cookie_header)
        else:
            if config.wiki_farm:
                cookie_id = wikiutil.quoteCookiename(config.wiki_base_domain +
                                                     ',ID')
            else:
                cookie_id = wikiutil.quoteCookiename(config.sitename + ',ID')

            if not cookie.has_key(cookie_id):
                request.saved_cookie = self.makeCookieDict(cookie_header)

    def getTime(self, tm, global_time=False):
        """
        Get time in user's timezone.
        
        @param tm: time (UTC UNIX timestamp)
        @param global_time:  if True we output the server's time in the
                             server's default time zone
        @rtype: int
        @return: tm tuple adjusted for user's timezone
        """
        if not global_time: 
            return datetime.tmtuple(tm + self.tz_offset)
        else: 
            return datetime.tmtuple(tm + self.request.config.tz_offset)

    def getFormattedDate(self, tm):
        """
        Get formatted date adjusted for user's timezone.

        @param tm: time (UTC UNIX timestamp)
        @rtype: string
        @return: formatted date, see config.date_fmt
        """
        return time.strftime(config.date_fmt, self.getTime(tm))

    def getFormattedDateWords(self, tm):
        return time.strftime("%A, %B %d, %Y", self.getTime(tm))

    def getFormattedDateTime(self, tm, global_time=False):
        """
        Get formatted date and time adjusted for user's timezone.

        @param tm: time (UTC UNIX timestamp)
        @rtype: string
        @return: formatted date and time, see config.datetime_fmt
        """
        datetime_fmt = config.datetime_fmt
        return time.strftime(datetime_fmt, self.getTime(tm, global_time))

    def setShowComments(self, hideshow):
        """
        Set whether or not we show the comments on the RC page.

        @param tm: time (UTC UNIX timestamp), default: current time
        """
        if self.valid:
            bool_show= '1'
            if hideshow == 'showcomments':
                bool_show = 1
            elif hideshow == 'hidecomments':
                bool_show = 0
            self.rc_showcomments = bool_show
            self.request.cursor.execute(
                """UPDATE users set rc_showcomments=%(show_status)s
                   where id=%(userid)s""",
                {'show_status':bool_show, 'userid':self.id}, isWrite=True)
            if config.memcache:
                self.request.mc.set("users:%s" % self.id, self.getUserdict(),
                                    wiki_global=True)

    def getShowComments(self):
        """
        Get whether or not we show comments on the RC page.

        @rtype: int
        @return: bookmark time (UTC UNIX timestamp) or None
        """
        if self.valid:
            return self.rc_showcomments

        return 1

    def setRcGroupByWiki(self, group_by_wiki):
        """
        Sets whether or not we show the wikis on the
        interwiki recent changes page grouped by wiki or not.

        @param group_by_wiki: boolean -- True if we group by wiki.
        """
        if self.valid:
            self.rc_group_by_wiki = group_by_wiki
            self.request.cursor.execute(
                """UPDATE users SET rc_group_by_wiki=%(rc_group_by_wiki)s
                   where id=%(userid)s""",
                {'rc_group_by_wiki': group_by_wiki, 'userid':self.id},
                isWrite=True)
            if config.memcache:
                self.request.mc.set("users:%s" % self.id, self.getUserdict(),
                                    wiki_global=True)

    def getRcGroupByWiki(self):
        """
        Do we group changes on the interwiki recent changes page by wiki?

        @rtype: boolean
        @return: whether or not we group by wiki.
        """
        if self.valid:
            return self.rc_group_by_wiki

    def setBookmark(self, tm = None, wiki_global=False):
        """
        Set bookmark timestamp.
        
        @param tm: time (UTC UNIX timestamp), default: current time
        """
        if self.valid:
            if not wiki_global:
                self.request.cursor.execute(
                    """SELECT user_name from userWikiInfo
                       where user_name=%(user_name)s and
                              wiki_id=%(wiki_id)s""",
                    {'user_name':self.name,
                     'wiki_id':self.request.config.wiki_id})
                result = self.request.cursor.fetchone()
                if result and result[0]:
                    self.request.cursor.execute(
                        """UPDATE userWikiInfo set rc_bookmark=%(timenow)s
                           where user_name=%(user_name)s and
                                 wiki_id=%(wiki_id)s""",
                        {'timenow':tm, 'user_name':self.name,
                         'wiki_id':self.request.config.wiki_id},
                        isWrite=True)
                else:
                    self.request.cursor.execute(
                        """INSERT into userWikiInfo (user_name, wiki_id,
                                                     rc_bookmark)
                           values (%(username)s, %(wiki_id)s, %(timenow)s)""",
                        {'username':self.name,
                         'wiki_id':self.request.config.wiki_id, 'timenow':tm},
                        isWrite=True)

                if not self.wiki_info.has_key(self.request.config.wiki_id):
                    self.wiki_info[self.request.config.wiki_id] = \
                        self.getWikiInfo()
                self.wiki_info[self.request.config.wiki_id].rc_bookmark = tm

                if config.memcache:
                    self.request.mc.set("userWikiInfo:%s" % self.id,
                        self.wiki_info[self.request.config.wiki_id])
                self.save()
            else:
                self.rc_bookmark = tm
                self.save()

    def getBookmark(self, wiki_global=False):
        """
        Get recent changes bookmark timestamp.
        
        @rtype: int
        @return: bookmark time (UTC UNIX timestamp) or None
        """
        if self.valid:
            if not wiki_global:
                if not self.wiki_info.has_key(self.request.config.wiki_id):
                    self.wiki_info[self.request.config.wiki_id] = \
                        self.getWikiInfo()
                if self.wiki_info[self.request.config.wiki_id]:
                    return self.wiki_info[
                        self.request.config.wiki_id].rc_bookmark
            else:
              return self.rc_bookmark
        return None

    def getFavBookmark(self, page):
        """
        Get favorites bookmark timestamp.

        @rtype: float
        @return: bookmark time (UTC UNIX timestamp) or None
        """
        if not self.favorites:
            return
        if (self.favorites.has_key(page.wiki_name) and
            self.favorites[page.wiki_name].has_key(page.page_name)):
            return self.favorites[page.wiki_name][page.page_name]

    def delBookmark(self, wiki_global=False):
        """
        Removes recent changes bookmark timestamp.

        @rtype: int
        @return: None on success, True on failure
        """
        if self.valid:
            if not wiki_global:
                self.request.cursor.execute(
                    """UPDATE userWikiInfo set rc_bookmark=NULL
                       where user_name=%(user_name)s and
                             wiki_id=%(wiki_id)s""",
                    {'user_name':self.name,
                     'wiki_id':self.request.config.wiki_id}, isWrite=True)
                if self.wiki_info.has_key(self.request.config.wiki_id):
                    self.wiki_info[
                        self.request.config.wiki_id].rc_bookmark = None
                if config.memcache:
                    self.request.mc.set("users:%s" % self.id,
                                        self.getUserdict(), wiki_global=True)
                self.save()
                return None
            else:
                self.rc_bookmark = 0
                self.save()
            
        return True

    def _init_login(self):
      """
      Actions to be performed when an actual user logs in.
      """
      self.favorites = self.getFavorites()

    def getUserPages(self):
        """
        Get the list of wikis where this user has a page.
        """
        user_pages = self.user_pages
        if config.memcache and user_pages is None:
            user_pages = self.request.mc.get("user_pages:%s" % self.id,
                                             wiki_global=True)
        if user_pages is not None:
            return user_pages
        # grab the list of wikis from the database
        self.request.cursor.execute(
            """SELECT wiki_name FROM userPageOnWikis
               WHERE username=%(username)s""", {'username':self.name})
        result = self.request.cursor.fetchall()
        if result:
           user_pages = [i[0] for i in result] 
        else:
            user_pages = []
        
        if config.memcache:
            self.request.mc.add("user_pages:%s" % self.id, user_pages,
                                wiki_global=True)
        self.user_pages = user_pages
        return self.user_pages

    def addUserPage(self, wiki_name):
        """
        Adds the provided wiki_name to the list of user pages for this user.
        """
        user_pages = self.getUserPages()
        if wiki_name in user_pages:
            return
        user_pages.append(wiki_name)
        self.request.cursor.execute(
            """INSERT INTO userPageOnWikis (username, wiki_name) VALUES
               (%(username)s, %(wiki_name)s)""",
            {'username':self.name, 'wiki_name':wiki_name}, isWrite=True)
        if config.memcache:
            self.request.mc.set("user_pages:%s" % self.id, user_pages,
                                wiki_global=True)
        self.user_pages = user_pages

    def delUserPage(self, wiki_name):
        """
        Deletes the provided wiki_name from the list of user pages for this
        user.
        """
        user_pages = self.getUserPages()
        if wiki_name not in user_pages:
            return
        user_pages.remove(wiki_name)
        self.request.cursor.execute(
            """DELETE FROM userPageOnWikis WHERE
               username=%(username)s and wiki_name=%(wiki_name)s""",
            {'username':self.name, 'wiki_name':wiki_name}, isWrite=True)
        if config.memcache:
            self.request.mc.set("user_pages:%s" % self.id, user_pages,
                                wiki_global=True)
        self.user_pages = user_pages

    def getWatchedWikis(self, fresh=False):
        """
        Gets the list of wikis the user is watching.
        """
        watched = None
        if not self.valid:
           return {}
        if self.watched_wikis is not None:
            return self.watched_wikis
        if not fresh:
            if self.request.req_cache['watchedWikis'].has_key(self.id):
                return self.request.req_cache['watchedWikis'][self.id]
            if config.memcache:
                watched = self.request.mc.get('watchedWikis:%s' % self.id,
                                          wiki_global=True)
        if watched is None:
            watched = {}
            self.request.cursor.execute(
                """SELECT wiki_name from userWatchedWikis
                   where username=%(username)s order by wiki_name asc""",
                {'username': self.name})
            results = self.request.cursor.fetchall()
            if results:
                for result in results:
                    wiki_name = result[0] 
                    watched[wiki_name] = None
            if config.memcache:
                self.request.mc.add('watchedWikis:%s' % self.id, watched,
                                    wiki_global=True)
            self.request.req_cache['watchedWikis'][self.id] = watched
        
        return watched

    def setWatchedWikis(self, new_wiki_list):
        """
        Sets the user's wiki list to be the given wiki_list.
        """
        # ensure we have the list before proceeding
        currently_watched_wikis = self.getWatchedWikis(fresh=True) 
        wikis_to_add = []
        wikis_to_remove = copy(currently_watched_wikis)
        for wiki_name in new_wiki_list:
            if wiki_name in currently_watched_wikis:
                del wikis_to_remove[wiki_name]
                continue
            else:
                wikis_to_add.append(wiki_name)

        # write to DB
        d = {'user_name': self.name}
        for wiki_name in wikis_to_add:
            d['wiki_name'] = wiki_name
            self.request.cursor.execute(
                """INSERT into userWatchedWikis (username, wiki_name)
                   values (%(user_name)s, %(wiki_name)s)""", d, isWrite=True)
        for wiki_name in wikis_to_remove:
            d['wiki_name'] = wiki_name
            self.request.cursor.execute(
                """DELETE from userWatchedWikis
                   where username=%(user_name)s and wiki_name=%(wiki_name)s""",
                d, isWrite=True)

        new_wikis = {}
        for wiki_name in new_wiki_list:
            new_wikis[wiki_name] = None
        self.watched_wikis = new_wikis

        # set to cache
        self.request.req_cache['watchedWikis'][self.id] = self.watched_wikis
        if config.memcache:
            self.request.mc.set('watchedWikis:%s' % self.id,
                                self.watched_wikis, wiki_global=True)

    def isWatchingWiki(self, wikiname):
        return wikiname in self.getWatchedWikis()

    def getFavorites(self):
        """
        Gets the dictionary of user's favorites.
        Returns {wiki_name:{'pagename':viewTime}} dictionary
        """
        favs = None
        if self.request.req_cache['userFavs'].has_key(self.id):
            favs = self.request.req_cache['userFavs'][self.id]
            return favs
        if self.favorites is not None:
            return self.favorites
        if config.memcache:
            favs = self.request.mc.get("userFavs:%s" % self.id,
                                       wiki_global=True)
        if favs is None:
            favs = {}
            self.request.cursor.execute(
                """SELECT page, viewTime, wiki_name from userFavorites
                   where username=%(username)s order by page asc""",
                {'username': self.name})
            result = self.request.cursor.fetchall()
            if result:
                for pagename, viewTime, wiki_name in result:
                    if favs.has_key(wiki_name):
                        favs[wiki_name][pagename] = viewTime
                    else:
                        favs[wiki_name] = { pagename: viewTime }
            if config.memcache:
                self.request.mc.add("userFavs:%s" % self.id, favs,
                                    wiki_global=True)
            self.request.req_cache['userFavs'][self.id] = favs  
            
        return favs

    def getWikiInfo(self):
        """
        Gets the user's stored WikiInfo for a particular wiki, if they have it.
        """
        wiki_info = None
        if config.memcache:
            wiki_info = self.request.mc.get('userWikiInfo:%s' % self.id)
        if wiki_info is None:
            self.request.cursor.execute(
                """SELECT first_edit_date, created_count, edit_count,
                          file_count, last_page_edited, last_edit_date,
                          rc_bookmark from userWikiInfo
                   where user_name=%(username)s and wiki_id=%(wiki_id)s""",
                {'username':self.name, 'wiki_id':self.request.config.wiki_id})
            result = self.request.cursor.fetchone() 
            if result:
                values = result
            else:
                values = DEFAULT_WIKI_INFO_VALUES

            d = {'first_edit_date': values[0],
                 'created_count': values[1],
                 'edit_count': values[2],
                 'file_count': values[3],
                 'last_page_edited': values[4],
                 'last_edit_date': values[5],
                 'rc_bookmark': values[6]
                }
            wiki_info = WikiInfo(self, **d)
            if config.memcache:
               self.request.mc.add('userWikiInfo:%s' % self.id, wiki_info)

        return wiki_info

    def setWikiInfo(self, wiki_info):
        """
        Sets wiki info on the current wiki.

        NOTE: We assume that we are making an edit when we run this function.
        """
        d = copy(wiki_info.__dict__)
        d['username'] = self.name
        d['wiki_id'] = self.request.config.wiki_id
        self.request.cursor.execute(
            """SELECT first_edit_date from userWikiInfo
               where user_name=%(username)s and wiki_id=%(wiki_id)s""", d)
        result = self.request.cursor.fetchone()
        if result: # user info on this wiki exists
            self.request.cursor.execute(
                """UPDATE userWikiInfo set created_count=%(created_count)s,
                       edit_count=%(edit_count)s, file_count=%(file_count)s,
                       last_page_edited=%(last_page_edited)s,
                       last_edit_date=%(last_edit_date)s
                   where user_name=%(username)s and wiki_id=%(wiki_id)s""",
                d, isWrite=True)
        else: # no info exists
            self.request.cursor.execute(
                """INSERT into userWikiInfo (user_name, wiki_id,
                                             first_edit_date, created_count,
                                             edit_count, file_count,
                                             last_page_edited, last_edit_date)
                   values (%(username)s, %(wiki_id)s, %(last_edit_date)s,
                           %(created_count)s, %(edit_count)s, %(file_count)s,
                           %(last_page_edited)s, %(last_edit_date)s)""",
                d, isWrite=True)
        if config.memcache:
            self.request.mc.set('userWikiInfo:%s' % self.id, wiki_info)

    def hasUnseenFavorite(self, wiki_global=False):
        from Sycamore.Page import Page
        timenow = time.time()
        if self.valid:
            self.favorites = self.getFavorites()
            if not wiki_global:
                if self.favorites.has_key(self.request.config.wiki_name):
                    for pagename in self.favorites[
                        self.request.config.wiki_name]:
                        if (Page(pagename, self.request).mtime() >
                            self.favorites[self.request.config.wiki_name][
                                pagename]):
                            return True
                return False 
            else:
                for wiki_name in self.favorites:
                    for pagename in self.favorites[wiki_name]:
                        if (Page(pagename, self.request,
                                 wiki_name=wiki_name).mtime() >
                            self.favorites[wiki_name][pagename]):
                            return True
                return False 

    def hasUserPageChanged(self):
        """
        Has one of the user pages for this user been modified since it was
        last viewed?
        """
        from Sycamore.Page import Page
        user_pages = self.getUserPages()
        self.favorites = self.getFavorites()
        for wiki_name in user_pages:
            user_page_name = config.user_page_prefix.lower() + self.name
            if (self.favorites.has_key(wiki_name) and
                self.favorites[wiki_name].has_key(user_page_name)):
                if (Page(user_page_name, self.request,
                         wiki_name=wiki_name).mtime() >
                    self.favorites[wiki_name][user_page_name]):
                    return True
        return False

    def getFavoriteList(self, wiki_global=False):
        """
        Get list of pages this user has marked as a favorite
        sorted in alphabetical order.

        @rtype: list of page objects
        @return: pages this user has marked as favorites.
        """
        from Sycamore.Page import Page
        self.favorites = self.getFavorites()
        if not wiki_global:
            if self.favorites.has_key(self.request.config.wiki_name):
                return [Page(pagename, self.request) for pagename in
                    self.favorites[self.request.config.wiki_name].keys()] 
        else:
            favorites = []
            for wiki_name in self.favorites:
                for pagename in self.favorites[wiki_name]:
                    favorites.append(Page(pagename, self.request,
                                          wiki_name=wiki_name))
            return favorites
        return []


    def checkFavorites(self, page):
        """
        Checks to see if pagename is in the favorites list, and if it is,
        it updates the timestamp.
        """
        if self.request.req_cache['userFavs'].has_key(self.id):
            # sometimes there's more than one user object floating around
            # and so we want to make sure that, if we modified it elsewhere,
            # that we get the correct favorites
            # XXX HACKISH/poor form
            self.favorites = self.request.req_cache['userFavs'][self.id]
        if (self.name and self.favorites and
            self.favorites.has_key(page.wiki_name)):
          if self.favorites[page.wiki_name].has_key(page.page_name):
              # we have it as a favorite
              timenow = time.time()
              self.favorites[self.request.config.wiki_name][page.page_name] = \
                timenow
              if config.memcache:
                  self.request.mc.set('userFavs:%s' % self.id, self.favorites,
                                      wiki_global=True)
              self.request.cursor.execute(
                """UPDATE userFavorites set viewTime=%(timenow)s
                   where username=%(name)s and page=%(pagename)s and
                         wiki_name=%(wiki_name)s""",
                {'timenow':timenow, 'name':self.name,
                 'pagename':page.page_name, 'wiki_name':page.wiki_name},
                isWrite=True) 
          
    def isFavoritedTo(self, page):
        """
        Check if the page is a user's favorite       
 
        @param page: page to check for subscription
        @rtype: int
        @return: 1, if user has page in favorited pages ("Bookmarks")
                 0, if not
        """
        if self.name and not self.favorites:
            self.favorites = self.getFavorites()
        if self.valid:
            if (self.favorites.has_key(page.wiki_name) and
                self.favorites[page.wiki_name].has_key(page.page_name)):
                return True
        return False


    def favoritePage(self, page, by_user=True):
        """
        Favorite a wiki page.
        
        @param page: page to subscribe
        @rtype: bool
        @return: true, if page was NEWLY subscribed.
        """ 
        if self.valid and self.name and not self.favorites:
            self.favorites = self.getFavorites()
        if not self.isFavoritedTo(page):
            if by_user:
                timenow = time.time()
            else:
                timenow = 0
            if not self.favorites.has_key(page.wiki_name):
                self.favorites[page.wiki_name] = {}
            self.favorites[page.wiki_name][page.page_name] = timenow
            self.request.cursor.execute(
                """INSERT into userFavorites (page, username, viewTime,
                                              wiki_name)
                   values (%(pagename)s, %(name)s, %(timenow)s,
                           %(wiki_name)s)""",
                {'pagename':page.page_name, 'name':self.name,
                 'timenow':timenow, 'wiki_name':page.wiki_name}, isWrite=True)
            if config.memcache:
                self.request.mc.set("userFavs:%s" % self.id, self.favorites,
                                    wiki_global=True)
            return True

        return False


    def delFavorite(self, page):
        if self.valid and self.name and not self.favorites:
            self.favorites = self.getFavorites()
        if self.isFavoritedTo(page):
            del self.favorites[page.wiki_name][page.page_name]
            if config.memcache:
                self.request.mc.set("userFavs:%s" % self.id, self.favorites,
                                    wiki_global=True)
            self.request.cursor.execute(
                """DELETE from userFavorites where page=%(pagename)s and
                                                   username=%(username)s and
                                                   wiki_name=%(wiki_name)s""",
                {'pagename':page.page_name, 'username':self.name,
                 'wiki_name':page.wiki_name}, isWrite=True)
            self.request.req_cache['userFavs'][self.id] = self.favorites
            return True

        return False
