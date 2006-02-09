# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - User Accounts

    @copyright: 2000-2004 by J?rgen Hermann <jh@web.de>, 2005-2006 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, string, time, Cookie, sha, locale, pickle
from LocalWiki import config, wikiutil, wikidb
from LocalWiki.util import datetime
import xml.dom.minidom



#import sys

#############################################################################
### Helpers
#############################################################################

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
      all_ids.append(userid[0])
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
    if not searchName: return ''

    cursor = request.cursor
    id = ''
    if request.req_cache['users_id'].has_key(searchName):
      id = request.req_cache['users_id'][searchName]
      return id
    if not id and config.memcache:
      id = request.mc.get('users_id:%s' % searchName)
    if not id:
      cursor.execute("SELECT id from users where name=%(username)s", {'username':searchName})
      result = cursor.fetchone()
      if result:
        id = result[0]
        if config.memcache: request.mc.add('users_id:%s' % searchName, id)

    request.req_cache['users_id'][searchName] = id
    return id

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
    return base64.encodestring(sha.new(cleartext).digest()).rstrip()


#############################################################################
### User
#############################################################################

class User:
    """A LocalWiki User"""

    _checkbox_fields = [
         ('edit_on_doubleclick', lambda _: _('Open editor on double click')),
         ('remember_me', lambda _: _('Remember login information forever (so you don\'t have to keep logging in)')),
         ('disabled', lambda _: _('Disable this account forever')),
    ]
    _transient_fields =  ['id', 'valid', 'may', 'auth_username', 'trusted']
    _MAX_TRAIL = config.trail_size

    def __init__(self, request, id=None, name="", password=None, auth_username=""):
        """
        Initialize user object
        
        @param request: the request object
        @param id: (optional) user ID
        @param name: (optional) user name
        @param password: (optional) user password
        @param auth_username: (optional) already authenticated user name (e.g. apache basic auth)
        """
        self.valid = 0
        self.id = id
        if auth_username:
            self.auth_username = auth_username
        elif request:
            self.auth_username = request.auth_username
        else:
            self.auth_username = ""
        self.name = name
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
        self.favorited_pages = ""
        self.theme_name = config.theme_default
	self.tz_offset = config.tz_offset
	self.rc_bookmark = 0
	self.rc_showcomments = 1
	self.favorites = {}
	self.is_login = False
        # if an account is disabled, it may be used for looking up
        # id -> username for page info and recent changes, but it
        # is not usabled for the user any more:
        # self.disabled   = 0
        # is handled by checkbox now.
        
        # attrs not saved to profile
        self.request = request
        self._trail = []

        # create checkbox fields (with default 0)
        for key, label in self._checkbox_fields:
            setattr(self, key, 0)

        self.remember_me = 1

        if not self.auth_username and not self.id:
            try:
                cookie = Cookie.SimpleCookie(request.saved_cookie)
            except Cookie.CookieError:
                # ignore invalid cookies, else user can't relogin
                cookie = None
            if cookie and cookie.has_key(wikiutil.quoteFilename(config.sitename)+'ID'):
		# does their cookie pass our super elite test?
		if self.isValidCookieDough(cookie[wikiutil.quoteFilename(config.sitename)+'ID'].value):
			# okay, lets let them in
       	        	self.id = self.getUserIdDough(cookie[wikiutil.quoteFilename(config.sitename)+'ID'].value)
			self.is_login = True
			

        # we got an already authenticated username:
        if not self.id and self.auth_username:
            self.id = getUserId(self.auth_username, self.request)

        if self.id:
            self.load_from_id()
            if self.name == self.auth_username:
                self.trusted = 1
        elif self.name:
            self.load()
            
        # "may" so we can say "if user.may.edit(pagename):"
        if config.SecurityPolicy:
            self.may = config.SecurityPolicy(self)
        else:
            from security import Default
            self.may = Default(self)

	if self.is_login:
	  self._init_login()


