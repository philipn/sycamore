# -*- coding: iso-8859-1 -*-
"""
    Sycamore - User Account Maintenance

    @copyright: 2005-2006 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import string, time, re, Cookie, random, urllib, locale
from copy import copy
from Sycamore import config, user, util, wikiutil, wikidb, farm
from Sycamore.Page import Page
import Sycamore.util.web
import Sycamore.util.mail
import Sycamore.util.datetime
from Sycamore.widget import html
from Sycamore.wikiaction import NOT_ALLOWED_CHARS
USER_NOT_ALLOWED_CHARS = NOT_ALLOWED_CHARS + '/:'

#import pytz from support
import sys, os.path
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, 'support'))])
import pytz

_debug = 0


#############################################################################
### Form POST Handling
#############################################################################

def savedata(request):
    """ Handle POST request of the user preferences form.

    Return error msg or None.  
    """
    return UserSettingsHandler(request).handleData()

class BadData(Exception): 
    pass

class UserSettingsHandler(object):

    def __init__(self, request):
        """ Initialize user settings form. """
        self.request = request
        self._ = request.getText


    def removeSession(self, cookiestring):
        # sane cookie check
        string_split = cookiestring.split(',')
        cookie_userid = string_split[0]
        cookie_sessionid = string_split[1]
        cookie_secret = string_split[2]
        if config.memcache:
          key = "userSessions:%s,%s" % (cookie_userid,cookie_sessionid)
          obj = self.request.mc.get(key, wiki_global=True)
          if obj:
            stored_secret, expiretime = obj
            # make sure they aren't just getting lucky with a fake cookie
            if stored_secret and (stored_secret == user.hash(cookie_secret)):
              self.request.mc.delete(key, wiki_global=True)
        self.request.cursor.execute("DELETE from userSessions where user_id=%(cookie_userid)s and session_id=%(cookie_sessionid)s and secret=%(cookie_secret)s", {'cookie_userid':cookie_userid, 'cookie_sessionid':cookie_sessionid, 'cookie_secret':user.hash(cookie_secret)}, isWrite=True)

    def _clear_all_sessions_except_current(self):
        current_session = self.request.user.cookie_dough[2]
        results = []
        if config.memcache:
            self.request.cursor.execute("SELECT session_id from userSessions where user_id=%(user_id)s and session_id != %(current_session)s", {'user_id':self.request.user.id, 'current_session':current_session})
            results = self.request.cursor.fetchall()
        self.request.cursor.execute("DELETE from userSessions where user_id=%(user_id)s and session_id != %(current_session)s", {'user_id':self.request.user.id, 'current_session':current_session}, isWrite=True)
        # clear from memcache
        for session in results:
            session_id = session[0]
            self.request.mc.delete("userSessions:%s,%s" % (self.request.user.id, session_id))


    def isValidCode(self, given_uid, given_code):
        state = False
        timenow = time.time()
        d = {'uid':given_uid, 'code':given_code, 'wiki_id':self.request.config.wiki_id, 'timevalid': (timenow-60*30)}
        self.request.cursor.execute("SELECT written_time from lostPasswords where code=%(code)s and uid=%(uid)s and written_time > %(timevalid)s", d)
        result = self.request.cursor.fetchone()
        if result and result[0]:
            state = True
            self.request.cursor.execute("DELETE from lostPasswords where uid=%(uid)s", d, isWrite=True)
        return state
                
    def createCode(self, userid):
        ourcode = str(random.random())
        code = ourcode
        written_time = time.time()
        d = {'uid':userid, 'code':code, 'written_time':written_time}
        self.request.cursor.execute("INSERT into lostPasswords (uid, code, written_time) values (%(uid)s, %(code)s, %(written_time)s)", d, isWrite=True)

        return ourcode


    def handleData(self, new_user=None):
        from Sycamore.Page import MAX_PAGENAME_LENGTH as MAX_USERNAME_LENGTH
        _ = self._
        form = self.request.form
        msg = ''
    
        isdisabled = False
        if form.get('disabled', [0])[0] == '1':
                isdisabled = True

        self.from_wiki = None
        if self.request.form.has_key('from_wiki'):
          self.from_wiki = self.request.form['from_wiki'][0].lower().strip()
          if not wikiutil.isInFarm(self.from_wiki, self.request):
            self.from_wiki = None

        new_user = int(form.get('new_user', [0])[0])
        # wiki farm authentication

        # we want them to be able to sign back in right after they click the 'logout' GET link, hence this test
        is_form_logout = (form.has_key('qs') and 
                          urllib.unquote(form['qs'][0]) == 'action=userform&logout=Logout')

        if self.request.form.has_key('badlogin') and self.request.form['badlogin'][0]:
            _create_nologin_cookie(self.request)
            if config.wiki_farm:
                wiki_base_url = farm.getBaseFarmURL(self.request)
            else:
                wiki_base_url = '%s/' % self.request.getScriptname()
    
            return_string = """
