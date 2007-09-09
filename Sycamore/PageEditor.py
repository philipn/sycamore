# -*- coding: utf-8 -*-
"""
    Sycamore - PageEditor class

    @copyright: 2005-2007 Philip Neustrom, <philipn@gmail.com>,
    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os
import time
import urllib
import string
import xml.dom.minidom

import Sycamore.util.web
import Sycamore.util.mail
import Sycamore.util.datetime

from Sycamore import caching
from Sycamore import config
from Sycamore import user
from Sycamore import util
from Sycamore import wikiutil
from Sycamore import wikidb
from Sycamore import search
from Sycamore.Page import Page
from Sycamore.widget import html

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
    class TooBig(SaveError):
        pass

    def __init__(self, page_name, request, **keywords):
        """
        Create page editor object.
        
        @param page_name: name of the page
        @param request: the request object
        @keyword do_revision_backup: if 0, suppress making a page backup
                                     per revision
        """
        self.request = request
        self._ = request.getText
        Page.__init__(self, page_name, request, **keywords)

        self.do_revision_backup = keywords.get('do_revision_backup', 1)

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
            from Sycamore.action import SpellCheck
        except ImportError:
            SpellCheck = None

        form = self.request.form
        _ = self._
        self.request.http_headers([("Content-Type",
            "text/html; charset=%s" % config.charset)] + self.request.nocache)
        msg = None
        preview = kw.get('preview', None)
        emit_anchor = not kw.get('staytop', 0)
        proper_name = self.proper_name()

        from Sycamore.formatter.text_html import Formatter
        self.request.formatter = Formatter(self.request, store_pagelinks=1,
                                           preview=preview)

        base_uri = "%s/%s?action=edit" % (self.request.getScriptname(),
                                          wikiutil.quoteWikiname(
                                            self.proper_name()))
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

        wikiutil.send_title(self.request,
            self.proper_name(),
            pagename=self.proper_name(),
            has_link=True,
            strict_title='Editing "%s"' % self.proper_name(),
            body_onload = "sizeForIE('savetext', 100, 'editorComment', 99);"
        )

        # start content div
        self.request.write('<div id="content" class="content">\n')
        
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
            if self.request.user.valid:
                text_rows = int(self.request.user.edit_rows)

        if form.has_key('cols'):
            text_cols = int(form['cols'][0])
            if self.request.user.valid:
                # possibly update user's pref
                if text_rows != self.request.user.edit_rows:
                    self.request.user.edit_rows = text_rows
                    self.request.user.save()
        else:
            text_cols = 80
            if self.request.user.valid:
                text_cols = int(self.request.user.edit_cols)

        # check datestamp (version) of the page our edit is based on
        if preview is not None:
            # propagate original datestamp
            mtime = float(form['datestamp'][0])

            # did someone else change the page while we were editing?
            conflict_msg = None
            if not self.exists():
                # page does not exist, are we creating it?
                if mtime:
                    conflict_msg = _('<p>Someone else <b>deleted</b> this '
                                     'page while you were editing!')
            elif mtime != self.mtime():
                conflict_msg = _('<p>Someone else changed this page while '
                                 'you were editing.')
                # merge conflicting versions
                allow_conflicts = 1
                from Sycamore.util import diff3
                savetext = self.get_raw_body()
                oldpg = Page(self.page_name, self.request, prev_date=mtime)
                original_text = oldpg.get_raw_body()
                saved_text = Page(self.page_name, self.request).get_raw_body()
                verynewtext, had_conflict = diff3.text_merge(
                    original_text, saved_text, savetext,
                    marker1='----- /!\ Edit conflict! Your version: -----\n',
                    marker2='----- /!\ Edit conflict! Other version: -----\n',
                    marker3='----- /!\ End of edit conflict -----\n')
                if had_conflict and self.request.user.valid and (
                   self.request.user.id == self.last_edit_info()[1]):
                    # user pressed back button or did something weird
                    conflict_msg =None
                elif had_conflict:
                    conflict_msg = _(conflict_msg + 
                                     'There was an <b>edit conflict between '
                                     'your changes!</b></p>'
                                     '<p>Please review the conflicts and '
                                     'merge the changes.</p>')
                    mtime = self.mtime()
                    self.set_raw_body(verynewtext, 1)
                else:
                   conflict_msg = _(conflict_msg + 
                                    'Your changes were sucessfully merged!')
                   mtime = self.mtime()
                   self.set_raw_body(verynewtext)

            if conflict_msg:
                self.request.write('<div id="message"><div>%s'
                                   '</div></div>'% conflict_msg)
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
        else:
            raw_body = self.get_raw_body()

        # send text above text area
        
        # button toolbar
        self.request.write('<div id="editArea">')
        self.request.write("<script type=\"text/javascript\">"
                           "var buttonRoot = '%s';</script>" % (
                            os.path.join(config.url_prefix,
                                         self.request.theme.name,
                                         'img', 'buttons')))
        if self.request.user.name:
          if config.user_page_prefix:
            self.request.write("<script type=\"text/javascript\">"
                               "var userPageLink = '[\"%s%s\"]';</script>" % (
                                config.user_page_prefix,
                                self.request.user.propercased_name))
          else: 
            self.request.write("<script type=\"text/javascript\">"
                               "var userPageLink = '[\"%s\"]';</script>" % (
                                config.user_page_prefix,
                                self.request.user.propercased_name))
        else:
          self.request.write("<script type=\"text/javascript\">"
                             "var userPageLink = '%s';</script>" % (
                             self.request.remote_addr))
          
        if config.wiki_farm:
            self.request.write("<script type=\"text/javascript\" "
                               "src=\"http://%s%s%s/edit.js\"></script>\n" % (
                                config.wiki_base_domain, config.web_dir,
                                config.url_prefix))
        else:
            self.request.write("<script type=\"text/javascript\" "
                               "src=\"%s%s/wiki/edit.js\"></script>\n" % (
                                config.web_dir, config.url_prefix))

        # send form
        self.request.write('<form name="editform" id="editform" '
                           'method="post" action="%s/%s#preview">' % (
                            self.request.getScriptname(),
                            wikiutil.quoteWikiname(proper_name)))

        self.request.write(str(html.INPUT(type="hidden", name="action",
                                          value="savepage")))
        if backto:
            self.request.write(str(html.INPUT(type="hidden",
                                              name="backto", value=backto)))

        # generate default content
        if not raw_body:
            if self.isTalkPage():
                raw_body = _('This page is for discussing the '
                             'contents of ["%s"].') % self.proper_name()[:-5]
            else:
                raw_body = _('Describe %s here.') % (self.proper_name(),)

        # replace CRLF with LF
        raw_body = self._normalize_text(raw_body)

        # send datestamp (version) of the page our edit is based on
        self.request.write('<input type="hidden" name="datestamp" '
                           'value="%s">' % repr(mtime))

        # Print the editor textarea and the save button
        self.request.write('<textarea id="savetext" name="savetext" '
                           'rows="%d" cols="%d" style="width:100%%;">%s'
                           '</textarea>' % (text_rows, text_cols,
                                            wikiutil.escape(raw_body)))

       # make sure we keep the template notice on a resize of the editor
        template_param = ''
        if form.has_key('template'):
            template_param = '&amp;template=' + form['template'][0]
       # draw edit size links
        self.request.write(_('<div class="pageEditInfo" id="editorSize">'
                             'editor size:'))
        self.request.write('<a href="%s&amp;rows=%d&amp;cols=60%s">%s'
                           '</a>' % (base_uri, text_rows + 10,
                                     template_param, '+'))
        self.request.write(',<a href="%s&amp;rows=%s&amp;cols=60%s">%s'
                           '</a>' % (base_uri, text_rows - 10,
                                     template_param, '-'))
        self.request.write('</div>')
        self.request.write('</p>') # close textarea

        self.request.write('<div id="editComment" id="editorResizeButtons"> '
                           '%s<br><input type="text" class="formfields" '
                           'name="comment" id="editorComment" value="%s" '
                           'size="%d" maxlength="80" style="width:99%%;">'
                           '</div>' % (_("<font size=\"+1\">Please comment "
                                         "about this change:</font>"),
                                       wikiutil.escape(kw.get('comment', ''),
                                       1), text_cols))

        # button bar
        button_spellcheck = (SpellCheck and
            '<input type="submit" class="formbutton" name="button_spellcheck"'
            ' value="%s">' % _('Check Spelling')) or ''

        save_button_text = _('Save Changes')
        cancel_button_text = _('Cancel')
        
        self.request.write("</div>")

        if self.request.user.may.admin(self):
            security_button = ('<input type="button" class="formbutton" '
                              'onClick="location.href='
                              '\'%s/%s?action=Security\'" '
                              'value="Security">') % (
                                self.request.getScriptname(),
                                wikiutil.quoteWikiname(proper_name))
        else:
            security_button = ''
       
        if self.request.user.may.delete(self):
            delete_button = ('<input type="button" class="formbutton" '
                            'onClick="location.href='
                            '\'%s/%s?action=DeletePage\'" value="Delete">') % (
                                self.request.getScriptname(),
                                wikiutil.quoteWikiname(proper_name))
            rename_button = ('<input type="button" class="formbutton" '
                            'onClick="location.href=\'%s/%s?action=Rename\'"'
                            ' value="Rename">') % (
                                self.request.getScriptname(),
                                wikiutil.quoteWikiname(proper_name))
        else:
            delete_button = ''
            rename_button = ''
        
        self.request.write('<div id="editButtonRow">'
                           '<span>'
                           '<input type="submit" class="formbutton" '
                           'name="button_preview" value="%s"> '
                           '<input type="submit" class="formbutton" '
                           'name="button_save" value="%s"> '
                           '<input type="submit" class="formbutton" '
                           'name="button_cancel" value="%s"> '
                           '</span>'
                           '<span class="editActions">'
                           '<input type="button" class="formbutton" '
                           'onClick="window.open(\'%s/%s?action=Files\', '
                           '\'files\', \'width=800,height=600,'
                           'scrollbars=1\')" value="Upload Files"> '
                           '%s '
                           '%s '
                           '%s '
                           '%s</span>'
                           '</div>' % (
                                _('Preview'), save_button_text,
                                cancel_button_text,
                                self.request.getScriptname(),
                                wikiutil.quoteWikiname(proper_name),
                                button_spellcheck, delete_button,
                                rename_button, security_button))

        if self.request.config.edit_agreement_text:
            self.request.write(self.request.config.edit_agreement_text)

        badwords_re = None
        if preview is not None:
            if SpellCheck and (
                    form.has_key('button_spellcheck') or
                    form.has_key('button_newwords')):
                badwords, badwords_re, msg = SpellCheck.checkSpelling(self,
                    self.request, own_form=0)
                self.request.write("<p>%s</p>" % msg)
        self.request.write("</form>")

        if config.wiki_farm:
            from Sycamore import farm
            help_link = farm.link_to_page(farm.getBaseWikiName(),
                                          "Help with Editing",
                                          self.request.formatter,
                                          force_farm=True)
        else:
            help_link = Page("Help with Editing", self.request).link_to()

        # QuickHelp originally by Georg Mischler <schorsch@lightingwiki.com>
        self.request.write('<h2>Editing quick-help</h2>\n'
            '<dl><div style="float: right; margin: 10px; border: 1px solid; '
            'padding: 3pt;">See <b>%s</b> for more information.</div>' % (
                help_link) + _("<dt>Emphasis:</dt>\n"
                    "<dd>''<em>italics</em>''; '''<strong>bold</strong>''';"
                    "'''''<strong><em>bold italics</em></strong>''''';"
                    "''<em>mixed '''<strong>bold</strong>''' and "
                    "italics</em>''; ---- horizontal rule.</dd>"
                    "<dt>Headings:</dt>"
                    "<dd>= Title 1 =; == Title 2 ==; === Title 3 ===;"
                    "==== Title 4 ====; ===== Title 5 =====.</dd>"
                    "<dt>Lists:</dt>"
                    "<dd>space and one of * bullets; 1., a., A., i., I. "
                    "numbered items;"
                    "  1.#n start numbering at n; space alone indents.</dd>"
                    "<dt>Links:</dt>"
                    "<dd>[\"brackets and double quotes\"]; [\"the exact "
                    "page name\" label];"
                    "  url; [url]; [url label].</dd>"
                    "<dt>Tables:</dt>"
                    "<dd>|| cell text |||| cell text spanning two columns ||;"
                    "  no trailing white space allowed after tables or titles."
                    "</dd></dl>"))

        if preview is not None:
            if not emit_anchor:
                preview_name = "previewHide"
            else:
                preview_name = "preview"
            self.request.write('<div id="%s" class="preview">' % preview_name)
            self.send_page(content_only=1, hilite_re=badwords_re,
                           preview=preview)
            self.request.write('</div>')

        self.request.write('</div>\n') # end content div

        wikiutil.send_after_content(self.request)

        self.request.theme.emit_custom_html(config.page_footer1)
        self.request.theme.emit_custom_html(config.page_footer2)

        self.request.write('</body></html>') 

    def sendCancel(self, newtext, datestamp):
        """
        User clicked on Cancel button.
        
        @param newtext: the edited text (which has been cancelled)
        @param datestamp: ...
        """
        _ = self._

        backto = self.request.form.get('backto', [None])[0]
        page = backto and Page(backto, self.request) or self
        page.send_page(msg=_('Edit was cancelled.'))

    def deletePage(self, comment=None, permanent=False, showrc=True):
        """
        Delete the page (but keep the backups)
        
        @param comment: Comment given by user
        @param permanent: Do we permanently delete all past versions of
                          the page?
        @param showrc: Do we log this revert to recent changes?
                       This option assumes permanent is True.
        """
        from Sycamore import caching
        if permanent:
            # nuke all cached page information
            caching.deleteAllPageInfo(self.page_name, self.request)
            # nuke all old versions!  wwheewwwahawwww
            self.request.cursor.execute("""DELETE from allPages
                where name=%(page_name)s and wiki_id=%(wiki_id)s""",
                {'page_name':self.page_name,
                 'wiki_id':self.request.config.wiki_id},
                isWrite=True)
            # nuke all map points!  wwheewwwahawwww
            self.request.cursor.execute("""DELETE from oldMapPoints
                where pagename=%(page_name)s and wiki_id=%(wiki_id)s""",
                {'page_name':self.page_name,
                 'wiki_id':self.request.config.wiki_id},
                isWrite=True)
            self.request.cursor.execute("""DELETE from mapPoints
                where pagename=%(page_name)s and wiki_id=%(wiki_id)s""",
                {'page_name':self.page_name,
                 'wiki_id':self.request.config.wiki_id},
                isWrite=True)
            
        # First save a final backup copy of the current page
        # (recreating the page allows access to the backups again)
        if not (permanent and not showrc):
            try:
                self.saveText("deleted", '0', comment=comment or '',
                              action='DELETE')
            except self.SaveError, msg:
                return msg

        # Then really delete it
        self.request.cursor.execute("""DELETE from curPages
            where name=%(page_name)s and wiki_id=%(wiki_id)s""",
            {'page_name':self.page_name,
             'wiki_id':self.request.config.wiki_id},
            isWrite=True)

        from Sycamore import caching, search

        if config.memcache:
            pagecount = wikidb.getPageCount(self.request) - 1
            self.request.mc.set('active_page_count', pagecount)
            if permanent and not showrc:
                  caching.updateRecentChanges(self)

        self.request.req_cache['pagenames'][(
            self.page_name, self.wiki_name)] = False

        cache = caching.CacheEntry(self.page_name, self.request)
        cache.clear(type='page save delete')

        # remove entry from the search databases
        search.remove_from_index(self)

        return ''

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
            newtext = '\n'.join(
                [line.rstrip() for line in newtext.splitlines()])

        # add final newline if not present in textarea, better for diffs
        # (does not include former last line when just adding text to
        # bottom; idea by CliffordAdams)
        if newtext and newtext[-1] != '\n':
            newtext = newtext + '\n'

        return newtext

    def _write_to_db(self, text, action, comment, ip, proper_name):
        """
        Write the text to the page tables in the database.
        """
        ourtime = time.time()
        self.request.save_time = ourtime
        self.request.cursor.execute("""SELECT name, propercased_name
            from curPages where name=%(page_name)s and wiki_id=%(wiki_id)s""",
            {'page_name':self.page_name,
             'wiki_id':self.request.config.wiki_id})
        exists = self.request.cursor.fetchone()
        if not proper_name:
            if exists:
                proper_name = exists[1]
            else:
                proper_name = self.given_name
 
        if not self.request.user.id:
            user_id = 'anon:%s' % i
        else:
            user_id = self.request.user.id

        if exists:
            self.request.cursor.execute("""UPDATE curPages set
                name=%(page_name)s, text=%(text)s, editTime=%(ourtime)s,
                userEdited=%(id)s, propercased_name=%(proper_name)s
                where name=%(page_name)s and wiki_id=%(wiki_id)s""",
                {'page_name': self.page_name, 'text': text,
                 'ourtime': ourtime, 'id': user_id, 'proper_name':proper_name,
                 'wiki_id':self.request.config.wiki_id},
                isWrite=True)
        else:
            self.request.cursor.execute("""INSERT into curPages 
                (name, text, cachedText, editTime, cachedTime, userEdited, 
                 propercased_name, wiki_id) values
                (%(page_name)s, %(text)s, NULL, %(ourtime)s, NULL, %(id)s,
                 %(proper_name)s, %(wiki_id)s)""",
                {'page_name':self.page_name, 'text':text, 'ourtime':ourtime,
                 'id':user_id, 'proper_name':proper_name,
                 'wiki_id':self.request.config.wiki_id},
                isWrite=True)

        # then we need to update the allPages table for Recent Changes
        # and page-centric info.

        self.request.cursor.execute("""INSERT into allPages
            (name, text, editTime, userEdited, editType, comment, userIP,
             propercased_name, wiki_id) values
            (%(page_name)s, %(text)s, %(ourtime)s, %(id)s, %(action)s,
             %(comment)s, %(ip)s, %(proper_name)s, %(wiki_id)s)""",
            {'page_name':self.page_name, 'proper_name':proper_name,
             'text':text, 'ourtime':ourtime, 'id':user_id, 'action':action,
             'comment':wikiutil.escape(comment),'ip':ip,
             'wiki_id':self.request.config.wiki_id},
            isWrite=True)

        # set in-memory page text/cached page text
        self.set_raw_body(text, set_cache=True)

        import caching
        cache = caching.CacheEntry(self.page_name, self.request)

        if config.memcache and not exists:
          pagecount = wikidb.getPageCount(self.request) + 1
          self.request.mc.set('active_page_count', pagecount)
        
        # set trigger for clearing possible dependencies (e.g. [[Include]])
        # we want this to be a post-commit trigger so that we don't
        # have stale data
        for pagename in caching.depend_on_me(self.page_name, self.request,
                                             exists, action=action):
          self.request.postCommitActions.append(
            (caching.CacheEntry(pagename, self.request).clear,))
        
        if exists:
            type = 'page save'
        else:
            type = 'page save new'
        self.buildCache(type=type)

        # check if this is a user page and keep track of it, if so
        changed_state = (action == 'SAVENEW' or action == 'DELETE')
        is_user_page = self.page_name.startswith(
            config.user_page_prefix.lower())
        if is_user_page and changed_state:
            user.userPageChangedState(self, action)

    def saveText(self, newtext, datestamp, **kw):
        """
        Save new text for a page.

        @param newtext: text to save for this page
        @param datestamp: ...
        @keyword stripspaces: strip whitespace from line ends (default: 0)
        @keyword notify: send email notice tp subscribers (default: 0)
        @keyword comment: comment field (when preview is true)
        @keyword action: action for log (default: SAVE)
        @keyword proper_name: properly-cased pagename (for renames)
        @keyword ignore_edit_conflicts: force a save regardless of status
                                        (boolean)
        @keyword force_save: ignore "page content the same" error
        @rtype: string
        @return: error msg
        """
        self.page_name = self.page_name.strip() # to ensure consistency
        _ = self._
        newtext = self._normalize_text(newtext, **kw)

        # for inline editing we want things to be as smooth as we can
        no_save_msg = False
        if (self.request.form.has_key('no_save_msg') and
            self.request.form['no_save_msg'][0]):
            no_save_msg = True

        msg = ""
        merged_changes = False
        ignore_edit_conflicts = kw.get('ignore_edit_conflicts', False)
        if not self.request.user.may.save(self, newtext, datestamp, **kw):
            msg = _('You are not allowed to edit this page!')
            raise self.AccessDenied, msg
        elif not newtext.strip():
            msg = _('You cannot save empty pages.')
            raise self.EmptyPage, msg
        elif (not ignore_edit_conflicts and datestamp != '0' and
              (datestamp < self.mtime()) and self.exists()):
            from Sycamore.util import diff3
            savetext = newtext
            original_text = Page(self.page_name, self.request,
                                 prev_date=datestamp).get_raw_body()
            saved_text = self.get_raw_body()
            verynewtext, had_conflict = diff3.text_merge(
                original_text, saved_text, savetext,
                marker1='----- /!\ Edit conflict! Your version: -----\n',
                marker2='----- /!\ Edit conflict! Other version: -----\n',
                marker3='----- /!\ End of edit conflict -----\n')
            msg = _("Someone else changed this page while you were editing.")

            if (had_conflict and self.request.user.valid and
                (self.request.user.id == self.last_edit_info()[1])):
               # user pressed back button or did something weird
               had_conflict = False
               msg = None
            else:
                # we did some sort of merging or we had a conflict,
                # so let them know
                if had_conflict:
                    raise self.EditConflict, (msg, verynewtext)
                merged_changes = True
                msg = _("""%s Your changes were successfully merged! """ % msg)
                newtext = verynewtext
        elif (newtext == self.get_raw_body() and not
              self._rename_lowercase_condition() and
              kw.get('action') != 'SAVE/REVERT' and not
              kw.get('force_save')):
            # check to see if they're saving the page with the same content
            # it had before
            msg = _('You did not change the page content, not saved!')
            raise self.Unchanged, msg
        elif (config.max_page_size and 
            len(newtext.encode(config.charset)) > (config.max_page_size*1024)):
            msg = _('This page is too big!  Pages can be, at most, %sK.  '
                    'Consider splitting the page up into multiple pages '
                    'instead!' % config.max_page_size)
            raise self.TooBig, msg

        # save only if no error occured (msg is empty)
        if not msg or merged_changes:
            # set success msg
            if not merged_changes and not no_save_msg:
              msg = _("Thank you for your changes. "
                      "Your attention to detail is appreciated. ")

            # determine action for edit logging
            action = kw.get('action', 'SAVE')
            if action=='SAVE' and not self.exists():
                action = 'SAVENEW'
                           
            # write the page file
            mtime = self._write_to_db(newtext, action, kw.get('comment',''),
                                      self.request.remote_addr,
                                      kw.get('proper_name',None))
            # deal with the case of macros / other items that change state by
            # /not/ being in the page
            wikiutil.macro_delete_checks(self)
            
            # we'll try to change the stats early-on
            if self.request.user.name:
                self.userStatAdd(self.request.user, action, self.page_name)

            # add the page to the search index or update its index
            if action != 'DELETE':
                search.add_to_index(self)

            # note the change in recent changes.  this explicit call is needed
            # because of the way we cache our change information
            caching.updateRecentChanges(self)

            return msg

    def _rename_lowercase_condition(self):
        given_name = self.given_name
        current_name = self.proper_name()
        # implies existance
        if current_name:
          if ((current_name != given_name) and
              (current_name.lower() == given_name.lower())):
            return True

        return False
          
    def userStatAdd(self, theuser, action, pagename):
        self.request.cursor.execute("""SELECT created_count, edit_count
            from users where name=%(username)s""", {'username':theuser.name})
        result = self.request.cursor.fetchone()
       
        total_created_count = result[0]
        total_edit_count = result[1]

        wiki_info = theuser.getWikiInfo() 

        local_created_count = wiki_info.created_count
        local_edit_count = wiki_info.edit_count

        total_edit_count += 1
        local_edit_count += 1
        if action == 'SAVENEW': 
            total_created_count += 1
            local_created_count += 1
        last_page_edited = pagename
        last_edit_date = time.time()

        last_wiki_edited = self.request.config.wiki_id
        d = {'total_created_count':total_created_count,
             'total_edit_count':total_edit_count,
             'last_wiki_edited':last_wiki_edited,
             'last_page_edited':last_page_edited,
             'last_edit_date':last_edit_date,
             'username':theuser.name,
             'wiki_id':self.request.config.wiki_id,
             'local_created_count':local_created_count,
             'local_edit_count':local_edit_count,
             'file_count': wiki_info.file_count}
        self.request.cursor.execute("""UPDATE users set
            created_count=%(total_created_count)s,
            edit_count=%(total_edit_count)s,
            file_count=%(file_count)s,
            last_page_edited=%(last_page_edited)s,
            last_edit_date=%(last_edit_date)s,
            last_wiki_edited=%(wiki_id)s
            where name=%(username)s""", d, isWrite=True)

        wiki_info.created_count = local_created_count
        wiki_info.edit_count = local_edit_count
        wiki_info.last_page_edited = last_page_edited
        wiki_info.last_edit_date = last_edit_date

        theuser.setWikiInfo(wiki_info)