#    def __filename(self):
#        """
#        get filename of the user's file on disk
#        @rtype: string
#        @return: full path and filename of user account file
#        """
#        return os.path.join(config.user_dir, self.id or "...NONE...")


    def exists(self):
        """
        Do we have a user account for this user?
        
        @rtype: bool
        @return: true, if we have a user account
        """
	result = False
	if self.request.req_cache['users'].has_key(self.id):
	  result = self.request.req_cache['users'][self.id]
	if not result:
	  if config.memcache:
	    result = self.request.mc.get('users:%s' % self.id)
	  if not result:
	    self.request.cursor.execute("SELECT name, email, enc_password, language, remember_me, css_url, disabled, edit_cols, edit_rows, edit_on_doubleclick, theme_name, last_saved, tz_offset, rc_bookmark from users where id=%(userid)s", {'userid':self.id})
	    data = self.request.cursor.fetchone()
	    if data:
              user_data = {'enc_password': ''}
              user_data['name'] = data[0] 
	      user_data['email'] = data[1]
	      user_data['enc_password'] = data[2]
	      user_data['language'] = data[3]
	      user_data['remember_me'] = data[4]
	      user_data['css_url'] = data[5]
	      user_data['disabled'] = data[6]
	      user_data['edit_cols'] = data[7]
	      user_data['edit_rows'] = data[8]
	      user_data['edit_on_doubleclick'] = data[9]
	      user_data['theme_name'] = data[10]
	      user_data['last_saved'] = data[11]
	      user_data['tz_offset'] = data[12]
	      user_data['rc_bookmark'] = data[13]
	      result = user_data
	      if config.memcache: self.request.mc.add('users:%s' % self.id, result)

          self.request.req_cache['users'][self.id] = result
	  
	if result: return True
	return False

    def load(self):
        """
        Lookup user ID by user name and load user account.

        Can load user data if the user name is known, but only if the password is set correctly.
        """
        self.id = getUserId(self.name, self.request)
        if self.id:
            self.load_from_id(1)
        #print >>sys.stderr, "self.id: %s, self.name: %s" % (self.id, self.name)
        
    def load_from_id(self, check_pass=0):
        """
        Load user account data from disk.

        Can only load user data if the id number is already known.

        This loads all member variables, except "id" and "valid" and
        those starting with an underscore.
        
        @param check_pass: If 1, then self.enc_password must match the
                           password in the user account file.
        """
        if not self.exists(): return

        # XXX UNICODE fix needed, we want to read utf-8 and decode to unicode
	user_data = False
	if self.request.req_cache['users'].has_key(self.id):
	  user_data = self.request.req_cache['users'][self.id]
	if not user_data:
	  if config.memcache:
	    user_data = self.request.mc.get('users:%s' % self.id)
	  if not user_data:
	    self.request.cursor.execute("SELECT name, email, enc_password, language, remember_me, css_url, disabled, edit_cols, edit_rows, edit_on_doubleclick, theme_name, last_saved, tz_offset, rc_bookmark, rc_showcomments from users where id=%(userid)s", {'userid':self.id})
	    data = self.request.cursor.fetchone()

            user_data = {'enc_password': ''}
            user_data['name'] = data[0] 
	    user_data['email'] = data[1]
	    user_data['enc_password'] = data[2]
	    user_data['language'] = data[3]
	    user_data['remember_me'] = data[4]
	    user_data['css_url'] = data[5]
	    user_data['disabled'] = data[6]
	    user_data['edit_cols'] = data[7]
	    user_data['edit_rows'] = data[8]
	    user_data['edit_on_doubleclick'] = data[9]
	    user_data['theme_name'] = data[10]
	    user_data['last_saved'] = data[11]
	    user_data['tz_offset'] = data[12]
	    user_data['rc_bookmark'] = data[13]
	    user_data['rc_showcomments'] = data[14]

	    if config.memcache: self.request.mc.add('users:%s' % self.id, user_data)

	  self.request.req_cache['users'][self.id] = user_data

        if check_pass:
            # If we have no password set, we don't accept login with username
            if not user_data['enc_password']:
                return
            # Check for a valid password
            elif user_data['enc_password'] != self.enc_password:
                # print >>sys.stderr, "File:%s Form:%s" % (user_data['enc_password'], self.enc_password)
                return
            else:
                self.trusted = 1

        # Copy user data into user object
        for key, val in user_data.items():
            vars(self)[key] = val

        # old passwords are untrusted
        if hasattr(self, 'password'): del self.password
        if hasattr(self, 'passwd'): del self.passwd

        # make sure checkboxes are boolean
        for key, label in self._checkbox_fields:
            try:
                setattr(self, key, int(getattr(self, key)))
            except ValueError:
                setattr(self, key, 0)

        # convert (old) hourly format to seconds
        #if -24 <= self.tz_offset and self.tz_offset <= 24:
        #    self.tz_offset = self.tz_offset * 3600

        # clear trail
        self._trail = []

        if not self.disabled:
            self.valid = 1

    def _new_user_id(self):
      # Generates a new and unique user id
      from random import randint
      id = "%s.%d" % (str(time.time()), randint(0,65535))
      # check to make sure the id is unique (we could, after all, change our user id scheme at some point..)
      self.request.cursor.execute("SELECT id from users where id=%(userid)s", {'userid':id})
      result = self.request.cursor.fetchone()
      while result:
        # means it's not unique, so let's try another
        id = "%s.%d" % (str(time.time()), randint(0,65535))
	self.request.cursor.execute("SELECT id from users where id=%(userid)s", {'userid':id})
        result = self.request.cursor.fetchone()
      return id

    def getUserdict(self):
       #Returns dictionary of all relevant user values -- essentially an entire user's relevant information
	return {'id':self.id, 'name':self.name, 'email':self.email, 'enc_password':self.enc_password, 'language':self.language, 'remember_me': str(self.remember_me), 'css_url':self.css_url, 'disabled':str(self.disabled), 'edit_cols':self.edit_cols, 'edit_rows':self.edit_rows, 'edit_on_doubleclick':str(self.edit_on_doubleclick), 'theme_name':self.theme_name, 'last_saved':self.last_saved, 'tz_offset':self.tz_offset, 'rc_bookmark': self.rc_bookmark, 'rc_showcomments': self.rc_showcomments}


    def save(self):
        """
        Save user account data to user account file on disk.

        This saves all member variables, except "id" and "valid" and
        those starting with an underscore.
        """
        self.last_saved = str(time.time())

        userdict = self.getUserdict()

        if not self.id:
	  self.id = self._new_user_id()
 	  # account doesn't exist yet
	  userdict['join_date'] = time.time()
	  userdict['id'] = self.id
	  self.request.cursor.execute("INSERT into users (id, name, email, enc_password, language, remember_me, css_url, disabled, edit_cols, edit_rows, edit_on_doubleclick, theme_name, last_saved, join_date, tz_offset) values (%(id)s, %(name)s, %(email)s, %(enc_password)s, %(language)s, %(remember_me)s, %(css_url)s, %(disabled)s, %(edit_cols)s, %(edit_rows)s, %(edit_on_doubleclick)s, %(theme_name)s, %(last_saved)s, %(join_date)s, %(tz_offset)s)", userdict)
	  if config.memcache:
	    self.request.mc.set("users:%s" % self.id, userdict)
	else:
	  self.request.cursor.execute("UPDATE users set id=%(id)s, name=%(name)s, email=%(email)s, enc_password=%(enc_password)s, language=%(language)s, remember_me=%(remember_me)s, css_url=%(css_url)s, disabled=%(disabled)s, edit_cols=%(edit_cols)s, edit_rows=%(edit_rows)s, edit_on_doubleclick=%(edit_on_doubleclick)s, theme_name=%(theme_name)s, last_saved=%(last_saved)s, tz_offset=%(tz_offset)s where id=%(id)s", userdict)
	  if config.memcache:
	    self.request.mc.set("users:%s" % self.id, userdict)
		
    def makeCookieHeader(self):
        """
        Make the Set-Cookie header for this user
            
        uses: config.cookie_lifetime (int) [hours]
            == 0  --> cookie will live forever (no matter what user has configured!)
            > 0   --> cookie will live for n hours (or forever when "remember_me")
            < 0   --> cookie will live for -n hours (forced, ignore "remember_me"!)
        """
	forever = 10*365*24*3600 # 10 years, after this time the polar icecaps will have melted anyway
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

        # XXX maybe better make this a critical section for persistent environments!?
        loc=locale.setlocale(locale.LC_TIME, 'C')
        expirestr = time.strftime("%A, %d-%b-%Y %H:%M:%S GMT", time.gmtime(expire))
        locale.setlocale(locale.LC_TIME, loc)

        cookie = Cookie.SimpleCookie()
	sessionid, secret = self.cookieDough(expire, now)
        cookie[wikiutil.quoteFilename(config.sitename)+'ID'] = self.id + ',' + sessionid + ',' + secret
	cookie_dir = config.web_dir
	if not cookie_dir: cookie_dir = '/'
        return "%s expires=%s;host=%s;Path=%s" % (cookie.output(), expirestr, config.domain, cookie_dir)


    def cookieDough(self, expiretime, now):
	"""
	Creates a session-specific secret that is stored in the user's cookie.
	Stores a hashed version of of this secret in a session dictionary.
	@return pair:  session id associated with the secret, string containing the secret
	----
	the session dict is key'd by the session id
	  and each node of the list is a (hashed secret, time of creation) pair
	"""
	import random, cPickle
	secret = hash(str(random.random()))

	sessionid = hash(str(time.time()) + str(self.id))
	# clear possibly old expired sessions
	self.request.cursor.execute("DELETE from userSessions where user_id=%(id)s and expire_time>=%(timenow)s", {'id':self.id, 'timenow':time.time()})
	# add our new session
	hash_secret = hash(secret)
	self.request.cursor.execute("INSERT into userSessions (user_id, session_id, secret, expire_time) values (%(user_id)s, %(session_id)s, %(secret)s, %(expiretime)s)", {'user_id':self.id, 'session_id':sessionid, 'secret':hash_secret, 'expiretime':expiretime})
	if config.memcache:
	  key = "userSessions:%s,%s" % (self.id, sessionid)
	  if self.remember_me:
	    seconds_until_expire = 0
	  else:
	    seconds_until_expire = int(expiretime - now)
	  self.request.mc.set(key, hash_secret, time=seconds_until_expire)

	return (sessionid, secret)
    
    def getUserIdDough(self, cookiestring):
	"""
	return the user id from the cookie
	"""
	return (cookiestring.split(','))[0]

    def isValidCookieDough(self, cookiestring):
        stored_secret = False
	split_string = cookiestring.split(',')
	userid = split_string[0]
	sessionid = split_string[1]
	secret = split_string[2]
	if config.memcache:
	  key = "userSessions:%s,%s" % (userid, sessionid)
	  stored_secret = self.request.mc.get(key)
	if not stored_secret:
	  self.request.cursor.execute("SELECT secret, expire_time from userSessions where user_id=%(userid)s and session_id=%(sessionid)s and expire_time>=%(timenow)s", {'userid':userid, 'sessionid':sessionid, 'timenow':time.time()})
	  result = self.request.cursor.fetchone()
	  if result:
	    stored_secret = result[0]
	    stored_expiretime = result[1]
	    if config.memcache:
	      if self.remember_me:
	        seconds_until_expire = 0
	      else:
	        seconds_until_expire = int(stored_expiretime - time.time())

	      self.request.mc.add(key, stored_secret, time=seconds_until_expire)

	if stored_secret and (stored_secret == hash(secret)):
	  return True

	return False
	
    def sendCookie(self, request):
        """
        Send the Set-Cookie header for this user.
        
        @param request: the request object
        """
        # prepare to send cookie
	cookie_header = self.makeCookieHeader()
        request.setHttpHeader(cookie_header)

        # create a "fake" cookie variable so the rest of the
        # code works as expected
        try:
            cookie = Cookie.SimpleCookie(request.saved_cookie)
        except Cookie.CookieError:
            # ignore invalid cookies, else user can't relogin
            request.saved_cookie = cookie_header
        else:
            if not cookie.has_key(wikiutil.quoteFilename(config.sitename)+'ID'):
                request.saved_cookie = cookie_header


    def getTime(self, tm, global_time=False):
        """
        Get time in user's timezone.
        
        @param tm: time (UTC UNIX timestamp)
	@param global_time:  if True we output the server's time in the server's default time zone
        @rtype: int
        @return: tm tuple adjusted for user's timezone
        """
        if self.tz_offset and not global_time: return datetime.tmtuple(tm + self.tz_offset)
	else: return datetime.tmtuple(tm + config.tz_offset)


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
	    if hideshow == 'showcomments' : bool_show = 1
	    elif hideshow == 'hidecomments' : bool_show = 0
	    self.rc_showcomments = bool_show
	    self.request.cursor.execute("UPDATE users set rc_showcomments=%(show_status)s where id=%(userid)s", {'show_status':bool_show, 'userid':self.id})
	    if config.memcache:
	      self.request.mc.set("users:%s" % self.id, self.getUserdict())

    def getShowComments(self):
        """
        Get whether or not we show comments on the RC page.

        @rtype: int
        @return: bookmark time (UTC UNIX timestamp) or None
        """
        if self.valid:
	  return self.rc_showcomments

        return 1

    def setBookmark(self, tm = None):
        """
        Set bookmark timestamp.
        
        @param tm: time (UTC UNIX timestamp), default: current time
        """
        if self.valid:
            if not tm: tm = time.time()
	    self.request.cursor.execute("UPDATE users set rc_bookmark=%(timenow)s where id=%(userid)s", {'timenow':str(tm), 'userid':self.id})
	    self.rc_bookmark = tm
	    if config.memcache:
	      self.request.mc.set("users:%s" % self.id, self.getUserdict())


    def getBookmark(self):
        """
        Get recent changes bookmark timestamp.
        
        @rtype: int
        @return: bookmark time (UTC UNIX timestamp) or None
        """
        if self.valid: return self.rc_bookmark
        return None


    def getFavBookmark(self, pagename):
        """
        Get favorites bookmark timestamp.

        @rtype: int
        @return: bookmark time (UTC UNIX timestamp) or None
        """
        #if self.valid and os.path.exists(self.__filename() + ".favbookmark"):
        #    try:
        #        return int(open(self.__filename() + ".favbookmark", 'r').readline())
        #    except (OSError, ValueError):
        #        return None
        #return None
        #index = string.find(self.favorited_pages, pagename + "*")
        #return int(self.favorited_pages[index + len(pagename + "*"):index + 10 + len(pagename + "*")])
        #import re
        #from LocalWiki import wikiutil
	if self.favorites.has_key(pagename):
	  return self.favorites[pagename]
	else: return None

    def delBookmark(self):
        """
        Removes recent changes bookmark timestamp.

        @rtype: int
        @return: 0 on success, 1 on failure
        """
        if self.valid:
	   self.request.cursor.execute("UPDATE users set rc_bookmark=NULL where id=%(id)s", {'id':self.id})
	   self.rc_bookmark = 0
	   if config.memcache:
	     self.request.mc.set("users:%s" % self.id, self.getUserdict())
	   return 0
	    
        return 1

    #def delFavBookmark(self):
    #    """
    #    Removes favorites bookmark timestamp.
