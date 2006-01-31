# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - User Account Maintenance

    @copyright: 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import string, time, re, Cookie
from LocalWiki import config, user, util, wikiutil, wikidb
import LocalWiki.util.web
import LocalWiki.util.mail
import LocalWiki.util.datetime
from LocalWiki.widget import html

_debug = 0


#############################################################################
### Form POST Handling
#############################################################################

def savedata(request):
    """ Handle POST request of the user preferences form.

    Return error msg or None.  
    """
    return UserSettingsHandler(request).handleData()


class UserSettingsHandler:

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
	  stored_secret = self.request.mc.get(key)
	  # make sure they aren't just getting lucky with a fake cookie
	  if stored_secret and (stored_secret == user.hash(cookie_secret)):
	    self.request.mc.delete(key)
	self.request.cursor.execute("DELETE from userSessions where user_id=%(cookie_userid)s and session_id=%(cookie_sessionid)s and secret=%(cookie_secret)s", {'cookie_userid':cookie_userid, 'cookie_sessionid':cookie_sessionid, 'cookie_secret':user.hash(cookie_secret)})

    def isValidCode(self, given_uid, given_code):
	import cPickle, os
	state = False
	if os.path.exists(config.data_dir + '/lostpasswddict.pickle'):
		lostpasswdfile = open(config.data_dir + '/lostpasswddict.pickle', 'r')	
		dict = cPickle.load(lostpasswdfile)
		if dict.has_key(given_uid):
			for code in dict[given_uid]:
				split_string = code.split(',')
				hashed_code = split_string[0]
				written_time = float(split_string[1])
				if written_time + 60*30 > time.time():
					if hashed_code == user.hash(given_code):
						del dict[given_uid]
						lostpasswdfile.close()
						lostpasswdfile = open(config.data_dir + '/lostpasswddict.pickle', 'w')
						cPickle.dump(dict, lostpasswdfile, 2)
						state = True
		lostpasswdfile.close()
	return state
		
    def createCode(self, userid):
	import random, cPickle, os
	ourcode = str(random.random())
	if os.path.exists(config.data_dir + '/lostpasswddict.pickle'):
	   lostpasswdfile = open(config.data_dir + '/lostpasswddict.pickle', 'r')
	   dict = cPickle.load(lostpasswdfile)
	   lostpasswdfile.close()
	   lostpasswdfile = open(config.data_dir + '/lostpasswddict.pickle', 'w')
	else:
	   lostpasswdfile = open(config.data_dir + '/lostpasswddict.pickle', 'w')
	   dict = {}

	if dict.has_key(userid):
		dict[userid].append(user.hash(ourcode) + ',' + str(time.time()))
	else:
		dict[userid] = [user.hash(ourcode) + ',' + str(time.time())]
	
	cPickle.dump(dict, lostpasswdfile, 2)
	lostpasswdfile.close()
	return ourcode


    def handleData(self):
        _ = self._
        form = self.request.form
    
	isdisabled = False
	if form.get('disabled', [0])[0] == '1':
		isdisabled = True
        if form.has_key('logout') or isdisabled:
            # clear the cookie in the browser and locally
            try:
                cookie = Cookie.SimpleCookie(self.request.saved_cookie)
            except Cookie.CookieError:
                # ignore invalid cookies
                cookie = None
            else:
                if cookie.has_key(wikiutil.quoteFilename(config.sitename)+'ID'):
	            self.removeSession(cookie[wikiutil.quoteFilename(config.sitename)+'ID'].value)
		    #not sure why this uid line is here..
                    #uid = cookie[wikiutil.quoteFilename(config.sitename)+'ID'].value
		    cookie_dir = config.web_dir
	   	    if not cookie_dir: cookie_dir = '/'
                    self.request.setHttpHeader('Set-Cookie: %s=%s; expires=Tuesday, 01-Jan-1999 12:00:00 GMT;host=%s;Path=%s' % (wikiutil.quoteFilename(config.sitename)+'ID', cookie[wikiutil.quoteFilename(config.sitename)+'ID'].value,config.domain, cookie_dir))
            self.request.saved_cookie = ''
            self.request.auth_username = ''
            self.request.user = user.User(self.request)
            return _("Cookie deleted. You are now logged out.")
    
        if form.has_key('login_sendmail'):
            if not config.mail_smarthost:
                return _('''This wiki is not enabled for mail processing. '''
                        '''Contact the owner of the wiki, who can either enable email, or remove the "Subscribe" icon.''')
            try:
                email = form['email'][0].lower()
            except KeyError:
                return _("Please provide a valid email address!")
    
            text = ''
            users = user.getUserList(self.request.cursor)
            for uid in users:
                theuser = user.User(self.request, uid)
                if theuser.valid and theuser.email.lower() == email:
                    code = self.createCode(theuser.id)
                    text = "Go here to automatically log into the %s: %s/?action=userform&uid=%s&code=%s\nOnce you're logged in, you should change your password in Settings (you forgot your password, right?) -- entering your password twice and then clicking save will change your password." % (config.sitename, self.request.getBaseURL(), theuser.id, code)
                    break
            if not text:
                return _("Found no account matching the given email address '%(email)s'!") % {'email': email}
    
            mailok, msg = util.mail.sendmail(self.request, [email], 
                'Your wiki account data', text, mail_from=config.mail_from)
            return wikiutil.escape(msg)

        if form.has_key('login') or form.has_key('uid'):
            # check for "uid" value that we use in the relogin URL
	    # this is turned OFF for security reasons
            #try:
            #     uid = form['uid'][0]
            #except KeyError:
            #     uid = None
	    uid = None

	    if form.has_key('code') and form.has_key('uid'):
               given_uid = form['uid'][0]
               given_code = form['code'][0]
	
               if self.isValidCode(given_uid, given_code):
		  uid = given_uid

            # try to get the user name
            try:
                name = form['username'][0].replace('\t', ' ').strip()
            except KeyError:
                name = ''

            # try to get the password
            password = form.get('password',[''])[0]
  
            # load the user data and check for validness
            theuser = user.User(self.request, uid, name=name, password=password)

            if config.relative_dir: add_on = '/'
            else: add_on = ''

            if not theuser.valid:
                return_string = """
Unknown user name or wrong password.<br /><br />New user?  <a href="/%s%sUser_Preferences">Click here to create an account!</a><br /><br />Forgot your password?  We'll email it to you.
<form action="/%s%s" method="POST"><input type="hidden" name="action" value="userform">
Email address: <input class="formfields" type="text" name="email">&nbsp;<input type="submit" class="formbutton" name="login_sendmail" value="Mail me my account data">
</form>
""" % (config.relative_dir, add_on, config.relative_dir, add_on)

                return return_string

            # send the cookie
            theuser.sendCookie(self.request)
            self.request.user = theuser
        else:
            # save user's profile, first get user instance
            theuser = user.User(self.request)
    
            # try to get the name, if name is empty or missing, return an error msg
            try:
                theuser.name = form['username'][0].replace('\t', ' ').strip()
            except KeyError:
                return _("Please enter a user name!")
    
    	    if self.request.user.name and (self.request.user.name != theuser.name):
	      # they are still logged on and are trying to make a new account
	      return _("Please log out before creating an account.")
            # Is this an existing user trying to change password, or a new user?
            newuser = True
            if user.getUserId(theuser.name, self.request):
                if theuser.name != self.request.user.name:
                    return _("User name already exists!")
                else:
                    newuser = False

            # try to get the password and pw repeat
            password = form.get('password', [''])[0]
            password2 = form.get('password2',[''])[0]

            # Check if password is given and matches with password repeat
            if password != password2:
                return _("Passwords don't match!")
            if not password and newuser:
                return _("Please specify a password!")
            if password:
                theuser.enc_password = user.encodePassword(password)

            # try to get the (optional) email
            theuser.email = form.get('email', [''])[0]
    
            # editor size
            theuser.edit_rows = util.web.getIntegerInput(self.request, 'edit_rows', theuser.edit_rows, 10, 60)
            theuser.edit_cols = util.web.getIntegerInput(self.request, 'edit_cols', theuser.edit_cols, 30, 100)
    
            # time zone
            theuser.tz_offset = util.web.getIntegerInput(self.request, 'tz_offset', theuser.tz_offset, -84600, 84600)
    
            # date format
            #try:
            #    theuser.datetime_fmt = UserSettings._date_formats.get(form['datetime_fmt'][0], '')
            #except (KeyError, ValueError):
            #    pass
    
            # try to get the (optional) theme
            #theuser.theme_name = form.get('theme_name', [config.theme_default])[0]

            # User CSS URL
            theuser.css_url = form.get('css_url', [''])[0]
    
            # try to get the (optional) preferred language
            #theuser.language = form.get('language', [''])[0]

            # checkbox options
	    keys = []
            for key, label in user.User._checkbox_fields:
                value = form.get(key, [0])[0]
                try:
                    value = int(value)
                except ValueError:
                    pass
                setattr(theuser, key, value)
    
            # quicklinks for header
            #quicklinks = form.get('quicklinks', [''])[0]
            #quicklinks = quicklinks.replace('\r', '')
            #quicklinks = quicklinks.split('\n')
            #quicklinks = map(string.strip, quicklinks)
            #quicklinks = filter(None, quicklinks)
            #quicklinks = map(wikiutil.quoteWikiname, quicklinks)
            #theuser.quicklinks = ','.join(quicklinks)
            
            # subscription for page change notification
            #theuser.subscribed_pages = form.get('subscribed_pages', [''])[0]
            #theuser.subscribed_pages = theuser.subscribed_pages.replace('\r', '')
            #theuser.subscribed_pages = theuser.subscribed_pages.replace('\n', ',')
            
            # if we use ACLs, name and email are required to be unique
            # further, name is required to be a WikiName (CamelCase!)
            # we also must forbid the username to match page_group_regex
            # see also LocalWiki/scripts/moin_usercheck.py
            if config.acl_enabled and newuser:
                theuser.name = theuser.name.replace(' ','') # strip spaces, we don't allow them anyway
                if not re.match("(?:[%(u)s][%(l)s]+){2,}" % {'u': config.upperletters, 'l': config.lowerletters}, theuser.name):
                    return _("Please enter your name like that: FirstnameLastname")
                if re.search(config.page_group_regex, theuser.name):
                    return _("You must not use a group name as your user name.")
                if not theuser.email or not re.match(".+@.+\..{2,}", theuser.email):
                    return _("Please provide your email address - without that you could not "
                             "get your login data via email just in case you lose it.")
                users = user.getUserList(self.request.cursor)
                for uid in users:
                    if uid == theuser.id:
                        continue
                    thisuser = user.User(self.request, uid)
                    if thisuser.name == theuser.name:
                        return _("This user name already belongs to somebody else.")
                    if theuser.email and thisuser.email == theuser.email:
                        return _("This email already belongs to somebody else.")

            # save data and send cookie
            theuser.save()
            theuser.sendCookie(self.request)
            self.request.user = theuser
    
            result = _("User preferences saved!")
            if _debug:
                result = result + util.dumpFormData(form)
            return result


