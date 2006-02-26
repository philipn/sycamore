# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - PageEditor class

    @copyright: 2005-2006 Philip Neustrom, <philipn@gmail.com>, 2000-2004 by J?rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, time, urllib, string
from LocalWiki import caching, config, user, util, wikiutil, wikidb
from LocalWiki.Page import Page
from LocalWiki.widget import html
from LocalWiki.logfile import editlog, eventlog
import LocalWiki.util.web
import LocalWiki.util.mail
import LocalWiki.util.datetime
import xml.dom.minidom



#############################################################################
### Javascript code for editor page
#############################################################################

def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

#############################################################################
### PageEditor - Edit pages
#############################################################################
class PageEditor(Page):
    """Editor for a wiki page."""

    # exceptions for .saveText()
    class SaveError(Exception):
        pass
    class AccessDenied(SaveError):
        pass
    class Immutable(AccessDenied):
        pass
    class NoAdmin(AccessDenied):
        pass
    class EmptyPage(SaveError):
        pass
    class Unchanged(SaveError):
        pass
    class EditConflict(SaveError):
        pass

    def __init__(self, page_name, request, **keywords):
        """
        Create page editor object.
        
        @param page_name: name of the page
        @param request: the request object
        @keyword do_revision_backup: if 0, suppress making a page backup per revision
        """
        self.request = request
        self._ = request.getText
        Page.__init__(self, page_name, request, **keywords)

        self.do_revision_backup = keywords.get('do_revision_backup', 1)
        #self.do_editor_backup = keywords.get('do_editor_backup', 1)


    def sendEditor(self, **kw):
        """
        Send the editor form page.

        @keyword preview: if given, show this text in preview mode
        @keyword staytop: don't go to #preview
        @keyword comment: comment field (when preview is true)
	@keyword had_conflict: we had an edit conflict on a save.
        """
        import re

        try:
            from LocalWiki.action import SpellCheck
        except ImportError:
            SpellCheck = None

        form = self.request.form
        _ = self._
        self.request.http_headers([("Content-Type", "text/html")] + self.request.nocache)
        msg = None
        preview = kw.get('preview', None)
        emit_anchor = not kw.get('staytop', 0)

        from LocalWiki.formatter.text_html import Formatter
        self.request.formatter = Formatter(self.request, store_pagelinks=1, preview=preview)

        base_uri = "%s?action=edit" % wikiutil.quoteWikiname(self.page_name)
        backto = form.get('backto', [None])[0]
        if backto:
            base_uri += '&amp;' + util.web.makeQueryString(backto=backto)

        # check edit permissions
        if not self.request.user.may.edit(self):
            msg = _('You are not allowed to edit this page.')
        elif self.prev_date:
            # Trying to edit an old version, this is not possible via
            # the web interface, but catch it just in case...
            msg = _('Cannot edit old revisions!')

        # Did one of the prechecks fail?
        if msg and not kw.get('had_conflict', None):
            self.send_page(msg=msg)
            return

        # check for preview submit
        if preview is None:
            title = _('Edit "%(pagename)s"')
        else:
            title = _('Preview of "%(pagename)s"')
            self.set_raw_body(preview.replace("\r", ""), 1)

	page_needle = self.page_name
        if config.allow_subpages and page_needle.count('/'):
          page_needle = '/' + page_needle.split('/')[-1]
        link = '%s/%s?action=fullsearch&amp;value=%s&amp;literal=1&amp;case=1&amp;context=40' % (
         self.request.getScriptname(),
         wikiutil.quoteWikiname(self.page_name),
         urllib.quote_plus(page_needle, ''))

        wikiutil.send_title(self.request,
            self.page_name,
            pagename=self.page_name,
	    link=link,
	    strict_title='Editing "%s"' % self.page_name,
        )
        
        self.request.write('<div id="content">\n') # start content div
        
        # get request parameters
	text_rows = None
        if form.has_key('rows'):
	  text_rows = int(form['rows'][0])
	  if self.request.user.valid:
	    # possibly update user's pref
	    if text_rows != self.request.user.edit_rows:
	      self.request.user.edit_rows = text_rows
	      self.request.user.save()
	else:
          text_rows = config.edit_rows
          if self.request.user.valid: text_rows = int(self.request.user.edit_rows)

        if form.has_key('cols'):
            text_cols = int(form['cols'][0])
	    if self.request.user.valid:
	      # possibly update user's pref
	      if text_rows != self.request.user.edit_rows:
	        self.request.user.edit_rows = text_rows
	        self.request.user.save()
	else:
            text_cols = 80
            if self.request.user.valid: text_cols = int(self.request.user.edit_cols)

        # check datestamp (version) of the page our edit is based on
        if preview is not None:
            # propagate original datestamp
            mtime = float(form['datestamp'][0])

            # did someone else change the page while we were editing?
            conflict_msg = None
            if not self.exists():
                # page does not exist, are we creating it?
                if mtime:
                    conflict_msg = _('Someone else <b>deleted</b> this page while you were editing!')
            elif mtime != self.mtime():
                conflict_msg = _('Someone else changed this page while you were editing.')
                # merge conflicting versions
                allow_conflicts = 1
                from LocalWiki.util import diff3
                savetext = self.get_raw_body()
                original_text = Page(self.page_name, self.request, prev_date=mtime).get_raw_body()
                saved_text = Page(self.page_name, self.request).get_raw_body()
                verynewtext, had_conflict = diff3.text_merge(original_text, saved_text, savetext,
                marker1='----- /!\ Edit conflict! Other version: -----\n',
	        marker2='----- /!\ Edit conflict! Your version: -----\n',
                marker3='----- /!\ End of edit conflict -----\n')

                if had_conflict:
                    conflict_msg = _("""%s
There was an <b>edit conflict between your changes!</b><p>Please review the conflicts and merge the changes.</p>""" % conflict_msg)
		    mtime = self.mtime()
                    self.set_raw_body(verynewtext)
	        else:
		   conflict_msg = _("""%s
Your changes were sucessfully merged!""" % conflict_msg)

            if conflict_msg:
                self.request.write('<div id="message">%s</div>' % conflict_msg)
                emit_anchor = 0 # make this msg visible!
        elif self.exists():
            # datestamp of existing page
            mtime = self.mtime()
        else:
            # page creation
            mtime = 0

        # output message
        message = kw.get('msg', '')
        if message:
            self.request.write('<div id="message">%s</div>' % (message))

        # get the text body for the editor field
        if form.has_key('template'):
            # "template" parameter contains the name of the template page
            template_page = wikiutil.unquoteWikiname(form['template'][0])
            raw_body = Page(template_page, self.request).get_raw_body()
            if raw_body:
                self.request.write(_("[Content of new page loaded from %s]") % (template_page,), '<br>')
            else:
                self.request.write(_("[Template %s not found]") % (template_page,), '<br>')
        else:
            raw_body = self.get_raw_body()

        # send text above text area
        template_param = ''
        if form.has_key('template'):
            template_param = '&amp;template=' + form['template'][0]
        self.request.write(_('<div class="pageEditInfo">editor size:'))
        self.request.write('<a href="%s&amp;rows=%d&amp;cols=60%s">%s</a>' % (
            base_uri, text_rows + 10, template_param, '+'))
        self.request.write(',<a href="%s&amp;rows=%s&amp;cols=60%s">%s</a>' % (
            base_uri, text_rows - 10, template_param, '-'))

        self.request.write('</div>')
        
        # button toolbar
        self.request.write('<p>')
	self.request.write("<script type=\"text/javascript\">var buttonRoot = '%s';</script>" % (os.path.join(config.url_prefix, self.request.user.theme_name, 'img', 'buttons')))
	if self.request.user.name:
	  self.request.write("""<script type=\"text/javascript\">var userPageLink = '["%s"]';</script>""" % (self.request.user.name))
	else:
	  self.request.write("""<script type=\"text/javascript\">var userPageLink = '%s';</script>""" % (self.request.remote_addr))
	  
        self.request.write("<script type=\"text/javascript\" src=\"%s/wiki/edit.js\"></script>" % (config.web_dir))
        # send form
        self.request.write('<form name="editform" method="post" action="%s/%s#preview">' % (
            self.request.getScriptname(),
            wikiutil.quoteWikiname(self.page_name),
            ))

        self.request.write(str(html.INPUT(type="hidden", name="action", value="savepage")))
        if backto:
            self.request.write(str(html.INPUT(type="hidden", name="backto", value=backto)))

        # generate default content
        if not raw_body:
            raw_body = _('Describe %s here.') % (self.page_name,)

        # replace CRLF with LF
        raw_body = self._normalize_text(raw_body)

        # make a preview backup?
        #if preview is not None:
        #    # make backup on previews
        #    self._make_backup(raw_body)

        # send datestamp (version) of the page our edit is based on
        self.request.write('<input type="hidden" name="datestamp" value="%s">' % (repr(mtime)))

        # Print the editor textarea and the save button
        self.request.write('<textarea id="savetext" name="savetext" rows="%d" cols="%d" style="width:100%%">%s</textarea>'
            % (text_rows, text_cols, wikiutil.escape(raw_body)))
        self.request.write('</p>')

        self.request.write("""<p> %s<br><input type="text" class="formfields" name="comment" value="%s" size="%d" maxlength="80" style="width:100%%"></p>""" %
                (_("<font size=\"+1\">Please comment about this change:</font>"), wikiutil.escape(kw.get('comment', ''), 1), text_cols))

        # category selection
        #cat_pages = wikiutil.filterCategoryPages(wikiutil.getPageList(config.text_dir))
        #cat_pages.sort()
        #cat_pages.insert(0, ('', _('<No addition>')))
        #self.request.write("<p>", _('Make this page belong to category %(category)s') % {
        #    'category': str(util.web.makeSelection('category', cat_pages)),
        #})

        # button bar
        button_spellcheck = (SpellCheck and
            '<input type="submit" class="formbutton" name="button_spellcheck" value="%s">'
                % _('Check Spelling')) or ''

        save_button_text = _('Save Changes')
        cancel_button_text = _('Cancel')
        
        self.request.write("</p>")
            