#
#        @rtype: int
#        @return: 0 on success, 1 on failure
#        """
#        if self.valid:
#            if os.path.exists(self.__filename() + ".favbookmark"):
#                try:
#                    os.unlink(self.__filename() + ".favbookmark")
#                except OSError:
#                    return 1
#            return 0
#        return 1

#    def getQuickLinks(self):
#        """
#        Get list of pages this user wants in the page header.
#
#        @rtype: list
#        @return: quicklinks from user account
#        """
#        if not self.quicklinks: return []
#
#        from LocalWiki import wikiutil
#        quicklinks = self.quicklinks.split(',')
#        quicklinks = map(string.strip, quicklinks)
#        quicklinks = filter(None, quicklinks)
#        quicklinks = map(wikiutil.unquoteWikiname, quicklinks)
#        return quicklinks


#    def getSubscriptionList(self):
#        """
#        Get list of pages this user has subscribed to.
#        
#        @rtype: list
#        @return: pages this user has subscribed to
#        """
#        subscrPages = self.subscribed_pages.split(",")
#        subscrPages = map(string.strip, subscrPages)
#        subscrPages = filter(None, subscrPages)
#        return subscrPages

    def _init_login(self):
      """
      Actions to be performed when an actual user logs in.
      """
      self.favorites = self.getFavorites()

    def getFavorites(self):
        """
	Gets the dictionary of user's favorites.
	"""
	favs = {}
	if self.favorites: return self.favorites
        if self.request.req_cache['userFavs'].has_key(self.id):
	  favs = self.request.req_cache['userFavs'][self.id]
	  return favs
	if config.memcache:
	  favs = self.request.mc.get("userFavs:%s" % self.id)
	  self.request.req_cache['userFavs'][self.id] = favs  
	if not favs:
	  favs = {}
	  self.request.cursor.execute("SELECT page, viewTime from userFavorites where username=%(username)s", {'username': self.name})
	  result = self.request.cursor.fetchall()
	  if result:
	    for pagename, viewTime in result:
	      favs[pagename] = viewTime
	  if config.memcache:
	    self.request.mc.add("userFavs:%s" % self.id, favs)
	  self.request.req_cache['userFavs'][self.id] = favs  
	    
	return favs


    def getFavoriteList(self):
        """
        Get list of pages this user has marked as a favorite sorted in alphabetical order.

        @rtype: list
        @return: pages this user has marked as favorites.
        """
	return self.favorites.keys().sort()


    def checkFavorites(self, pagename):
        """
        Checks to see if pagename is in the favorites list, and if it is, it updates the timestamp.
        """
        if self.name and self.favorites:
	  if self.favorites.has_key(pagename):
          # we have it as a favorite
	    timenow = time.time()
	    self.favorites[pagename] = timenow
	    if config.memcache:
	      self.request.mc.set('userFavs:%s' % self.id, self.favorites)
	    self.request.cursor.execute("UPDATE userFavorites set viewTime=%(timenow)s where username=%(name)s and page=%(pagename)s", {'timenow':timenow, 'name':self.name, 'pagename':pagename}) 
 	  

    def isFavoritedTo(self, pagename):
        """
        Check if the page is a user's favorite       
 
        @param page: page to check for subscription
        @rtype: int
        @return: 1, if user has page in favorited pages ("Bookmarks")
                 0, if not
        """
        if self.valid and self.name and not self.favorites: self.favorites = self.getFavorites()
        if self.valid:
	  if self.favorites.has_key(pagename):
	    return True
	return False

