# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - PageEditor class

    @copyright: 2000-2004 by J?rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, time, urllib, string
from LocalWiki import caching, config, user, util, wikiutil
from LocalWiki.Page import Page
from LocalWiki.widget import html
from LocalWiki.logfile import editlog, eventlog
import LocalWiki.util.web
import LocalWiki.util.mail
import LocalWiki.util.datetime
import xml.dom.minidom
import cPickle



#############################################################################
### Javascript code for editor page
#############################################################################

# This code is internal to allow I18N, else we'd use a .js file;
# we avoid the "--" operator to make this XHTML happy!
_countdown_js = """
<script type="text/javascript">
var timeout_min = %(lock_timeout)s;
var state = 0; // 0: start; 1: long count; 2: short count; 3: timeout; 4/5: blink
var counter = 0, step = 1, delay = 1;

function countdown() {
    // change state if counter is down
    if (counter <= 1) {
        state += 1
        if (state == 1) {
            counter = timeout_min
            step = 1
            delay = 60000
        }
        if (state == 2) {
            counter = 60
            step = 5
            delay = step * 1000
        }
        if (state == 3 || state == 5) {
            window.status = "%(lock_expire)s"
            state = 3
            counter = 1
            step = 1
            delay = 500
        }
        if (state == 4) {
            // blink the above text
            window.status = " "
            counter = 1
            delay = 250
        }
    }

    // display changes
    if (state < 3) {
        var msg
        if (state == 1) msg = "%(lock_mins)s"
        if (state == 2) msg = "%(lock_secs)s"
        window.status = msg.replace(/#/, counter)
    }
    counter -= step

    // Set timer for next update
    setTimeout("countdown()", delay)
}
</script>
"""
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
        @keyword do_editor_backup: if 0, suppress making of HomePage/MoinEditorBackup per edit
        """
        self.request = request
        self._ = request.getText
        Page.__init__(self, page_name, **keywords)

        self.do_revision_backup = keywords.get('do_revision_backup', 1)
        self.do_editor_backup = keywords.get('do_editor_backup', 1)

        self.lock = PageLock(page_name, request)


    def sendEditor(self, **kw):
        """
        Send the editor form page.

        @keyword preview: if given, show this text in preview mode
        @keyword staytop: don't go to #preview
        @keyword comment: comment field (when preview is true)
        """
        import re

        try:
            from LocalWiki.action import SpellCheck
        except ImportError:
            SpellCheck = None

        form = self.request.form
        _ = self._
        self.request.http_headers(self.request.nocache)
        msg = None
        edit_lock_message = None
        preview = kw.get('preview', None)
        emit_anchor = not kw.get('staytop', 0)

        from LocalWiki.formatter.text_html import Formatter
        self.request.formatter = Formatter(self.request, store_pagelinks=1)

        base_uri = "%s?action=edit" % wikiutil.quoteWikiname(self.page_name)
        backto = form.get('backto', [None])[0]
        if backto:
            base_uri += '&amp;' + util.web.makeQueryString(backto=backto)

        # check edit permissions
        if not self.request.user.may.edit(self.page_name):
            msg = _('You are not allowed to edit this page.')
        elif not self.isWritable():
            msg = _('Page is immutable!')
        elif self.prev_date:
            # Trying to edit an old version, this is not possible via
            # the web interface, but catch it just in case...
            msg = _('Cannot edit old revisions!')
        else:
            # try to aquire edit lock
            ok, edit_lock_message = self.lock.aquire()
            if not ok:
                # failed to get the lock
                if preview is not None:
                    edit_lock_message = _('The lock you held timed out, be prepared for editing conflicts!'
                        ) + "<br>" + edit_lock_message
                else:
                    msg = edit_lock_message

            # FIXME - not a good way to count html in a string... - especially if it got removed...
            #if edit_lock_message.count('<strong class="highlight">'):
            #    emit_anchor = 0

        # Did one of the prechecks fail?
        if msg:
            self.send_page(self.request, msg=msg)
            return

        # check for preview submit
        if preview is None:
            title = _('Edit "%(pagename)s"')
        else:
            title = _('Preview of "%(pagename)s"')
            self.set_raw_body(preview.replace("\r", ""), 1)

        # send header stuff
        lock_timeout = self.lock.timeout / 60
        lock_page = wikiutil.escape(self.page_name, quote=1)
        lock_expire = _("Your edit lock on %(lock_page)s has expired!") % {'lock_page': lock_page}
        lock_mins = _("Your edit lock on %(lock_page)s will expire in # minutes.") % {'lock_page': lock_page}
        lock_secs = _("Your edit lock on %(lock_page)s will expire in # seconds.") % {'lock_page': lock_page}
        wikiutil.send_title(self.request,
            title % {'pagename': self.split_title(self.request),},
            pagename=self.page_name,
            body_onload=self.lock.locktype and 'countdown()' or '', # broken / bug in Mozilla 1.5, when using #preview
            html_head=self.lock.locktype and (
                _countdown_js % {
                     'lock_timeout': lock_timeout,
                     'lock_expire': lock_expire,
                     'lock_mins': lock_mins,
                     'lock_secs': lock_secs,
                    }) or ''
        )
        
        self.request.write('<div id="content">\n') # start content div
        
        # get request parameters
        try:
            text_rows = int(form['rows'][0])
        except StandardError:
            text_rows = config.edit_rows
            if self.request.user.valid: text_rows = int(self.request.user.edit_rows)
        try:
            text_cols = int(form['cols'][0])
        except StandardError:
            text_cols = 80
            if self.request.user.valid: text_cols = int(self.request.user.edit_cols)

        # check datestamp (version) of the page our edit is based on
        if preview is not None:
            # propagate original datestamp
            mtime = int(form['datestamp'][0])

            # did someone else change the page while we were editing?
            conflict_msg = None
            if not self.exists():
                # page does not exist, are we creating it?
                if mtime:
                    conflict_msg = _('Someone else deleted this page while you were editing!')
            elif mtime != os.path.getmtime(self._text_filename()):
                conflict_msg = _('Someone else changed this page while you were editing!')
                # merge conflicting versions
                allow_conflicts = 1
                from LocalWiki.util import diff3
                savetext = self.get_raw_body()
                original_text = Page(self.page_name, date=str(mtime)).get_raw_body()
                saved_text = Page(self.page_name).get_raw_body()
                verynewtext = diff3.text_merge(original_text, saved_text, savetext,
                                               allow_conflicts,
                                               '----- /!\ Edit conflict! Other version: -----\n',
                                               '----- /!\ Edit conflict! Your version: -----\n',
                                               '----- /!\ End of edit conflict -----\n')
                if verynewtext:
                    conflict_msg = _("""Someone else saved this page while you were editing!