#############################################################################
### Form Generation
#############################################################################

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
	if self.request.user.tz_offset: tz = self.request.user.tz_offset
	else: tz = config.tz_offset

        options = []
        now = time.time()
        for halfhour in range(-47, 48):
            offset = halfhour * 1800
            t = now + offset

            options.append((
                offset,
                '%s [%s%s:%s]' % (
                    time.strftime(config.datetime_fmt, util.datetime.tmtuple(t)),
                    "+-"[offset < 0],
                    string.zfill("%d" % (abs(offset) / 3600), 2),
                    string.zfill("%d" % (abs(offset) % 3600 / 60), 2),
                ),
            ))
 
        return util.web.makeSelection('tz_offset', options, tz)


#    def _dtfmt_select(self):
#        """ Create date format selection. """
#        _ = self._
#        try:
#            selected = [
#                k for k, v in self._date_formats.items()
#                    if v == self.request.user.datetime_fmt][0]
#        except IndexError:
#            selected = ''
#        options = [('', _('Default'))] + self._date_formats.items()
#
#        return util.web.makeSelection('datetime_fmt', options, selected)


    def _lang_select(self):
        """ Create language selection. """
        from LocalWiki import i18n
        from LocalWiki.i18n import NAME
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
        cur_theme = self.request.user.valid and self.request.user.theme_name or config.theme_default
        options = []
        for theme in wikiutil.getPlugins('theme'):
            options.append((theme, theme))
                
        return util.web.makeSelection('theme_name', options, cur_theme)
  
    def make_form(self):
        """ Create the FORM, and the TABLE with the input fields
        """
        self._form = html.FORM(action=self.request.getScriptname() + self.request.getPathinfo())
        self._table = html.TABLE(border=0)

        # Use the user interface language and direction
        lang_attr = self.request.theme.ui_lang_attr()
        self._form.append(html.Raw("<div %s>" % lang_attr))

        self._form.append(html.INPUT(type="hidden", name="action", value="userform"))
        self._form.append(self._table)
        self._form.append(html.Raw("</div>"))


    def make_row(self, label, cell, **kw):
        """ Create a row in the form table.
        """
        self._table.append(html.TR().extend([
            html.TD(**kw).extend([html.B().append(label), '   ']),
            html.TD().extend(cell),
        ]))


    def asHTML(self):
        """ Create the complete HTML form code. """
        _ = self._
        self.make_form()

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
            buttons = [
                ("save", _('Create Profile')),
            ]

        #self._table.append(html.Raw(html_uid))
        
        self.make_row(_('Name'), [
            html.INPUT(
                type="text", size=32, name="username", value=self.request.user.name
            ),
            ' ', _('(Use FirstnameLastname. Please do not use nickname or business name.)'),
        ])

        self.make_row(_('Password'), [
            html.INPUT(
                type="password", size=32, name="password",
            )
        ])

        self.make_row(_('Password repeat'), [
            html.INPUT(
                type="password", size=32, name="password2",
            ),
            ' ', _('(New User or password change)'),
        ])

        self.make_row(_('Email'), [
            html.INPUT(
                type="text", size=40, name="email", value=self.request.user.email
            )])

        # show options only if already logged in
        if self.request.user.valid:
            
            #if not config.theme_force:
            #    self.make_row(_('Preferred theme'), [self._theme_select()])

            self.make_row(_('User CSS URL'), [
                html.INPUT(
                    type="text", size=40, name="css_url", value=self.request.user.css_url
                ),
                ' ', _('(Leave it empty for disabling user CSS)'),
            ])

            self.make_row(_('Editor size'), [
                html.INPUT(type="text", size=3, maxlength=3,
                    name="edit_cols", value=self.request.user.edit_cols),
                ' x ',
                html.INPUT(type="text", size=3, maxlength=3,
                    name="edit_rows", value=self.request.user.edit_rows),
            ])

            self.make_row(_('Time zone'), [
                _('Your time is'), ' ',
                self._tz_select(),
                html.BR(),
                _('Server time is'), ' ',
                time.strftime(config.datetime_fmt, util.datetime.tmtuple()),
                ' (UTC)',
            ])

            #self.make_row(_('Date format'), [self._dtfmt_select()])

            #self.make_row(_('Preferred language'), [self._lang_select()])
            
            # boolean user options
            bool_options = []
            checkbox_fields = user.User._checkbox_fields
            _ = self.request.getText
            checkbox_fields.sort(lambda a, b: cmp(a[1](_), b[1](_)))
            for key, label in checkbox_fields:
                if key != "remember_last_visit":
                    bool_options.extend([
                        html.INPUT(type="checkbox", name=key, value=1,
                            checked=getattr(self.request.user, key, 0)),
                        ' ', label(_), html.BR(),
                     ])

            self.make_row(_('General options'), bool_options, valign="top")

            #self.make_row(_('Quick links'), [
            #    html.TEXTAREA(name="quicklinks", rows=6, cols=50)
            #        .append('\n'.join(self.request.user.getQuickLinks())),
            #], valign="top")

            # subscribed pages
	    """
            if config.mail_smarthost:
                notifylist = self.request.user.getSubscriptionList()
                notifylist.sort()

                warning = []
                if not self.request.user.email:
                    warning = [
                        html.BR(),
                        html.SMALL(Class="warning").append(
                            _("This list does not work, unless you have"
                              " entered a valid email address!")
                        )]
                
                self.make_row(
                    html.Raw(_('Subscribed wiki pages <br>(one per line)')),
                    [html.TEXTAREA(name="subscribed_pages", rows=6, cols=50).append(
                        '\n'.join(notifylist)),
                    ] + warning,
                    valign="top"
                )
	     """

        # Add buttons
        button_cell = []
        for name, label in buttons:
            button_cell.extend([
                html.INPUT(type="submit", name=name, value=label),
                ' ',
            ])
        self.make_row('', button_cell)

        return str(self._form)


def getUserForm(request):
    """ Return HTML code for the user settings. """
    return UserSettings(request).asHTML()


#############################################################################
### User account administration
#############################################################################

def do_user_browser(request):
    """ Browser for SystemAdmin macro. """
    from LocalWiki.util.dataset import TupleDataset, Column
    from LocalWiki.Page import Page
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

        userhomepage = Page(account.name, self.request.cursor)
        if userhomepage.exists():
            namelink = userhomepage.link_to(request)
        else:
            namelink = account.name

        data.addRow((
            request.formatter.code(1) + uid + request.formatter.code(0),
            request.formatter.rawHTML(namelink),
            request.formatter.url('mailto:' + account.email, account.email, 'external', pretty_url=1, unescaped=1),
            '',
        ))

    if data:
        from LocalWiki.widget.browser import DataBrowserWidget

        browser = DataBrowserWidget(request)
        browser.setData(data)
        return browser.toHTML()

    # No data
    return ''