#        if config.page_license_enabled:
#            self.request.write('<p><em>', _(
#"""By hitting <strong>%(save_button_text)s</strong> you put your changes under the %(license_link)s.
#If you don't want that, hit <strong>%(cancel_button_text)s</strong> to cancel your changes.""") % {
#                'save_button_text': save_button_text,
#                'cancel_button_text': cancel_button_text,
#                'license_link': wikiutil.getSysPage(self.request, config.page_license_page).link_to(self.request),
#            }, '</em></p>')
        
        #fixedName = re.sub("'","_27",self.page_name)
        show_applet = True
        if wikiutil.isSystemPage(self.request, self.page_name):
          show_applet = False
        mapButton = ""
        mapHtml = ""
        relative_dir = ''
        if config.relative_dir:
          relative_dir = '/' + config.relative_dir
        if show_applet:
          mapButton = '<input id="show" class="formbutton" type="button" value="Edit Map" onclick="doshow();"/><input class="formbutton" id="hide" style="display: none;" type="button" value="Hide Map" onclick="dohide();"/>'
          mapHtml = '<br><table style="display: none;" id="map" cellspacing="0" cellpadding="0" width="810" height="460"><tr><td bgcolor="#ccddff" style="border: 1px dashed #aaaaaa;"><applet code="WikiMap.class" archive="%s/wiki/map.jar, %s/wiki/txp.jar" height=460 width=810 border="1"><param name="map" value="%s/wiki/map.xml"><param name="points" value="%s/Map?action=mapPointsXML"><param name="set" value="true"><param name="highlight" value="%s"><param name="wiki" value="%s">You do not have Java enabled.</applet></td></tr></table>' % (config.web_dir, config.web_dir, config.web_dir, relative_dir, self.page_name, relative_dir)
        
        self.request.write('''
<table border="0" cellspacing="0"><tr height="30"><td nowrap><font size="3">
<input type="submit" class="bigbutton" name="button_preview" value="%s">
<input type="submit" class="formbutton" name="button_save" value="%s">
<input type="submit" class="formbutton" name="button_cancel" value="%s">
</td><td width="12">&nbsp;</td><td bgcolor="#ccddff" style="border: 1px dashed #AAAAAA;">
&nbsp;&nbsp;%s
<input type="button" class="formbutton" onClick="window.open('%s/%s?action=Files', 'images', 'width=800,height=600,scrollbars=1')" value="Images">
%s
<input type="button" class="formbutton" onClick="location.href='%s/%s?action=DeletePage'" value="Delete">
<input type="button" class="formbutton" onClick="location.href='%s/%s?action=Rename'" value="Rename">&nbsp;&nbsp;</td></tr></table>
%s
''' % (_('Preview'), save_button_text, cancel_button_text, mapButton, relative_dir, wikiutil.quoteWikiname(self.page_name), button_spellcheck, relative_dir, wikiutil.quoteWikiname(self.page_name), relative_dir, wikiutil.quoteWikiname(self.page_name),mapHtml))

        #if config.mail_smarthost:
        #    self.request.write('''<input type="checkbox" name="notify" value="1"%s><label>%s</label>''' % (
        #        ('', ' checked="checked"')[preview is None or (form.get('notify',['0'])[0] == '1')],
        #        _('Send mail notification'),
        #    ))

        self.request.write('By clicking "Save Changes" you are agreeing to release your contribution under the <a href="http://creativecommons.org/licenses/by/2.0/">Creative Commons-By license</a>, unless noted otherwise. <b>Do not submit copyrighted work (including images) without permission.</b>  For more information, see <a href="%s/Copyrights">Copyrights</a>.' % relative_dir)

        badwords_re = None
        if preview is not None:
            if SpellCheck and (
                    form.has_key('button_spellcheck') or
                    form.has_key('button_newwords')):
                badwords, badwords_re, msg = SpellCheck.checkSpelling(self, self.request, own_form=0)
                self.request.write("<p>%s</p>" % msg)
        self.request.write("</form>")


        # QuickHelp originally by Georg Mischler <schorsch@lightingwiki.com>
        self.request.write('<h2>Editing quick-help</h2>\n<dl><div style="float: right; margin: 10px; border: 1px solid; padding: 3pt;">See <b>%s</b> for more information.</div>' % (Page("Help On Editing", self.request).link_to()) + _("""<dt>Emphasis:</dt>
<dd>''<em>italics</em>''; '''<strong>bold</strong>'''; '''''<strong><em>bold italics</em></strong>''''';
    ''<em>mixed '''<strong>bold</strong>''' and italics</em>''; ---- horizontal rule.</dd>
<dt>Headings:</dt>
<dd>= Title 1 =; == Title 2 ==; === Title 3 ===;
    ==== Title 4 ====; ===== Title 5 =====.</dd>
<dt>Lists:</dt>
<dd>space and one of * bullets; 1., a., A., i., I. numbered items;
    1.#n start numbering at n; space alone indents.</dd>
<dt>Links:</dt>
<dd>["brackets and double quotes"]; ["the exact page name" label];
    url; [url]; [url label].</dd>
<dt>Tables:</dt>
<dd>|| cell text |||| cell text spanning two columns ||;
    no trailing white space allowed after tables or titles.</dd>
""") + '</dl>')

        if preview is not None:
	    if not emit_anchor:
	      preview_name = "previewHide"
	    else: preview_name = "preview"
            self.request.write('<div id="%s" class="preview">' % preview_name)
            self.send_page(content_only=1, hilite_re=badwords_re, preview=preview)
            self.request.write('</div>')

        self.request.write('</div>\n') # end content div

        self.request.theme.emit_custom_html(config.page_footer1)
        self.request.theme.emit_custom_html(config.page_footer2)


    def sendCancel(self, newtext, datestamp):
        """
        User clicked on Cancel button.
        
        @param newtext: the edited text (which has been cancelled)
        @param datestamp: ...
        """
        _ = self._
        #self._make_backup(self._normalize_text(newtext))

        backto = self.request.form.get('backto', [None])[0]
        page = backto and Page(backto, self.request) or self
        page.send_page(msg=_('Edit was cancelled.'))


    def deletePage(self, comment=None):
        """
        Delete the page (but keep the backups)
        
        @param comment: Comment given by user
        """
        # !!! Need to aquire lock for this, and possibly BEFORE user pressed DELETE.
        # !!! Possibly with shorter timeout.

        # First save a final backup copy of the current page
        # (recreating the page allows access to the backups again)
        try:
            self.saveText("deleted", '0', comment=comment or '', action='DELETE')
        except self.SaveError:
            # XXXX Error handling
            pass
        # Then really delete it
	self.request.cursor.execute("DELETE from curPages where name=%(page_name)s", {'page_name':self.page_name}, isWrite=True)
	from LocalWiki import caching
	cache = caching.CacheEntry(self.page_name, self.request)
	cache.clear()
	self.request.req_cache['pagenames'][self.page_name] = False

	# remove entry from the search databases
	os.spawnl(os.P_WAIT, config.app_dir + '/remove_from_index', config.app_dir + '/remove_from_index', '%s' % wikiutil.quoteFilename(self.page_name))

    def _sendNotification(self, comment, emails, email_lang, oldversions):
        """
        Send notification email for a single language.
        @param comment: editor's comment given when saving the page
        @param emails: list of email addresses
        @param email_lang: language of emails
        @param oldversions: old versions of this page
        @rtype: int
        @return: sendmail result
        """
        _ = lambda s, r=self.request, l=email_lang: r.getText(s, lang=l)

        mailBody = _("Dear Wiki user,\n\n"
            'You have subscribed to a wiki page or wiki category on "%(sitename)s" for change notification.\n\n'
            "The following page has been changed by %(editor)s:\n"
            "%(pagelink)s\n\n") % {
                'editor': user.getUserIdentification(self.request),
                'pagelink': self.request.getQualifiedURL(self.url(self.request)),
                'sitename': config.sitename or self.request.getBaseURL(),
        }

        if comment:
            mailBody = mailBody + \
                _("The comment on the change is:\n%(comment)s\n\n") % {'comment': comment}

        # append a diff
        if not oldversions:
            mailBody = mailBody + \
                _("No older revisions of the page stored, diff not available.")
        else:
            newpage = os.path.join(config.text_dir, wikiutil.quoteFilename(self.page_name))
            oldpage = os.path.join(config.backup_dir, oldversions[0])

            rc, page_file, backup_file, lines = wikiutil.pagediff(oldpage, newpage)
            if lines and len(lines) > 2:
                mailBody = "%s%s\n%s" % (
                    mailBody, ("-" * 78), ''.join(lines[2:]))
            else:
                mailBody = mailBody + _("No differences found!\n")
                if rc:
                    mailBody = mailBody + '\n\n' + \
                        _('The diff function returned with error code %(rc)s!') % {'rc': rc}

        return util.mail.sendmail(self.request, emails,
            _('[%(sitename)s] Update of "%(pagename)s"') % {
                'sitename': config.sitename or "Wiki",
                'pagename': self.page_name,
            },
            mailBody, mail_from=config.mail_from)
            # was: self.request.user.email, but we don't want to disclose email


    def _notifySubscribers(self, comment):
        """
        Send email to all subscribers of this page.
        
        @param comment: editor's comment given when saving the page
        @rtype: string
        @return: message, indicating success or errors.
        """
        _ = self._
        subscribers = self.getSubscribers(self.request, return_users=1)

        wiki_is_smarter_than_its_users = _("You will not be notified of your own changes!") + '<br>'

        if subscribers:
            # get a list of old revisions, and append a diff
            oldversions = wikiutil.getBackupList(config.backup_dir, self.page_name)

            # send email to all subscribers
            results = [_('Status of sending notification mails:')]
            for lang in subscribers.keys():
                emails = map(lambda u: u.email, subscribers[lang])
                names  = map(lambda u: u.name,  subscribers[lang])
                mailok, status = self._sendNotification(comment, emails, lang, oldversions)
                recipients = ", ".join(names)
                results.append(_('[%(lang)s] %(recipients)s: %(status)s') % {
                    'lang': lang, 'recipients': recipients, 'status': status})

            return wiki_is_smarter_than_its_users + '<br>'.join(results)

        return wiki_is_smarter_than_its_users + _('Nobody subscribed to this page, no mail sent.')


    def _user_variable(self):
        """
        If user has a profile return the user name from the profile
        else return the remote address or "<unknown>"

        If the user name contains spaces it is wiki quoted to allow
        links to the wiki user homepage (if one exists).
        
        @rtype: string
        @return: wiki freelink to user's homepage or remote address
        """
        username = self.request.user.name
        if username and \
                username.count(' ') and Page(username, self.request).exists():
            username = '["%s"]' % username
        return user.getUserIdentification(self.request, username)


    def _expand_variables(self, text):
        """
        Expand @VARIABLE@ in `text`and return the expanded text.
        
        @param text: current text of wikipage
        @rtype: string
        @return: new text of wikipage, variables replaced
        """
        #!!! TODO: Allow addition of variables via moin_config (and/or a text file)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", util.datetime.tmtuple())
        system_vars = {
            'PAGE': lambda s=self: s.page_name,
            'TIME': lambda t=now: "[[DateTime(%s)]]" % t,
            'DATE': lambda t=now: "[[Date(%s)]]" % t,
            'USERNAME': lambda s=self: s._user_variable(),
            'USER': lambda s=self: "-- %s" % (s._user_variable(),),
            'SIG': lambda s=self, t=now: "-- %s [[DateTime(%s)]]"
                % (s._user_variable(), t,),
        }

        if self.request.user.valid and self.request.user.name:
            if self.request.user.email:
                system_vars['MAILTO'] = lambda u=self.request.user: \
                    "[mailto:%s %s]" % (u.email, u.name)
            # users can define their own vars via UserHomepage/MyDict
            uservarspagename = self.request.user.name + "/MyDict"
            dicts = self.request.dicts
            if dicts.has_dict(uservarspagename):
                userdict = dicts.dict(uservarspagename)
                for key in userdict.keys():
                    text = text.replace('@%s@' % key, userdict[key])
                    
        #!!! TODO: Use a more stream-lined re.sub algorithm
        for name, val in system_vars.items():
            text = text.replace('@%s@' % name, val())
        return text


    def _normalize_text(self, newtext, **kw):
        """
        Normalize CRLF to LF, and handle trailing whitespace.
        
        @param newtext: new text of the page
        @keyword stripspaces: if 1, strip spaces from text
        @rtype: string
        @return: normalized text
        """
        # remove CRs (so Win32 and Unix users save the same text)
        newtext = newtext.replace("\r", "")

        # possibly strip trailing spaces
        if True:
            newtext = '\n'.join([line.rstrip() for line in newtext.splitlines()])

        # add final newline if not present in textarea, better for diffs
        # (does not include former last line when just adding text to
        # bottom; idea by CliffordAdams)
        if newtext and newtext[-1] != '\n':
            newtext = newtext + '\n'

        return newtext


    #def _make_backup(self, newtext, **kw):
    #    """
    #    Make a backup of text before saving and on previews, if user
    #    has a homepage. Return URL to backup if one is made.
    #    
    #    @param newtext: new text of the page
    #    @keyword ...:...
    #    @rtype: string
    #    @return: url of page backup
    #    """
    #    _ = self._
    #    # check for homepage
    #    pg = wikiutil.getHomePage(self.request)
    #    if not pg:
    #        return None

    #    if config.allow_subpages:
    #        delimiter = "/"
    #    else:
    #        delimiter = ""
    #    backuppage = PageEditor(pg.page_name + delimiter + "MoinEditorBackup", self.request, do_revision_backup=0)
    #    if config.acl_enabled:
    #        intro = "#acl %s:read,write,delete\n" % self.request.user.name
    #    else:
    #        intro = ""
    #    pagename = self.page_name
    #    ourtime = time.time()
    #    date = self.request.user.getFormattedDateTime(ourtime)
    #    intro += _('## backup of page "%(pagename)s" submitted %(date)s') % {
    #        'pagename': pagename, 'date': date,} + '\n'

    #   	db = wikidb.connect()
    #    cursor = db.cursor()
    #    if backuppage.exists():
    #       cursor.execute("start transaction;")
    #       cursor.execute("UPDATE curPages set text=%s, editTime=%s, userEdited=%s where name=%s", (intro+newtext, ourtime, self.request.user.name, backuppage.page_name))
    #       cursor.execute("commit;")
    #    else:
    #       cursor.execute("INSERT into curPages set name=%s, text=%s, editTime=%s, userEdited=%s", (backuppage.page_name, intro+newtext, ourtime, self.request.user.name))

    #    return backuppage.url(self.request)

    def _write_to_db(self, text, action, comment, ip):
	"""
	Write the text to the page tables in the database.
	"""
	ourtime = time.time()
	self.request.cursor.execute("SELECT name from curPages where name=%(page_name)s", {'page_name':self.page_name})
	exists = self.request.cursor.fetchone()
        if not self.request.user.id:
            user_id = 'anon:%s' % ip
        else:
            user_id = self.request.user.id

	if exists:
		self.request.cursor.execute("UPDATE curPages set name=%(page_name)s, text=%(text)s, editTime=%(ourtime)s, userEdited=%(id)s where name=%(page_name)s", {'page_name': self.page_name, 'text': text, 'ourtime': ourtime, 'id': user_id}, isWrite=True)
	else:
		self.request.cursor.execute("INSERT into curPages values (%(page_name)s, %(text)s, NULL, %(ourtime)s, NULL, %(id)s)", {'page_name':self.page_name, 'text':text, 'ourtime':ourtime, 'id':user_id}, isWrite=True)

	# then we need to update the allPages table for Recent Changes and page-centric Info.

	self.request.cursor.execute("INSERT into allPages (name, text, editTime, userEdited, editType, comment, userIP) values (%(page_name)s, %(text)s, %(ourtime)s, %(id)s, %(action)s, %(comment)s, %(ip)s)", {'page_name':self.page_name, 'text':text, 'ourtime':ourtime, 'id':user_id, 'action':action, 'comment':wikiutil.escape(comment),'ip':ip}, isWrite=True)

	import caching
	cache = caching.CacheEntry(self.page_name, self.request)
	cache.clear()
	# clear possible dependencies (e.g. [[Include]])
	for pagename in caching.depend_on_me(self.page_name, self.request):
	  caching.CacheEntry(pagename, self.request).clear()

	# set in-memory page text
	self.set_raw_body(text)


    def _write_file(self, text):
        """
        Write the text to the page file (and make a backup of old page).
        
        @param text: text to save for this page
        @rtype: int
        @return: mtime of new page
        """
        from LocalWiki.util import filesys
        is_deprecated = text[:11].lower() == "#deprecated"

	#DBFIX need to KILL all file dependencies once we have the allPages table as well
        # save to tmpfile
        tmp_filename = self._tmp_filename()
        tmp_file = open(tmp_filename, 'wb')
        # XXX UNICODE fix needed
        tmp_file.write(text)
        tmp_file.close()
        page_filename = self._text_filename()

        if not os.path.isdir(config.backup_dir):
            os.mkdir(config.backup_dir, 0777 & config.umask)
            os.chmod(config.backup_dir, 0777 & config.umask)
        log = editlog.EditLog(config.data_dir + '/pages/' + wikiutil.quoteFilename(self.page_name) + '/last-edited')
	ed_time = 0
        for pageline in log.lastline():
                line = pageline
		ed_time = line.ed_time
                break
	if not ed_time:
		if os.path.exists(page_filename):
			ed_time = os.path.getmtime(page_filename)
		else:
			ed_time = int(time.time())
		
        if os.path.isfile(page_filename) and not is_deprecated and self.do_revision_backup:
            filesys.rename(page_filename, os.path.join(config.backup_dir,
                wikiutil.quoteFilename(self.page_name) + '.' + str(int(ed_time))))

        # set in-memory content
        self.set_raw_body(text)

        # replace old page by tmpfile
        os.chmod(tmp_filename, 0666 & config.umask)
        filesys.rename(tmp_filename, page_filename)
        return os.path.getmtime(page_filename)

    #def build_index(self):
    #    """
    #    Builds the index with all the pages. . This should hopefully rarely be run.
    #    """
    #    forked_id = 0
    #    pages = list(wikiutil.getPageList())
    #    for page in pages:
    #            p = Page(page)
    #            #add_to_index(wikiutil.quoteWikiname(p.page_name), p.get_raw_body())
    #            os.spawnl(os.P_WAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index', '%s' % wikiutil.quoteWikiname(p.page_name), '%s' % wikiutil.quoteWikiname(p.get_raw_body()))


    def saveText(self, newtext, datestamp, **kw):
        """
        Save new text for a page.

        @param newtext: text to save for this page
        @param datestamp: ...
        @keyword stripspaces: strip whitespace from line ends (default: 0)
        @keyword notify: send email notice tp subscribers (default: 0)
        @keyword comment: comment field (when preview is true)
        @keyword action: action for editlog (default: SAVE)
        @rtype: string
        @return: error msg
        """
        _ = self._
        newtext = self._normalize_text(newtext, **kw)
        #backup_url = self._make_backup(newtext, **kw)

        #!!! need to check if we still retain the lock here
        #!!! datestamp check is not enough since internal operations use "0"

        # expand variables, unless it's a template or form page
        if not wikiutil.isTemplatePage(self.page_name):
            newtext = self._expand_variables(newtext)

        msg = ""
        if not self.request.user.may.save(self, newtext, datestamp, **kw):
            msg = _('You are not allowed to edit this page!')
            raise self.AccessDenied, msg
        elif not newtext.strip():
            msg = _('You cannot save empty pages.')
            raise self.EmptyPage, msg
        elif datestamp != '0' and datestamp < self.mtime():
            raise self.EditConflict, msg
        elif newtext == self.get_raw_body() and not self._rename_lowercase_condition():
            msg = _('You did not change the page content, not saved!')
            raise self.Unchanged, msg
	# check to see if they're renaming the page to the same thing (thus, no content change)
        elif config.acl_enabled:
	    from wikiacl import parseACL
            acl = self.getACL()
            if not acl.may(self.request, self.request.user.name, "admin") \
               and parseACL(newtext) != acl:
                msg = _("You can't change ACLs on this page since you have no admin rights on it!")
                raise self.NoAdmin, msg
            
        # save only if no error occured (msg is empty)
        if not msg:
            # set success msg
            msg = _("Thank you for your changes. Your attention to detail is appreciated. ")

            # determine action for edit logging
            action = kw.get('action', 'SAVE')
            if action=='SAVE' and not self.exists():
                action = 'SAVENEW'
               
            # write the page file
            mtime = self._write_to_db(newtext, action, kw.get('comment',''), self.request.remote_addr)

            if self._acl_cache.has_key(self.page_name):
                del self._acl_cache[self.page_name]

	    # see if we need to update the group dictionary
	    if wikiutil.isGroupPage(self.page_name):
	      from LocalWiki import wikidicts
              dicts = wikidicts.GroupDict(self.request)
              dicts.scandicts()
	      dicts.addgroup(self.page_name)
	      dicts.save()

            # we'll try to change the stats early-on
            if self.request.user.name:
                self.userStatAdd(self.request.user.name, action, self.page_name)

            # we quote the pagetext so we can pass it as a single argument and then have the process run without us paying it any attention
            os.spawnl(os.P_WAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index', wikiutil.quoteWikiname(self.page_name), wikiutil.quoteWikiname(newtext))

	    # we do this so we don't return another copy of the page to the user!

            return msg

    def _rename_lowercase_condition(self):
        given_name = self.page_name 
	current_name = self.getName()
	# implies existance
	if current_name:
	  if (current_name != given_name) and (current_name.lower() == given_name.lower()):
	    return True

	return False
	  


    def notifySubscribers(self, **kw):
        msg = ''
        #if config.mail_smarthost and kw.get('notify', 0):
        msg = msg + self._notifySubscribers(kw.get('comment', ''))
        return msg

    def userStatAdd(self, username, action, pagename):
        self.request.cursor.execute("SELECT created_count, edit_count from users where name=%(username)s", {'username':username})
        result = self.request.cursor.fetchone()
       
        created_count = result[0]
        edit_count = result[1]

        edit_count += 1
        if action == 'SAVENEW':	
            created_count += 1
        last_page_edited = pagename
        last_edit_date = time.time()
        self.request.cursor.execute("UPDATE users set created_count=%(created_count)s, edit_count=%(edit_count)s, last_page_edited=%(last_page_edited)s, last_edit_date=%(last_edit_date)s where name=%(username)s", {'created_count':created_count, 'edit_count':edit_count, 'last_page_edited':last_page_edited, 'last_edit_date':last_edit_date, 'username':username}, isWrite=True)


def is_word_in_file(file, word):
      """
      Pass me a file location and i tell you if word is in that file
      """
      f = open(file)
      lines = f.readlines()
      f.close()
      for line in lines:
         if string.find(line, word) >= 0:
            return 1
      return 0

def on_same_line(file, word1, word2):
      f = open(file)
      lines = f.readlines()
      f.close()
      for line in lines:
         if string.find(line, word1) >= 0 and string.find(line, word2) >= 0:
            return 1
      return 0