Please review the page and save then. Do not save this page as it is!
Have a look at the diff of %(difflink)s to see what has been changed."""
                    ) % {'difflink':self.link_to(self.request, querystr='action=diff&amp;date=' + str(mtime))}
                    mtime = os.path.getmtime(self._text_filename())
                    self.set_raw_body(verynewtext)
            if conflict_msg:
                self.request.write('<div id="message">%s</div>' % conflict_msg)
                emit_anchor = 0 # make this msg visible!
        elif self.exists():
            # datestamp of existing page
            mtime = os.path.getmtime(self._text_filename())
        else:
            # page creation
            mtime = 0

        # output message
        message = kw.get('msg', '')
        if edit_lock_message or message:
            self.request.write('<div id="message">%s%s</div>' % (message, edit_lock_message))

        # get the text body for the editor field
        if form.has_key('template'):
            # "template" parameter contains the name of the template page
            template_page = wikiutil.unquoteWikiname(form['template'][0])
            raw_body = Page(template_page).get_raw_body()
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
        self.request.write('<p>')
        self.request.write('<a href="%s&amp;rows=10&amp;cols=60%s">%s</a>' % (
            base_uri, template_param, _('Reduce editor size')))
        self.request.write(" | ", wikiutil.getSysPage(self.request, 'Help On Formatting').link_to(self.request))
        #self.request.write(" | ", wikiutil.getSysPage(self.request, 'InterWiki').link_to(self.request))
        if preview is not None and emit_anchor:
            self.request.write(' | <a href="#preview">%s</a>' % _('Skip to preview'))
        self.request.write(' ')
        self.request.write(_('[current page size <strong>%(size)d</strong> bytes]') % {'size': self.size()})
        self.request.write('</p>')
        
        # button toolbar
        self.request.write('<p>')
        self.request.write("<script type=\"text/javascript\" src=\"/edit.js\"></script>")
        # send form
        self.request.write('<form name="editform" method="post" action="%s/%s#preview">' % (
            self.request.getScriptname(),
            wikiutil.quoteWikiname(self.page_name),
            ))

        #self.request.write("<script type='text/javascript'>\nfunction addButton(imageFile, speedTip, tagOpen, tagClose, sampleText) {speedTip=escapeQuotes(speedTip); tagOpen=escapeQuotes(tagOpen); tagClose=escapeQuotes(tagClose); sampleText=escapeQuotes(sampleText); var mouseOver=\"\";// we can't change the selection, so we show example texts // when moving the mouse instead, until the first button is clicked if(!document.selection && !is_gecko) { // filter backslashes so it can be shown in the infobox var re=new RegExp(\"\\\\\\\\n\",\"g\"); tagOpen=tagOpen.replace(re,\"\"); tagClose=tagClose.replace(re,\"\"); mouseOver = \"onMouseover=\\\"if(!noOverwrite){document.infoform.infobox.value='\"+tagOpen+sampleText+tagClose+\"'};\\\"\"; }document.write(\"<a href=\\\"javascript:insertTags\"); document.write(\"('\"+tagOpen+\"','\"+tagClose+\"','\"+sampleText+\"');\\\">\");document.write(\"<img width=\\\"23\\\" height=\\\"22\\\" src=\\\"\"+imageFile+\"\\\" border=\\\"0\\\" ALT=\\\"\"+speedTip+\"\\\" TITLE=\\\"\"+speedTip+\"\\\"\"+mouseOver+\">\"); document.write(\"</a>\"); return; }")
        # turn it off for now
        #self.request.write("<script type=\"text/javascript\">\n document.writeln(\"<div id='toolbar'>\");\n addButton('buttons/bold.png','Bold text','\\'\\'\\'','\\'\\'\\'','Bold text'); \n addButton('buttons/italic.png','Italic text','\\'\\'','\\'\\'','Italic text');\n addButton('buttons/extlink.png','External link','[',']','http://www.example.com');\n addButton('buttons/head.png','Headline','\n= ',' =\n','Headline text');\n addButton('buttons/hline.png','Horizontal line (use sparingly)','\n-----\n','','');\n addButton('buttons/center.png','Center','-->','<--','');\n addButton('buttons/image.png','Attached image','\nattachment:','\n','photo.jpg');\n addButton('buttons/plain.png','Ignore wiki formatting','{{{','}}}','Insert non-formatted text here');\n document.writeln(\"</div>\");\n </script>\n'"
        self.request.write(str(html.INPUT(type="hidden", name="action", value="savepage")))
        if backto:
            self.request.write(str(html.INPUT(type="hidden", name="backto", value=backto)))

        # generate default content
        if not raw_body:
            raw_body = _('Describe %s here.') % (self.page_name,)

        # replace CRLF with LF
        raw_body = self._normalize_text(raw_body)

        # make a preview backup?
        if preview is not None:
            # make backup on previews
            self._make_backup(raw_body)

        # send datestamp (version) of the page our edit is based on
        self.request.write('<input type="hidden" name="datestamp" value="%d">' % (mtime,))

        # Print the editor textarea and the save button
        self.request.write('<textarea id="savetext" name="savetext" rows="%d" cols="%d" style="width:100%%">%s</textarea>'
            % (text_rows, text_cols, wikiutil.escape(raw_body)))
        self.request.write('</p>')

        self.request.write("<p>", _("<font size=\"+1\">Please comment about this change:</font>"),
            '<br><input type="text" class="formfields" name="comment" value="%s" size="%d" maxlength="80" style="width:100%%"></p>' % (
                wikiutil.escape(kw.get('comment', ''), 1), text_cols,))

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
        applet = 1
        exclude = '"User Preferences" "Recent Changes" "Davis Map" "Front Page" "To Do"'
        if string.find(exclude, '"' + self.page_name + '"') >= 0:
          applet = 0
        if applet and is_word_in_file(config.web_root + "/map.xml", '"' + self.page_name.replace("&", "&amp;") + '"') or on_same_line(config.web_root + "/points.xml", "category", '"' + self.page_name.replace("&", "&amp;") + '"'):
          applet = 0
        mapButton = ""
        mapHtml = ""
        relative_dir = ''
        if config.relative_dir:
          relative_dir = '/' + config.relative_dir
        if applet:
          mapButton = '<input id="show" class="formbutton" type="button" value="Edit Map" onclick="doshow();"/><input class="formbutton" id="hide" style="display: none;" type="button" value="Hide Map" onclick="dohide();"/>'
          mapHtml = '<br><table style="display: none;" id="map" cellspacing="0" cellpadding="0" width="810" height="460"><tr><td bgcolor="#ccddff" style="border: 1px dashed #aaaaaa;"><applet code="WikiMap.class" archive="%s/map.jar, %s/txp.jar" height=460 width=810 border="1"><param name="map" value="%s/map.xml"><param name="points" value="%s/points.xml"><param name="set" value="true"><param name="highlight" value="%s"><param name="wiki" value="%s">You do not have Java enabled.</applet></td></tr></table>' % (config.web_dir, config.web_dir, config.web_dir, config.web_dir, self.page_name, relative_dir)
        
        self.request.write('''
<p>
<table border="0" cellspacing="0"><tr height="30"><td nowrap><font size="3">
<input type="submit" class="bigbutton" name="button_preview" value="%s">
<input type="submit" class="formbutton" name="button_save" value="%s">
<input type="submit" class="formbutton" name="button_cancel" value="%s">
</td><td width="12">&nbsp;</td><td bgcolor="#ccddff" style="border: 1px dashed #AAAAAA;">
&nbsp;&nbsp;%s
<input type="button" class="formbutton" onClick="window.open('%s/%s?action=AttachFile', 'attachments', 'width=800,height=600,scrollbars=1')" value="Images">
%s
<input type="button" class="formbutton" onClick="location.href='%s/%s?action=DeletePage'" value="Delete">
<input type="button" class="formbutton" onClick="location.href='%s/%s?action=Rename'" value="Rename">&nbsp;&nbsp;</td></tr></table>
</p>%s
<p>
''' % (_('Preview'), save_button_text, cancel_button_text, mapButton, relative_dir, wikiutil.quoteWikiname(self.page_name), button_spellcheck, relative_dir, wikiutil.quoteWikiname(self.page_name), relative_dir, wikiutil.quoteWikiname(self.page_name),mapHtml))

        #if config.mail_smarthost:
        #    self.request.write('''<input type="checkbox" name="notify" value="1"%s><label>%s</label>''' % (
        #        ('', ' checked="checked"')[preview is None or (form.get('notify',['0'])[0] == '1')],
        #        _('Send mail notification'),
        #    ))

        self.request.write('''
        <input type="checkbox" name="rstrip" value="1"%s>
        <label>%s</label>
        </p>
        ''' % (    ('', ' checked="checked"')[preview is not None and (form.get('rstrip',['0'])[0] == '1')],
             _('Remove trailing whitespace from each line')
         ))

        self.request.write('<p>By clicking "Save Changes" you are agreeing to release your contribution under the <a href="http://creativecommons.org/licenses/by/2.0/">Creative Commons-By license</a>, unless noted otherwise. <b>Do not submit copyrighted work (including images) without permission.</b>  For more information, see <a href="%s/Copyrights">Copyrights</a>.' %relative_dir)

        badwords_re = None
        if preview is not None:
            if SpellCheck and (
                    form.has_key('button_spellcheck') or
                    form.has_key('button_newwords')):
                badwords, badwords_re, msg = SpellCheck.checkSpelling(self, self.request, own_form=0)
                self.request.write("<p>%s</p>" % msg)
        self.request.write("</form>")


        # QuickHelp originally by Georg Mischler <schorsch@lightingwiki.com>
        self.request.write('<hr>\n<dl>' + _("""<dt>Emphasis:</dt>
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
            self.request.write('<div id="preview">')
            self.send_page(self.request, content_only=1, hilite_re=badwords_re)
            self.request.write('</div>')

        self.request.write('</div>\n') # end content div

        self.request.theme.emit_custom_html(config.page_footer1)
        self.request.theme.emit_custom_html(config.page_footer2)


    def sendCancel(self, newtext, datestamp):
        """
        User clicked on Cancel button. If edit locking is active,
        delete the current lock file.
        
        @param newtext: the edited text (which has been cancelled)
        @param datestamp: ...
        """
        _ = self._
        self._make_backup(self._normalize_text(newtext))
        self.lock.release()

        backto = self.request.form.get('backto', [None])[0]
        page = backto and Page(backto) or self
        page.send_page(self.request, msg=_('Edit was cancelled.'))


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
            self.saveText("deleted", '0', comment=comment or '')
        except self.SaveError:
            # XXXX Error handling
            pass
        # Then really delete it
        try:
            os.remove(self._text_filename())
        except OSError, er:
            import errno
            if er.errno <> errno.ENOENT: raise er

        
        pdfile= open(config.data_dir +'/pagedict.pickle' , 'r') # pickled pagedict
        pagedict =  cPickle.load(pdfile)
        pdfile.close()

        if pagedict.has_key(self.page_name.lower()):
                pdfile= open(config.data_dir +'/pagedict.pickle' , 'w') # pickled pagedict
                del pagedict[self.page_name.lower()]  #delete entry from dictionary
                cPickle.dump(pagedict, pdfile, 2)
                pdfile.close()

        

        # delete pagelink
        arena = "pagelinks"
        key   = wikiutil.quoteFilename(self.page_name)
        cache = caching.CacheEntry(arena, key)
        cache.remove()

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
        if username and config.allow_extended_names and \
                username.count(' ') and Page(username).exists():
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
        #now = time.strftime("%Y-%m-%dT%H:%M:%SZ", util.datetime.tmtuple())
