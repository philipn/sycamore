# -*- coding: utf-8 -*-
"""
    Sycamore - "create a new wiki" action

    This action allows you to create a new wiki in your wiki farm if you:
        1) Have wiki_farm = True set in your config
        2) Have allow_web_based_wiki_creation = True set in your config

    @copyright: 2006 Philip Neustrom <philipn@gmail.com>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import random
import base64
import time

from Sycamore import config
from Sycamore import farm
from Sycamore import wikiutil

from Sycamore.util import mail
from Sycamore.Page import Page
from Sycamore.formatter.text_html import Formatter

do_email_auth = True
if do_email_auth:
    from Sycamore.action import captcha

WIKI_PENDING_TIME = 60*30 # how long is our email good for?

def _createCode(request):
    wikiname = request.form['wikiname'][0].lower()
    ourcode = str(random.random())
    written_time = time.time()
    d = {'wiki_name':wikiname, 'code':ourcode, 'written_time':written_time}
    request.cursor.execute(
        """INSERT into wikisPending (wiki_name, code, written_time) values
           (%(wiki_name)s, %(code)s, %(written_time)s)""", d, isWrite=True)
    return ourcode

def _isValidCode(request, given_wiki_name, given_code):
    state = False
    timenow = time.time()
    d = {'wiki_name':given_wiki_name, 'code':given_code,
         'timevalid': (timenow - WIKI_PENDING_TIME)}
    request.cursor.execute("""SELECT written_time from wikisPending
                              where code=%(code)s and
                                    wiki_name=%(wiki_name)s and
                                    written_time > %(timevalid)s""", d)
    result = request.cursor.fetchone()
    if result and result[0]:
        state = True
    
    # decent place to clear out expired wikis 
    request.cursor.execute("""DELETE from wikisPending
                              where written_time <= %(timevalid)s""",
                           d, isWrite=True)
    return state

def _clearAuthCode(request, wikiname, code):
    d = {'wiki_name':wikiname, 'code':code}
    request.cursor.execute("""DELETE from wikisPending
                              where code=%(code)s and
                                    wiki_name=%(wiki_name)s""",
                           d, isWrite=True)

def send_validation_email(wikiname, request):
    if not config.mail_smarthost:
        msg = ("This wiki is not enabled for mail processing. "
               "Contact the owner of the wiki, who can enable email.")
    elif not request.isPOST():
        msg = "Use the interactive interface to change settings!"
    # check whether the user has an email address
    elif not request.user.email:
        msg = ("You didn't enter an email address in your profile. "
               "Select settings in the upper right corner and enter a "
               "valid email address.")
    else:
        code = _createCode(request)
        text = ("To create your wiki, %s, follow go to this URL: "
                "%s?action=new_wiki&wikiname=%s&code=%s . "
                "Note that this magic wiki-creating URL will expire in "
                "30 minutes." % (wikiname, farm.getBaseFarmURL(request),
                                 wikiname, code))
        mailok, msg = mail.sendmail(request, [request.user.email], 
                                    "Creating your wiki..", text,
                                    mail_from=config.mail_from)
        msg = ("An email with instructions has been sent to your email "
               "address, %s.  Check your mail!" % request.user.email)

    return msg

def has_valid_email_link(request):
    if (request.form.has_key('wikiname') and request.form['wikiname'][0] and
        request.form.has_key('code') and request.form['code'][0]):
        wikiname = request.form['wikiname'][0]
        code = request.form['code'][0]
        if _isValidCode(request, wikiname, code):
            return code

    return False

def execute(pagename, request):
    from Sycamore.PageEditor import PageEditor
    _ = request.getText
    actname = __name__.split('.')[-1]
    page = Page(pagename, request)
    msg = None
    form = request.form
    wikiname = None
    
    if not config.wiki_farm or not config.allow_web_based_wiki_creation:
        return page.send_page(msg='You are not allowed to create new wikis.')
    if not request.user.valid:
        return page.send_page(msg='You must be logged in to create new wikis.')

    if do_email_auth:
        if request.form.has_key('send_email') and request.form['send_email'][0]:
            if (not request.form.has_key('wikiname') or not
                request.form['wikiname'][0]):
                return page.send_page(msg='Missing wiki name.')
            wikiname = request.form['wikiname'][0].lower()
            if not farm.isValidWikiName(wikiname):
                msg = ('Wiki creation failed because the wiki name "%s" is '
                       'invalid.  You may only use the numbers 0-9, the '
                       'letters a-z, and the dash "-" in a wiki name.' %
                       wikiname)
            elif wikiutil.isInFarm(wikiname, request):
                msg = 'Wiki "%s" already exists!' % wikiname 
            else:
                msg = send_validation_email(wikiname, request)
            return page.send_page(msg=msg)
        email_code = has_valid_email_link(request)
        if not email_code:
            return page.send_page(msg=("Invalid email link. "
                                       "To create a wiki you must follow the link send to your email account."))
        
    if form.has_key('wikiname') and form['wikiname'][0]:
        can_create_wiki = False
        wikiname = form['wikiname'][0].lower()
        if do_email_auth:
            if not config.captcha_support:
                can_create_wiki = True
            elif form.has_key('captcha_id') and form.has_key('captcha_code'):
                this_captcha = captcha.Captcha(page, id=form['captcha_id'][0])
                if this_captcha.check(form['captcha_code'][0]):
                    can_create_wiki = True
                else:
                    msg = ('Human verification was incorrect.  '
                           'Please try again!')
            else:
                if form.has_key('audio'):
                    type = 'wav'
                else:
                    type = 'png'
                captcha.send_captcha(page, wikiname, actname, email_code, type)
                return
        else:
            can_create_wiki = True

        if can_create_wiki:
            msg = farm.create_wiki(wikiname, request.user.name, request)
            if do_email_auth:
                _clearAuthCode(request, wikiname, email_code)
            if msg:
                # there was a problem
                return page.send_page(msg=msg)

            farm.add_wiki_to_watch(wikiname, request) 

            formatter = Formatter(request)
            wiki_location = farm.link_to_wiki(wikiname, formatter)
            msg = (
                'Wiki "%s" created successfully! '
                'Follow this link to get to your wiki:\n'
                '<p>\n'
                '%s\n'
                '</p>\n'
                '<p>\n'
                'The wiki was added to your list of watched wikis '
                '(change in '
                    '<a href="%sUser_Settings">your account settings</a>).\n'
                '</p>' %
                (wikiname, wiki_location, farm.getBaseFarmURL(request)))

    return page.send_page(msg=msg)