#    def isSubscribedTo(self, pagelist):
#        """
#        Check if user subscription matches any page in pagelist.
#        
#        @param pagelist: list of pages to check for subscription
#        @rtype: int
#        @return: 1, if user has subscribed any page in pagelist
#                 0, if not
#        """
#        import re
#
#        matched = 0
#        if self.valid:
#            pagelist_lines = '\n'.join(pagelist)
#            for pattern in self.getSubscriptionList():
#                # check if pattern matches one of the pages in pagelist
#                matched = pattern in pagelist
#                if matched: break
#                try:
#                    rexp = re.compile("^"+pattern+"$", re.M)
#                except re.error:
#                    # skip bad regex
#                    continue
#                matched = rexp.search(pagelist_lines)
#                if matched: break
#        if matched:
#            return 1
#        else:
#            return 0
#
#
#    def subscribePage(self, pagename):
#        """
#        Subscribe to a wiki page.
#
#        Note that you need to save the user data to make this stick!
#
#        @param pagename: name of the page to subscribe
#        @rtype: bool
#        @return: true, if page was NEWLY subscribed.
#        """
#        subscrPages = self.getSubscriptionList()
#
#        # add page to subscribed pages property
#        if pagename not in subscrPages: 
#            subscrPages.append(pagename)
#            self.subscribed_pages = ','.join(subscrPages)
#            return 1
#
#        return 0

    def favoritePage(self, pagename):
        """
        Favorite a wiki page.
        
        @param pagename: name of the page to subscribe
        @rtype: bool
        @return: true, if page was NEWLY subscribed.
        """ 
        if self.valid and self.name and not self.favorites: self.favorites = self.getFavorites()
	if not self.isFavoritedTo(pagename):
	  timenow = time.time()
	  self.favorites[pagename] = timenow
	  self.request.cursor.execute("INSERT into userFavorites (page, username, viewTime) values (%(pagename)s, %(name)s, %(timenow)s)", {'pagename':pagename, 'name':self.name, 'timenow':timenow})
	  if config.memcache:
	    self.request.mc.set("userFavs:%s" % self.id, self.favorites)
	  return True

        return False


    def delFavorite(self, pagename):
        if self.valid and self.name and not self.favorites: self.favorites = self.getFavorites()
	if self.isFavoritedTo(pagename):	
	   del self.favorites[pagename]
	   if config.memcache:
	     self.request.mc.set("userFavs:%s" % self.id, self.favorites)
	   self.request.cursor.execute("DELETE from userFavorites where page=%(pagename)s and username=%(username)s", {'pagename':pagename, 'username':self.name})
           return True

        return False


    def addTrail(self, pagename):
        """
        Add page to trail.
        
        @param pagename: the page name to add to the trail
        """
        if self.valid:
            # load trail if not known
            self.getTrail()      
            
            # don't append tail to trail ;)
            if self._trail and self._trail[-1] == pagename: return

            # append new page, limiting the length
            self._trail = filter(lambda p, pn=pagename: p != pn, self._trail)
            self._trail = self._trail[-(self._MAX_TRAIL-1):]
            self._trail.append(pagename)

            # save new trail
            # XXX UNICODE fix needed, encode as utf-8
            trailfile = open(self.__filename() + ".trail", "w")
            trailfile.write('\n'.join(self._trail))
            trailfile.close()
            try:
                os.chmod(self.__filename() + ".trail", 0666 & config.umask)
            except OSError:
                pass


    def getTrail(self):
        """
        Return list of recently visited pages.
        
        @rtype: list
        @return: pages in trail
        """
        if self.valid \
                and not self._trail \
                and os.path.exists(self.__filename() + ".trail"):
            try:
                # XXX UNICODE fix needed, decode from utf-8
                self._trail = open(self.__filename() + ".trail", 'r').readlines()
            except (OSError, ValueError):
                self._trail = []
            else:
                self._trail = filter(None, map(string.strip, self._trail))
                self._trail = self._trail[-self._MAX_TRAIL:]
        return self._trail