Unknown username or wrong password.<br /><br />New user?  <a href="%s%s?new_user=1">Click here to create an account!</a><br /><br />Forgot your password?  We'll email it to you.
<form action="%s" method="POST"><input type="hidden" name="action" value="userform">
Email address: <input class="formfields" type="text" name="email">&nbsp;<input type="submit" class="formbutton" name="login_sendmail" value="Mail me my account data">
</form>
""" % (wiki_base_url, wikiutil.quoteWikiname(config.page_user_preferences), wiki_base_url)
            return return_string


        if form.has_key('login_check') and form['login_check'][0] and form.has_key('backto_wiki') and form.has_key('backto_page'):
            backto_wiki = form['backto_wiki'][0]
            backto_page = form['backto_page'][0].encode(config.charset)
            if form.has_key('qs') and not is_form_logout:
                q_query_string = form['qs'][0]
            else:
                q_query_string = ''

            if self.request.user.valid:
                secret, stored_expire_time, session = self.request.user.cookie_dough
                if q_query_string:
                    url = '%s?action=userform&backto_page=%s&qs=%s&secret=%s&expire_time=%s&uid=%s&session=%s' % (backto_page,
                        urllib.quote(backto_page), urllib.quote(q_query_string), urllib.quote(secret), stored_expire_time, self.request.user.id, urllib.quote(session))
                else:
                     url = '%s?action=userform&backto_page=%s&secret=%s&expire_time=%s&uid=%s&session=%s' % (backto_page,
                        urllib.quote(backto_page), urllib.quote(secret), stored_expire_time, self.request.user.id, urllib.quote(session))
            else:
                if q_query_string:
                    url = '%s?action=userform&backto_page=%s&not_logged_in=1&qs=%s' % (backto_page, urllib.quote(backto_page), urllib.quote(q_query_string))
                else:
                     url = '%s?action=userform&backto_page=%s&not_logged_in=1' % (backto_page, urllib.quote(backto_page))

            self.request.http_redirect(url) 
            return 

        # bounce-back wiki farm authentication
        if form.has_key('not_logged_in') and form.has_key('backto_page'):
            backto = urllib.unquote(form['backto_page'][0].encode(config.charset))
            if form.has_key('qs') and not is_form_logout:
                query_string = '?%s' % urllib.unquote(form['qs'][0])
            else:
                query_string = ''
            url = '%s%s' % (backto, query_string)
            _create_nologin_cookie(self.request)
            self.request.http_redirect(url)
            return
        # bounce-back wiki farm authentication
        elif form.has_key('uid') and form.has_key('secret') and form.has_key('session') and form.has_key('expire_time'):
            uid = form['uid'][0]
            secret = urllib.unquote(form['secret'][0])
            session = form['session'][0]
            expire_time = float(form['expire_time'][0])
            if form.has_key('backto_page'):
                backto_page = form['backto_page'][0]
            else:
                backto_page = '/' 
            if form.has_key('qs') and not is_form_logout:
                query_string = '?%s' % urllib.unquote(form['qs'][0])
            else:
                query_string = ''
            url = '%s%s' % (backto_page, query_string)
    
            self.request.http_redirect(url)
            self.request.user.sendCookie(self.request, expire=expire_time, sessionid=session, secret=secret, id=uid) 
            self.request.user.clearNologinCookie(self.request)
            return 

        if form.has_key('logout') or isdisabled:
            msg = ''
            if isdisabled:
                if not self.request.isPOST():
                    return """Use the interactive interface to change settings!"""
                # disable the account
                self.request.user.disabled = 1
                # save user's profile
                self.request.user.save()
                msg = '<p>%s</p>' % _("Your account has been disabled.")

            # clear the cookie in the browser and locally
            try:
                cookie = Cookie.SimpleCookie(self.request.saved_cookie)
            except Cookie.CookieError:
                # ignore invalid cookies
                cookie = None
            else:
                if config.wiki_farm:
                    cookie_id = wikiutil.quoteCookiename(config.wiki_base_domain + ',ID')
                else:
                    cookie_id = wikiutil.quoteCookiename(config.sitename + ',ID')

                if cookie.has_key(cookie_id):
                    self.removeSession(cookie[cookie_id].value)
                    #not sure why this uid line is here..
                    #uid = cookie[wikiutil.quoteFilename(config.sitename)+'ID'].value
                    cookie_dir = config.web_dir
                    if not cookie_dir: cookie_dir = '/'
                    domain = wikiutil.getCookieDomain(self.request)
                    #if config.wiki_base_domain == 'localhost'or config.wiki_base_domain == '127.0.0.1':
                    #  # browsers reject domain=localhost or domain=127.0.0.1
                    #  domain = '' 
                    #else:
                    #  domain = config.wiki_base_domain
                    self.request.setHttpHeader(('Set-Cookie','%s=%s; expires=Tuesday, 01-Jan-1999 12:00:00 GMT;domain=%s;Path=%s' % (cookie_id, cookie[cookie_id].value, domain, cookie_dir)))
            self.request.saved_cookie = ''
            self.request.auth_username = ''
            self.request.user = user.User(self.request)
            return msg + _("Cookie deleted. You are now logged out.")
    
        if form.has_key('login_sendmail'):
            if not self.request.isPOST():
                return """Use the interactive interface to change settings!"""
            if not config.mail_smarthost:
                return _('''This wiki is not enabled for mail processing. '''
                        '''Contact the owner of the wiki, who can either enable email, or remove the "Subscribe" icon.''')
            try:
                email = form['email'][0].lower()
            except KeyError:
                return _("Please provide a valid email address!")
    
            text = ''
            uid = user.getUserIdByEmail(email, self.request)
            if uid:
                theuser = user.User(self.request, uid)
                if theuser.valid:
                    code = self.createCode(theuser.id)
                    if config.wiki_farm:
                        url = farm.getBaseFarmURL(self.request)
                        sitename = farm.getBaseWikiFullName(self.request)
                    else:
                        url = '%s/' % self.request.getBaseURL()
                    text = "Go here to automatically log into %s: %s%s?action=userform&uid=%s&code=%s\nOnce you're logged in, you should change your password in your settings (you forgot your password, right?).\n\n(The link in this email is good for one use only.)" % (sitename, url, wikiutil.quoteWikiname(config.page_user_preferences), theuser.id, code)

            if not text:
                return _("Found no account matching the given email address '%(email)s'!") % {'email': email}


            mailok, msg = util.mail.sendmail(self.request, [email], 
                'Your wiki account data', text, mail_from=config.mail_from)
            return wikiutil.escape(msg)

        if form.has_key('login') or form.has_key('uid'):
            uid = None

            if form.has_key('code') and form.has_key('uid'):
               given_uid = form['uid'][0].strip()
               given_code = form['code'][0].strip()
        
               given_code
               if self.isValidCode(given_uid, given_code):
                  uid = given_uid

            if uid:
                # we were given account information so let's create an account -> log them in
                theuser = user.User(self.request, id=uid)
                msg = _("You are now logged in!  Please change your password below!")
                # send the cookie
                theuser.sendCookie(self.request)
                self.request.user = theuser
                return msg
            else:
                # we weren't given information, so let's see if they gave us a login/password

                # try to get the user name
                try:
                    name = form['username'][0].replace('\t', ' ').strip()
                except KeyError:
                    name = ''

                # try to get the password
                password = form.get('password',[''])[0]

                # load the user data and check for validness
                if name:
                    theuser = user.User(self.request, name=name, password=password, is_login=True)
                else:
                    theuser = user.User(self.request, id=uid, name=name, password=password, is_login=True)


                if config.wiki_farm:
                    wiki_base_url = farm.getBaseFarmURL(self.request)
                else:
                    wiki_base_url = '%s/' % self.request.getScriptname()

                if not theuser.valid:
                    if not self.request.form.has_key('backto_wiki') or not self.request.form['backto_wiki'][0]:
                        return_string = """