#now = time.asctime(time.localtime(time.time() + config.tz_offset))
        now = self.request.user.getFormattedDateTime(time.time())
        system_vars = {
            'SIG': lambda s=self, t=now: "[\"%s\"] %s"
                % (s._user_variable(), t,),
            'sig': lambda s=self, t=now: "[\"%s\"] %s"
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
        if kw.get('stripspaces', 0):
            newtext = '\n'.join([line.rstrip() for line in newtext.splitlines()])

        # add final newline if not present in textarea, better for diffs
        # (does not include former last line when just adding text to
        # bottom; idea by CliffordAdams)
        if newtext and newtext[-1] != '\n':
            newtext = newtext + '\n'

        return newtext


    def _make_backup(self, newtext, **kw):
        """
        Make a backup of text before saving and on previews, if user
        has a homepage. Return URL to backup if one is made.
        
        @param newtext: new text of the page
        @keyword ...:...
        @rtype: string
        @return: url of page backup
        """
        _ = self._
        # check for homepage
        pg = wikiutil.getHomePage(self.request)
        if not pg or not self.do_editor_backup:
            return None

        if config.allow_subpages:
            delimiter = "/"
        else:
            delimiter = ""
        backuppage = PageEditor(pg.page_name + delimiter + "MoinEditorBackup", self.request, do_revision_backup=0)
        if config.acl_enabled:
            intro = "#acl %s:read,write,delete\n" % self.request.user.name
        else:
            intro = ""
        pagename = self.page_name
        date = self.request.user.getFormattedDateTime(time.time())
        intro += _('## backup of page "%(pagename)s" submitted %(date)s') % {
            'pagename': pagename, 'date': date,} + '\n'
        backuppage._write_file(intro + newtext)
        return backuppage.url(self.request)

    def _write_file(self, text):
        """
        Write the text to the page file (and make a backup of old page).
        
        @param text: text to save for this page
        @rtype: int
        @return: mtime of new page
        """
        from LocalWiki.util import filesys
        is_deprecated = text[:11].lower() == "#deprecated"

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

    def build_index(self):
        """
        Builds the index with all the pages. . This should hopefully rarely be run.
        """
        forked_id = 0
        pages = list(wikiutil.getPageList(config.text_dir))
        for page in pages:
                p = Page(page)
                #add_to_index(wikiutil.quoteWikiname(p.page_name), p.get_raw_body())
                os.spawnl(os.P_WAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index', '%s' % wikiutil.quoteFilename(p.page_name), '%s' % wikiutil.quoteFilename(p.get_raw_body()))


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
        backup_url = self._make_backup(newtext, **kw)

        #!!! need to check if we still retain the lock here
        #!!! datestamp check is not enough since internal operations use "0"

        # expand variables, unless it's a template or form page
        if not (wikiutil.isTemplatePage(self.page_name) or
                wikiutil.isFormPage(self.page_name)):
            newtext = self._expand_variables(newtext)

        msg = ""
        if not self.request.user.may.save(self, newtext, datestamp, **kw):
            msg = _('You are not allowed to edit this page!')
            raise self.AccessDenied, msg
        elif not self.isWritable():
            msg = _('Page is immutable!')
            raise self.Immutable, msg
        elif not newtext:
            msg = _('You cannot save empty pages.')
            raise self.EmptyPage, msg
        elif datestamp != '0' and datestamp != str(os.path.getmtime(self._text_filename())):
            msg = _("""Sorry, someone else saved the page while you edited it.
<p>Please do the following: Use the back button of your browser, and cut&paste
your changes from there. Then go forward to here, and click EditText again.
Now re-add your changes to the current page contents.</p>
<p><em>Do not just replace
the content editbox with your version of the page, because that would
delete the changes of the other person, which is excessively rude!</em></p>
""")

            if backup_url:
                msg += "<p>%s</p>" % _(
                    'A backup of your changes is <a href="%(backup_url)s">here</a>.') % {'backup_url': backup_url}
            raise self.EditConflict, msg
        elif newtext == self.get_raw_body():
            msg = _('You did not change the page content, not saved!')
            raise self.Unchanged, msg
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

            # determine action for edit log 
            action = kw.get('action', 'SAVE')
            if action=='SAVE' and not self.exists():
                action = 'SAVENEW'
               
           
            if not os.path.exists(config.data_dir + "/text/" + wikiutil.quoteFilename(self.page_name)):  
            # update pagedict ionary
                pdfile= open(config.data_dir +'/pagedict.pickle' , 'r') # pickled pagedict
                pagedict = cPickle.load(pdfile)
                pdfile.close()
                pdfile= open(config.data_dir +'/pagedict.pickle' , 'w') # pickled pagedict
                pagedict[self.page_name.lower()] = self.page_name
                cPickle.dump(pagedict, pdfile, 2) 
                pdfile.close()

        
            # write the page file
            mtime = self._write_file(newtext)
            if self._acl_cache.has_key(self.page_name):
                del self._acl_cache[self.page_name]

            self.lock.release(force=not msg)

            i_am_parent = os.fork()
            if not i_am_parent:
                # we'll try to change the stats early-on
                self.userStatAdd(self.request.user.name, action, self.page_name)

		# write the editlog entry
                log = editlog.EditLog()
                log.add(self.request, self.page_name, None, mtime,
                         kw.get('comment', ''), action=action)

		# write the page-centric editlog entry
                log = editlog.EditLog(config.data_dir + '/pages/' + wikiutil.quoteFilename(self.page_name) + '/editlog')
                log.add(self.request, self.page_name, None, mtime,
			        kw.get('comment', ''), action=action)

                # write last-edited file
                lastedited = wikiutil.getPagePath(self.page_name, 'last-edited')
                try:
                         os.remove(lastedited)
                except OSError:
                        pass
                log = editlog.EditLog(lastedited)
                log.add(self.request, self.page_name, None, mtime,
                    kw.get('comment', ''), action=action)
		
		# I do this log = 0 to call the destuctor of the log object -- we do os._exit(0) so we've gotta do this on our own
		log = 0

                # add event log entry
                #eventlog.EventLog().add(self.request, 'SAVEPAGE',
                #                    {'pagename': self.page_name})

                # we quote the pagetext so we can pass it as a single argument and then have the process run without us paying it any attention
                os.spawnl(os.P_WAIT, config.app_dir + '/add_to_index', config.app_dir + '/add_to_index', wikiutil.quoteFilename(self.page_name), wikiutil.quoteFilename(newtext))

            # we only need to build the index like..once..
                #self.build_index()

                # send notification mails
                #if config.mail_smarthost and kw.get('notify', 0):
                 #msg = msg + self._notifySubscribers(kw.get('comment', ''))
                #        self._notifySubscribers(kw.get('comment', ''))

		# we do this so we don't return another copy of the page to the user!
                os._exit(0)
            else:

        # remove lock (forcibly if we were allowed to break it by the UI)
        # !!! this is a little fishy, since the lock owner might not notice
        # we broke his lock ==> but datestamp checking during preview will
                return msg

    def notifySubscribers(self, **kw):
        msg = ''
        #if config.mail_smarthost and kw.get('notify', 0):
        msg = msg + self._notifySubscribers(kw.get('comment', ''))
        return msg

    def userStatAdd(self, username, action, pagename):
       dom = xml.dom.minidom.parse(config.app_dir + "/userstats.xml")
       users = dom.getElementsByTagName("user")
       root = dom.documentElement
       #is the user in the XML file?
       user_is_in = 0
       for user in users:
          if user.getAttribute("name") == username:
            user_is_in = 1
            edit_count = int(user.getAttribute("edit_count"))
            user.setAttribute("edit_count", str(edit_count + 1))
            if action == 'SAVENEW':
               user.setAttribute("created_count", str(int(user.getAttribute("created_count")) + 1))
            user.setAttribute("last_edit",self.request.user.getFormattedDateTime(time.time()))
            user.setAttribute("last_page_edited",pagename)
            break
            

       if not user_is_in:
           user = dom.createElement("user")
           user.setAttribute("name", username) 
           user.setAttribute("edit_count","1")
           # Did we make this page first for reals?
           if action == 'SAVENEW':
              user.setAttribute("created_count","1")
           else:
              user.setAttribute("created_count","0")
           # Fill in other data (this is an older user)
           user.setAttribute("last_edit",self.request.user.getFormattedDateTime(time.time()))
           user.setAttribute("last_page_edited",pagename)
           user.setAttribute("file_count","0")
           user.setAttribute("join_date",self.request.user.getFormattedDateTime(time.time()))
           root.appendChild(user)

       the_xml = dom.toprettyxml('')
       temp_stamp = str(time.time())
       xmlfile = open(config.app_dir + "/userstats.xml." + temp_stamp,"w")
       xmlfile.write(the_xml)
       xmlfile.close()
       os.rename(config.app_dir + "/userstats.xml." + temp_stamp, config.app_dir + "/userstats.xml")
        


class PageLock:
    """
    PageLock - Lock pages
    
    TODO: race conditions throughout, need to lock file during queries & update
    """
    def __init__(self, pagename, request):
        """
        """
        self.page_name = pagename
        self.request = request
        self._ = request.getText

        # current time and user for later checks
        self.now = time.time()
        self.uid = request.user.valid and request.user.id or request.remote_addr

        # get details of the locking preference, i.e. warning or lock, and timeout
        self.locktype = None
        self.timeout = 10 * 60 # default timeout in minutes

        if config.edit_locking:
            lockinfo = config.edit_locking.split()
            if 1 <= len(lockinfo) <= 2:
                self.locktype = lockinfo[0].lower()
                if len(lockinfo) > 1:
                    try:
                        self.timeout = int(lockinfo[1]) * 60
                    except ValueError:
                        pass


    def aquire(self):
        """
        Begin an edit lock depending on the mode chosen in the config.

        @rtype: tuple
        @return: tuple is returned containing 2 values:
              * a bool indicating successful aquiry
              * a string giving a reason for failure or an informational msg
        """
        if not self.locktype:
            # we are not using edit locking, so always succeed
            return 1, ''

        _ = self._
        #!!! race conditions, need to lock file during queries & update
        self._readLockFile()
        bumptime = self.request.user.getFormattedDateTime(self.now + self.timeout)
        timestamp = self.request.user.getFormattedDateTime(self.timestamp)
        owner = self.owner_html
        secs_valid = self.timestamp + self.timeout - self.now

        # do we own the lock, or is it stale?
        if self.owner is None or self.uid == self.owner or secs_valid < 0:
            # create or bump the lock
            self._writeLockFile()

            msg = []
            if self.owner is not None and -10800 < secs_valid < 0:
                mins_ago = secs_valid / -60
                msg.append(_(
                    "The lock of %(owner)s timed out %(mins_ago)d minute(s) ago,"
                    " and you were granted the lock for this page."
                    ) % {'owner': owner, 'mins_ago': mins_ago})

            if self.locktype == 'lock':
                msg.append(_(
                    "Other users will be <em>blocked</em> from editing this page until %(bumptime)s."
                    ) % {'bumptime': bumptime})
            else:
                msg.append(_(
                    "Other users will be <em>warned</em> until %(bumptime)s that you are editing this page."
                    ) % {'bumptime': bumptime})
            msg.append(_(
                "Use the Preview button to extend the locking period."
                ))
            result = 1, '\n'.join(msg)
        else:
            mins_valid = (secs_valid+59) / 60
            if self.locktype == 'lock':
                # lout out user
                result = 0, _(
                    "This page is currently <em>locked</em> for editing by %(owner)s until %(timestamp)s,"
                    " i.e. for %(mins_valid)d minute(s)."
                    ) % {'owner': owner, 'timestamp': timestamp, 'mins_valid': mins_valid}
            else:
                # warn user about existing lock
                result = 1, _(
                    'This page was opened for editing or last previewed at %(timestamp)s by %(owner)s.<br>\n'
                    '<strong class="box-warning">'
                    'You should <em>refrain from editing</em> this page for at least another %(mins_valid)d minute(s),\n'
                    'to avoid editing conflicts.'
                    '</strong><br>\n'
                    'To leave the editor, press the Cancel button.'
                    ) % {'timestamp': timestamp, 'owner': owner, 'mins_valid': mins_valid}
        return result


    def release(self, force=0):
        """ 
        Release lock, if we own it.
        
        @param force: if 1, unconditionally release the lock.
        """
        if self.locktype:
            # check that we own the lock in order to delete it
            #!!! race conditions, need to lock file during queries & update
            self._readLockFile()
            if force or self.uid == self.owner:
                self._deleteLockFile()


    def _filename(self):
        """get path and filename for edit-lock file"""
        return wikiutil.getPagePath(self.page_name, 'edit-lock')


    def _readLockFile(self):
        """Load lock info if not yet loaded."""
        _ = self._
        self.owner = None
        self.owner_html = wikiutil.escape(_("<unknown>"))
        self.timestamp = 0

        if self.locktype:
            try:
                entry = editlog.EditLog(filename=self._filename()).next()
            except StopIteration:
                entry = None
                                                    
            if entry:
                self.owner = entry.userid or entry.addr
                self.owner_html = entry.getEditor(self.request)
                self.timestamp = long(entry.ed_time)


    def _writeLockFile(self):
        """Write new lock file."""
        self._deleteLockFile()
        try:
            editlog.EditLog(filename=self._filename()).add(
               self.request, self.page_name, None, self.now, '', action="LOCK")
        except IOError:
            pass

    def _deleteLockFile(self):
        """Delete the lock file unconditionally."""
        try:
            os.remove(self._filename())
        except OSError:
            pass

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