Unknown username or wrong password.<br /><br />New user?  <a href="%s%s?new_user=1">Click here to create an account!</a><br /><br />Forgot your password?  We'll email it to you.
<form action="%s" method="POST"><input type="hidden" name="action" value="userform">
Email address: <input class="formfields" type="text" name="email">&nbsp;<input type="submit" class="formbutton" name="login_sendmail" value="Mail me my account data">
</form>
""" % (wiki_base_url, wikiutil.quoteWikiname(config.page_user_preferences), wiki_base_url)

                        return return_string
                    else:
                        self.request.http_redirect(urllib.unquote(self.request.form['backto_page'][0].encode(config.charset)) + '?action=userform&badlogin=1')
                        return

            # send the cookie
            theuser.sendCookie(self.request)
            self.request.user = theuser
            send_back_home(self.request, msg="You are now logged in!")
        else:
            if not self.request.isPOST():
                return """Use the interactive interface to change settings!"""
            # save user's profile, first get user instance
            theuser = user.User(self.request)
    
            # try to get the name, if name is empty or missing, return an error msg
            if form.has_key('username') and form['username'][0].replace('\t', '').strip():
                theuser.propercased_name = form['username'][0].replace('\t', ' ').strip()
                theuser.name = theuser.propercased_name.lower()
            elif form.has_key('username'):
                raise BadData, (_("Please enter a user name!"), new_user)
    
            if self.request.user.name and (self.request.user.name != theuser.name):
              # they are still logged on and are trying to make a new account
              raise BadData, (_("Please log out before creating an account."), new_user)
            if user.getUserId(theuser.name, self.request):
                if theuser.name != self.request.user.name:
                    raise BadData, (_("User name already exists!"), new_user)
                else:
                    new_user = False

            if form.has_key('save') and form['save'][0] == 'Change password':
                # change password setting 

                # try to get the password and pw repeat
                password = form.get('password', [''])[0]
                password2 = form.get('password2',[''])[0]

                # Check if password is given and matches with password repeat
                if password != password2:
                    raise BadData, (_("Passwords don't match!"), new_user)
                if not password and new_user:
                    raise BadData, (_("Please specify a password!"), new_user)
                if password:
                    theuser.enc_password = user.encodePassword(password)

                self._clear_all_sessions_except_current()

                msg = _("Password changed!")
            else:
                # process general settings

                # try to get the email
                theuser.email = form.get('email', [''])[0]

                if theuser.email:
                    email_user_id = user.getUserIdByEmail(theuser.email, self.request)
                else:
                    email_user_id = None
                if not theuser.email or not re.match(".+@.+\..{2,}", theuser.email):
                    raise BadData, (_("Please provide your email address - without that you could not "
                             "get your login data via email just in case you lose it."), new_user)
                elif email_user_id and email_user_id != theuser.id:
                    raise BadData, (_("""Somebody else has already registered with the email address "%s", please pick something else.""" % theuser.email), new_user)
        
                # editor size
                theuser.edit_rows = util.web.getIntegerInput(self.request, 'edit_rows', theuser.edit_rows, 10, 60)
                theuser.edit_cols = util.web.getIntegerInput(self.request, 'edit_cols', theuser.edit_cols, 30, 100)
        
                # time zone
                tz = form.get('tz', theuser.tz)[0]
                if tz not in pytz.common_timezones:
                    tz = theuser.tz
                theuser.tz = tz
        
                # try to get the (optional) theme
                #theuser.theme_name = form.get('theme_name', [config.theme_default])[0]

                wiki_for_userpage = form.get('wiki_for_userpage', [''])[0].lower()
                if wiki_for_userpage and not wikiutil.isInFarm(wiki_for_userpage, self.request):
                    raise BadData, (_('"%s" is not the name of a wiki.' % wiki_for_userpage), new_user)
                if wiki_for_userpage != theuser.wiki_for_userpage:
                    # they have changed the wiki! time to do something differently
                    msg = _("<p>User preferences saved!</p><p><strong>Note:</strong> It may take a bit for all links to your name to point to the new wiki.</p>")
                    theuser.wiki_for_userpage = wiki_for_userpage

                # User CSS URL
                theuser.css_url = form.get('css_url', [''])[0]
        
                # try to get the (optional) preferred language
                #theuser.language = form.get('language', [''])[0]
    
                # checkbox options
                keys = []
                for key in user_checkbox_fields:
                    value = form.get(key, [0])[0]
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                    setattr(theuser, key, value)
        
            if new_user:
                theuser.propercased_name = theuser.propercased_name.strip() # strip spaces, we don't allow them anyway
                theuser.name = theuser.propercased_name.lower()
                if not theuser.name.strip():
                    raise BadData, (_("Please provide a user name!"), new_user)
                elif theuser.propercased_name.find(' ') != -1:
                    raise BadData, (_("Invalid username: spaces are not allowed in user names"), new_user)
                elif re.search('[%s]' % re.escape(USER_NOT_ALLOWED_CHARS), theuser.propercased_name):
                    raise BadData, (_("Invalid username: the characters %s are not allowed in usernames." % wikiutil.escape(USER_NOT_ALLOWED_CHARS)), new_user)
                elif theuser.name == '..' or theuser.name == '.': # messes up subpages.  '/' isn't allowed, so we just disallow this and we're cool.
                    raise BadData, (_("Invalid username: okay, seriously, that's a pretty lame name.  Pick something better!"), new_user)
                elif len(theuser.propercased_name) > MAX_USERNAME_LENGTH:
                    raise BadData, (_("Invalid username: a username can be at most %s characters long." % MAX_USERNAME_LEGNTH), new_user)
                elif not theuser.email or not re.match(".+@.+\..{2,}", theuser.email):
                    raise BadData, (_("""Please provide your email address - without that you could not 
                             get your login data via email just in case you lose it."""), new_user)
                name_exists = user.getUserId(theuser.name, self.request)
                if name_exists:
                    raise BadData, (_("This user name already belongs to somebody else."), new_user)
                email_exists = user.getUserIdByEmail(theuser.email, self.request)
                if email_exists:
                    raise BadData, (_("This email already belongs to somebody else."), new_user)

                # try to get the password and pw repeat
                password = form.get('password', [''])[0]
                password2 = form.get('password2',[''])[0]

                # Check if password is given and matches with password repeat
                if password != password2:
                    raise BadData, (_("Passwords don't match!"), new_user)
                if not password and new_user:
                    raise BadData, (_("Please specify a password!"), new_user)
                if password:
                    theuser.enc_password = user.encodePassword(password)

                theuser.anonymous = False


            # save data and send cookie
            theuser.save(new_user=new_user)
            theuser.sendCookie(self.request)
            self.request.user = theuser
    

            from Sycamore.formatter.text_html import Formatter
            formatter = Formatter(self.request)

            if not new_user:
              if not msg:
                msg = _("User preferences saved!")
              if self.from_wiki:
                go_back_to_wiki = farm.link_to_wiki(self.from_wiki, formatter)
                msg = '%s<br/><br/>Wanna go back to %s?' % (msg, go_back_to_wiki)
            else:
              msg = _("Account created!  You are now logged in.")
              self.request.user.valid = 1
              if self.from_wiki and self.from_wiki.lower() != farm.getBaseWikiName(self.request):
                go_back_to_wiki = farm.link_to_wiki(self.from_wiki, formatter)
                msg = '%s<br/><br/>Head back over to %s and your new account should work there!' % (msg, go_back_to_wiki)
            if _debug:
                msg = msg + util.dumpFormData(form)
            return msg

def send_back_home(request, msg=''):
    if request.form.has_key('backto_wiki') and request.form.has_key('backto_page'):
        backto_wiki = request.form['backto_wiki'][0]
        q_backto_page = request.form['backto_page'][0]
        if request.form.has_key('qs'):
            q_query_string = request.form['qs'][0]
        else:
            q_query_string = ''
        secret, stored_expire_time, session = request.user.cookie_dough
        if q_query_string:
            url = '%s?action=userform&backto_page=%s&qs=%s&secret=%s&expire_time=%s&uid=%s&session=%s' % (urllib.unquote(q_backto_page),
                q_backto_page, q_query_string, urllib.quote(secret), stored_expire_time, request.user.id, urllib.quote(session))
        else:
             url = '%s?action=userform&backto_page=%s&secret=%s&expire_time=%s&uid=%s&session=%s' % (urllib.unquote(q_backto_page),
                q_backto_page, urllib.quote(secret), stored_expire_time, request.user.id, urllib.quote(session))
        request.http_redirect(url) 

#############################################################################
### Form Generation
#############################################################################

user_checkbox_fields = {
    'remember_me': 'Remember login information (so you don\'t have to keep logging in',
    'disabled': 'Disable this account forever &mdash; WARNING!! &mdash; permanent'
}

first_time_msg = """<h2>First time</h2>
<p>
Your email is needed for you to be able to recover lost login data.
</p>
<p>
If you click on Create Profile, a user profile will be created for you and you will be logged in immediately. 
</p>"""

forgot_password_msg = """<h2>Forgot password?</h2>
<p>
If you forgot your password, attempt to log in via the login box in the upper right hand corner of the screen and you will be given further instruction.
</p>
"""

class UserSettings:
    """ User login and settings management. """

    _date_formats = {
        'iso':  '%Y-%m-%d %H:%M:%S',
        'us':   '%m/%d/%Y %I:%M:%S %p',
        'euro': '%d.%m.%Y %H:%M:%S',
        'rfc':  '%a %b %d %H:%M:%S %Y',
    }


    def __init__(self, request):
        """ Initialize user settings form.
        """
        self.request = request
        self._ = request.getText


    def _tz_select(self):
        """ Create time zone selection. """
        tz  = self.request.user.tz

        options = []
        for timezone in pytz.common_timezones:
            options.append((timezone, timezone))
 
        return util.web.makeSelection('tz', options, tz)


    def _lang_select(self):
        """ Create language selection. """
        from Sycamore import i18n
        from Sycamore.i18n import NAME
        _ = self._
        cur_lang = self.request.user.valid and self.request.user.language or ''
        langs = i18n.wikiLanguages().items()
        langs.sort(lambda x,y,NAME=NAME: cmp(x[1][NAME], y[1][NAME]))
        options = [('', _('<Browser setting>'))]
        for lang in langs:
            # i18n source might be encoded so we recode language names
            name = lang[1][NAME]
            # XXX UNICODE fix needed?
            name = i18n.recode(name, i18n.charset(), config.charset) or name
            options.append((lang[0], name))
                
        return util.web.makeSelection('language', options, cur_lang)
  
    def _theme_select(self):
        """ Create theme selection. """
        cur_theme = self.request.user.valid and self.request.user.theme_name or self.request.config.theme_default
        options = []
        for theme in wikiutil.getPlugins('theme'):
            options.append((theme, theme))
                
        return util.web.makeSelection('theme_name', options, cur_theme)

    def _from_wiki_msg(self):
        """
        Print a message that says what wiki we're from and what our base wiki is.
        """
        wiki_name = self.from_wiki
        base_wiki_sitename = farm.getBaseWikiFullName(self.request)
        d = { 'wiki_name': farm.link_to_wiki(wiki_name, self.request.formatter), 'base_wiki_name': farm.link_to_wiki(farm.getBaseWikiName(self.request), self.request.formatter),
              'base_wiki_sitename_link': farm.link_to_wiki(farm.getBaseWikiName(self.request), self.request.formatter, text=base_wiki_sitename, no_icon=True),
              'base_wiki_sitename': base_wiki_sitename,
            }
        msg = config.wiki_farm_from_wiki_msg % d
        return msg

    def make_form(self, html_class="settings_form"):
        """ Create the FORM, and the DIVs with the input fields
        """
        if config.use_ssl:
            action = self.request.getScriptname() + self.request.getPathinfo()
            if config.wiki_farm:
                action = "%s%s" % (farm.getBaseFarmURL(self.request, force_ssl=config.use_ssl), wikiutil.quoteWikiname(config.page_user_preferences))
            else:
                action = '%s/%s' % (self.request.getQualifiedURL(self.request.getScriptname(), force_ssl=config.use_ssl), wikiutil.quoteWikiName(config.page_user_preferences))
        else:
            action = self.request.getScriptname() + self.request.getPathinfo()
        self._form = html.FORM(action=action)
        self._inner = html.DIV(html_class=html_class)

        # Use the user interface language and direction
        lang_attr = self.request.theme.ui_lang_attr()
        self._form.append(html.Raw("<div %s>" % lang_attr))

        self._form.append(html.INPUT(type="hidden", name="action", value="userform"))
        if self.from_wiki:
          self._form.append(html.INPUT(type="hidden", name="from_wiki", value=self.from_wiki))
        self._form.append(self._inner)
        self._form.append(html.Raw("</div>"))

  
    def make_row(self, label, cell, option_text=None, **kw):
        """ Create a row in the form.
        """
        if not option_text:
          self._inner.append(html.DIV(html_class="settings_form_item").extend([
              html.DIV(html_class="settings_form_label", **kw).extend([label]),
              html.DIV().extend(cell),
          ]))
        else:
          option_label = html.SPAN(html_class="optional", **kw).extend([option_text])
          settings_label = html.DIV(html_class="settings_form_label", **kw).extend([label, option_label])
          self._inner.append(html.DIV(html_class="settings_form_item").extend([
              settings_label,
              html.DIV().extend(cell),
          ]))


    def asHTML(self, msg='', new_user=False):
        """ Create the complete HTML form code. """
        _ = self._
        form_html = []
        self.from_wiki = None

        if self.request.form.has_key('new_user'):
          if self.request.form['new_user'][0] and not self.request.user.valid:
            new_user = True

        # if they are clicking into the user settings area
        # from a non-hub wiki then we want to get this wiki's name
        # and display some message accoridngly
        if self.request.form.has_key('from_wiki'):
          self.from_wiki = self.request.form['from_wiki'][0].lower().strip()
          if not wikiutil.isInFarm(self.from_wiki, self.request):
            self.from_wiki = None
        
        # different form elements depending on login state
        html_uid = ''
        html_sendmail = ''
        if self.request.user.valid:
            html_uid = '<tr><td>ID</td><td>%s</td></tr>' % (self.request.user.id,)
            buttons = [
                ('save', _('Save')),
                ('logout', _('Logout')),
            ]
        else:
            if new_user:
              buttons = [
                  ("save", _('Create Profile')),
              ]
            else: 
               buttons = [
                  ("login", _('Login')),
              ]

        #self._table.append(html.Raw(html_uid))
        self.make_form()

        if new_user and self.from_wiki:
           if self.from_wiki != farm.getBaseWikiName(self.request):
             self._inner.append(html.Raw(self._from_wiki_msg()))

        if not self.request.user.valid:
          if not new_user: user_name_help_text = ''
          else: user_name_help_text = _('(Please do not use nickname or business name.)')
          self.make_row(_('Name'), [
            html.INPUT(
                type="text", size=32, name="username", value=self.request.user.name
            ),
          ], option_text = user_name_help_text)

        if new_user:
            
            self.make_row(_('Password'), [
                html.INPUT(
                    type="password", size=32, name="password",
                )
            ])
            self.make_row(_('Password repeat'), [
                html.INPUT(
                    type="password", size=32, name="password2",
                ),
                ' ',
            ])

            self.make_row(_('Email'), [
                html.INPUT(
                  type="text", size=40, name="email", value=self.request.user.email
                )])

            if new_user: new_user_int = 1
            else: new_user_int = 0
            self.make_row('', [
                html.INPUT(
                  type="hidden", name="new_user", value=new_user_int
                )])


            # Add buttons for new user
            button_cell = []
            for name, label in buttons:
                button_cell.extend([
                    html.INPUT(type="submit", name=name, value=label),
                    ' ',
                ])
            self.make_row('', button_cell)

            form_html.append(str(self._form))
    
            form_html.append(first_time_msg)
            form_html.append(forgot_password_msg)

        # show options only if already logged in
        elif self.request.user.valid:
            self.make_form()

            self._inner.append(html.Raw('<h2>General Settings</h2>'))

            if self.from_wiki:
                if self.from_wiki != farm.getBaseWikiName(self.request):
                    self._inner.append(html.Raw(self._from_wiki_msg()))

            
            self.make_row(_('Email'), [
                html.INPUT(
                  type="text", size=40, name="email", value=self.request.user.email
                )])


            self.make_row(_('Time zone'), [
                _('My time zone is'), ' ',
                self._tz_select(),
            ])

            
            self.make_row('', [
                html.INPUT(type="checkbox", name='remember_me', value=1,
                            checked=getattr(self.request.user, 'remember_me', 0)),
                'Remember me so I don\'t have to keep logging in',
                ])


            if config.wiki_farm:
                # FIXME: make the link link somewhere sane based on current context.

                # prepare list of possible userpage locations
                wikis_for_userpage_options = copy(self.request.user.getWatchedWikis())
                if self.request.user.wiki_for_userpage:
                    wikis_for_userpage_options[self.request.user.wiki_for_userpage] = None
                wikis_for_userpage_options[farm.getBaseWikiName(self.request)] = None
                wikis_for_userpage_options = wikis_for_userpage_options.keys()
                selection_tuples = []
                for name in wikis_for_userpage_options:
                    selection_tuples.append((name, name))
                wikis_for_userpage_options = selection_tuples
                wikis_for_userpage_options.insert(0, ('', 'each wiki (default)'))

                self.make_row(_('User page'), [
                        html.Raw('<div><span style="vertical-align: bottom;">My name links to my user page on ' + self.request.theme.make_icon('interwiki', {'wikitag': self.request.user.wiki_for_userpage}, html_class="interwiki_icon") + '</span>'),
                        util.web.makeSelection('wiki_for_userpage', wikis_for_userpage_options, selectedval=self.request.user.wiki_for_userpage),
                        html.Raw('</div>')
                        ], option_text=_('(Choosing from watched wikis.)')) 

            self.make_row(_('Editor size'), [
                html.INPUT(type="text", size=3, maxlength=3,
                    name="edit_cols", value=self.request.user.edit_cols),
                ' x ',
                html.INPUT(type="text", size=3, maxlength=3,
                    name="edit_rows", value=self.request.user.edit_rows),
            ])


            #if not config.theme_force:
            #    self.make_row(_('Preferred theme'), [self._theme_select()])
            
            
            self.make_row(_('Personal CSS URL'), [
                html.INPUT(
                    type="text", size=40, name="css_url", value=self.request.user.css_url
                ),
                ' '], option_text=_('(Leave empty to disable user CSS)'),
            )

            # Add buttons
            button_cell = []
            for name, label in buttons:
                button_cell.extend([
                    html.INPUT(type="submit", name=name, value=label),
                    ' ',
                ])
            self.make_row('', button_cell)

            form_html.append(str(self._form))

            if config.wiki_farm:
                form_html.append('<h2>Watched wikis</h2><p>These are wikis you want to see on the Interwiki Recent Changes page.</p>')
    
                watched_wiki_list = self.request.user.getWatchedWikis()
                if not watched_wiki_list:
                    form_html.append('<p><em>You have no watched wikis.  To add watch a wiki, simply visit a wiki and click the "watch this wiki" link in the upper right hand corner of the screen (under "Welcome %s").</em></p>' % self.request.user.propercased_name)
                else:
                    form_html.append('<ul>')
                    for wiki_name in watched_wiki_list:
                        remove_link = '<span style="font-size:x-small; margin-left: 1.5em;">[%s]</span>' %  Page(config.page_user_preferences, self.request).link_to(
                            know_status=True, know_status_exists=True, querystr='action=watch_wiki&wikiname=%s&del=1' % wiki_name, text='remove')
                        form_html.append('<li>%s %s</li>' % (farm.link_to_wiki(wiki_name, self.request.formatter), remove_link))

                    form_html.append('</ul>')

            self.make_form()
            self._inner.append(html.Raw('<h2>Change password</h2>'))
            buttons = [("save", _("Change password"))]
    
            self.make_row(_('Password'), [
                html.INPUT(
                    type="password", size=32, name="password",
                )
            ])
            self.make_row(_('Password repeat'), [
                html.INPUT(
                    type="password", size=32, name="password2",
                ),
                ' ',
            ])
    
            # Add buttons 
            button_cell = []
            for name, label in buttons:
                button_cell.extend([
                    html.INPUT(type="submit", name=name, value=label),
                    ' ',
                ])
            self.make_row('', button_cell)

            self._inner.append(html.Raw('<h2>Disable account</h2>'))
            buttons = [("save", _("Disable account"))]

            self.make_row('', [
                html.INPUT(type="checkbox", name='disabled', value=1,
                            checked=getattr(self.request.user, 'disabled', 0)),
                'Disable this account forever',
                ])

    
            # Add buttons 
            button_cell = []
            for name, label in buttons:
                button_cell.extend([
                    html.INPUT(type="submit", name=name, value=label),
                    ' ',
                ])
            self.make_row('', button_cell)


            form_html.append(str(self._form))

        else:
            self.make_form()

            self._inner.append(html.Raw('<h2>Log in</h2>'))

            self.make_row(_('User name'), [
                html.INPUT(
                    type="text", size=22, name="username",
                )
            ])
            self.make_row(_('Password'), [
                html.INPUT(
                    type="password", size=22, name="password",
                ),
                ' ',
            ])

            # Add buttons for general settings
            button_cell = []
            for name, label in buttons:
                button_cell.extend([
                    html.INPUT(type="submit", name=name, value=label),
                    ' ',
                ])
            self.make_row('', button_cell)

            form_html.append(str(self._form))

            form_html.append(forgot_password_msg)


        return ''.join(form_html)


def getUserForm(request, msg='', new_user=False):
    """ Return HTML code for the user settings. """
    return UserSettings(request).asHTML(msg=msg, new_user=new_user)


#############################################################################
### User account administration
#############################################################################

def do_user_browser(request):
    """ Browser for SystemAdmin macro. """
    from Sycamore.util.dataset import TupleDataset, Column
    from Sycamore.Page import Page
    _ = request.getText

    data = TupleDataset()
    data.columns = [
        Column('id', label=('ID'), align='right'),
        Column('name', label=('Username')),
        Column('email', label=('Email')),
        Column('action', label=_('Action')),
    ]

    # Iterate over users
    for uid in user.getUserList(self.request.cursor):
        account = user.User(request, uid)

        userhomepage = Page(account.name, self.request)
        if userhomepage.exists():
            namelink = userhomepage.link_to()
        else:
            namelink = account.name

        data.addRow((
            request.formatter.code(1) + uid + request.formatter.code(0),
            request.formatter.rawHTML(namelink),
            request.formatter.url('mailto:' + account.email, account.email, 'external', pretty_url=1, unescaped=1),
            '',
        ))

    if data:
        from Sycamore.widget.browser import DataBrowserWidget

        browser = DataBrowserWidget(request)
        browser.setData(data)
        return browser.toHTML()

    # No data
    return ''

forever = 10*365*24*3600 # 10 years, after this time the polar icecaps will have melted anyway

def _create_nologin_cookie(request):
    try:
        cookie = Cookie.SimpleCookie(request.saved_cookie)
    except Cookie.CookieError:
        # ignore invalid cookies, else user can't relogin
        cookie = None
    if cookie and cookie.has_key(user.COOKIE_NOT_LOGGED_IN):
        return

    cookie_dir = config.web_dir
    if not cookie_dir: cookie_dir = '/'
    cookie_value = '%s="1"' % user.COOKIE_NOT_LOGGED_IN

    wiki_domain = wikiutil.getCookieDomain(request)
    domain = "domain=%s;" % wiki_domain
    
    now = time.time()
    expire = now + 10*60 # ten minutes until we check if we've logged in to the farm hub
    loc=locale.setlocale(locale.LC_TIME, 'C')
    expirestr = time.strftime("%A, %d-%b-%Y %H:%M:%S GMT", time.gmtime(expire))
    locale.setlocale(locale.LC_TIME, loc)

    cookie_header = ("Set-Cookie", "%s; expires=%s;%sPath=%s" % (cookie_value, expirestr, domain, cookie_dir))
    request.setHttpHeader(cookie_header)
