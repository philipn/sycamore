# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Macro Implementation

    These macros are used by the parser/wiki.py module
    to implement complex and/or dynamic page content.

    The sub-package "Sycamore.macro" contains external
    macros, you can place your extensions there.

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import time
from Sycamore import action, config, macro, util
from Sycamore import wikiutil, wikiaction, i18n
from Sycamore.Page import Page
from Sycamore.util import pysupport

#############################################################################
### Globals
#############################################################################

names = ["titlesearch", "wordindex", "titleindex",
         "goto", "interwiki", "systeminfo", "pagecount", "userpreferences",
         # Macros with arguments
         "icon", "pagelist", "date", "datetime", "anchor", "mailto", "getval",
]

# external macros
names.extend(wikiutil.getPlugins('macro'))

# languages
names.extend(i18n.languages.keys())

#############################################################################
### Helpers
#############################################################################

def _make_index_key(index_letters, additional_html=""):
    #index_letters.sort()
    links = map(lambda ch:
                    '<a href="#%s">%s</a>' %
                    (wikiutil.quoteWikiname(ch), ch.replace('~', 'Others')),
                index_letters)
    return "<p>%s%s</p>" % (' | '.join(links), additional_html)


#############################################################################
### Macros - Handlers for [[macroname]] markup
#############################################################################

class Macro:
    """ Macro handler 
    
    There are three kinds of macros: 
     * Builtin Macros - implemented in this file and named _macro_[name]
     * Language Pseudo Macros - any lang the wiki knows can be used as
       macro and is implemented here by _m_lang() 
     * External macros - implemented in either Sycamore.macro package, or
       in the specific wiki instance in the plugin/macro directory
    """

    Dependencies = {
        "TitleSearch" : ["namespace"],
        "Goto"        : [],
        "WordIndex"   : ["namespace"],
        "TitleIndex"  : ["namespace"],
        "InterWiki"   : ["pages"],  # if interwikimap is editable
        "SystemInfo"  : ["pages"],
        "PageCount"   : ["namespace"],
        "Icon"        : ["user"], # users have different themes and user prefs
        "PageList"    : ["namespace"],
        "Date"        : ["time"],
        "DateTime"    : ["time"],
        "UserPreferences" :["time"],
        "Anchor"      : [],
        "Mailto"      : ["user"],
        "GetVal"      : ["pages"],
        }

    # we need the lang macros to execute when html is generated,
    # to have correct dir and lang html attributes
    for lang in i18n.languages.keys():
        Dependencies[lang] = []
    

    def __init__(self, parser):
        self.parser = parser
        self.form = self.parser.form
        self.request = self.parser.request
        self.formatter = self.request.formatter
        self._ = self.request.getText

    def execute(self, macro_name, args, formatter=None):
        macro = wikiutil.importPlugin('macro', macro_name)
        if macro:
            return macro(self, args, formatter)

        builtins = vars(self.__class__)
        # builtin macro
        if builtins.has_key('_macro_' + macro_name):
            return builtins['_macro_' + macro_name](self, args, formatter)

        # language pseudo macro
        if i18n.languages.has_key(macro_name):
            return self._m_lang(macro_name, args)

        raise ImportError("Cannot load macro %s" % macro_name)

    def _m_lang(self, lang_name, text):
        """ Set the current language for page content.
        
            Language macro are used in two ways:
             * [lang] - set the current language until next lang macro
             * [lang(text)] - insert text with specific lang inside page
        """
        if text:
            return self.formatter.lang(lang_name, text)
        
        self.request.current_lang = lang_name
        return ''
  
    def get_dependencies(self, macro_name):
        if self.Dependencies.has_key(macro_name):
            return self.Dependencies[macro_name]
        result = wikiutil.importPlugin('macro', macro_name, 'Dependencies')
        if result != None:
            return result
        else:
            return ["time"]

    def _macro_titlesearch(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        return self._m_search("titlesearch")

    def _m_search(self, type):
        _ = self._
        if self.form.has_key('value'):
            default = wikiutil.unquoteWikiname(self.form["value"][0])
        else:
            default = ''
        boxes = ''
        if type == "fullsearch":
            boxes = (
                  '<br><input type="checkbox" name="context" value="40" checked="checked">'
                + _('Display context of search results')
                + '<br><input type="checkbox" name="case" value="1">'
                + _('Case-sensitive searching')
            )
        return self.formatter.rawHTML((
            '<form method="GET">'
            '<input type="hidden" name="action" value="%s">'
            '<input name="value" size="30" value="%s">&nbsp;'
            '<input type="submit" value="%s">'
            '%s</form>') % (type, wikiutil.escape(default, quote=1), _("Go"), boxes))

    
    def _macro_titleindex(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        _ = self._
        html = []
        index_letters = []
        allpages = int(self.form.get('allpages', [0])[0]) != 0
        pages = wikiutil.getPageList(self.request, alphabetize=False)
  	pages_deco = [ (pagename.lower(), pagename) for pagename in pages ]
	pages_deco.sort()
        pages = [ word for lower_word, word in pages_deco ]
        #list(wikiutil.getPageList(config.text_dir))
        # pages = filter(self.request.user.may.read, pages)
        #if not allpages:
        #    pages = [p for p in pages if not wikiutil.isSystemPage(self.request, p)]
        current_letter = None
        #for name in pages:
        #    html.append(' %s ' % name)
        relative_dir = ''
        if config.relative_dir:
            relative_dir = '/' + config.relative_dir
        for name in pages:
            if 1: #self.request.user.may.read(name):
                letter = name[0].upper()
                # XXX UNICODE - fix here, too?
                if wikiutil.isUnicodeName(letter):
                    try:
                        letter = wikiutil.getUnicodeIndexGroup(unicode(name, config.charset))
                        if letter: letter = letter.encode(config.charset)
                    except UnicodeError:
                        letter = None
                    if not letter: letter = "~"
                if letter not in index_letters:
                    index_letters.append(letter)
                if letter <> current_letter:
                    html.append('<a name="%s"><h3>%s</h3></a>' % (
                        wikiutil.quoteWikiname(letter), letter.replace('~', 'Others')))
                    current_letter = letter
                else:
                    html.append('<br>')
                html.append('<a href="%s/%s">%s</a>\n' % (relative_dir, wikiutil.quoteWikiname(name), name))
#Page(name).link_to(self.request, attachment_indicator=1))

	index = ''
        ## add rss link
        #if 0: # if wikixml.ok: # XXX currently switched off (not implemented)
        #    from Sycamore import wikixml
        #    img = self.request.theme.make_icon("rss")
        #    index = index + self.formatter.url(
        #        wikiutil.quoteWikiname(self.formatter.page.page_name) + "?action=rss_ti",
        #        img, unescaped=1)
        qpagename = wikiutil.quoteWikiname(self.formatter.page.page_name)
        index = index + _make_index_key(index_letters)
        return '%s%s' % (index, ''.join(html)) 
#return 'Temporarily disabled.'


    def _macro_interwiki(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        from cStringIO import StringIO

        # load interwiki list
        dummy = wikiutil.resolve_wiki(self.request, '')

        buf = StringIO()
        buf.write('<dl>')
        list = wikiutil._interwiki_list.items()
        list.sort()
        for tag, url in list:
            buf.write('<dt><tt><a href="%s">%s</a></tt></dt>' % (
                wikiutil.join_wiki(url, 'RecentChanges'), tag))
            if url.find('$PAGE') == -1:
                buf.write('<dd><tt><a href="%s">%s</a></tt></dd>' % (url, url))
            else:
                buf.write('<dd><tt>%s</tt></dd>' % url)
        buf.write('</dl>')

        return self.formatter.rawHTML(buf.getvalue())


    def _macro_systeminfo(self, args, formatter):
	"""
        import operator, sys
        from cStringIO import StringIO
        from Sycamore import processor
        _ = self._
        # check for 4XSLT
        try:
            import Ft
            ftversion = Ft.__version__
        except ImportError:
            ftversion = None
        except AttributeError:
            ftversion = 'N/A'

        pagelist = wikiutil.getPageList(config.text_dir)
        totalsize = reduce(operator.add, [Page(name).size() for name in pagelist])

        buf = StringIO()
        row = lambda label, value, buf=buf: buf.write(
            '<dt>%s</dt><dd>%s</dd>' %
            (label, value))

        buf.write('<dl>')
        row(_('Python Version'), sys.version)
        row(_('Sycamore Version'), _('Release %s [Revision %s]') % (version.release, version.revision))
        if ftversion:
            row(_('4Suite Version'), ftversion)
        row(_('Number of pages'), len(pagelist))
        row(_('Number of system pages'), len(filter(lambda p,r=self.request: wikiutil.isSystemPage(r,p), pagelist)))
        row(_('Number of backup versions'), len(wikiutil.getBackupList(config.backup_dir, None)))
        row(_('Accumulated page sizes'), totalsize)

        edlog = editlog.EditLog()
        row(_('Entries in edit log'),
            _("%(logcount)s (%(logsize)s bytes)") %
            {'logcount': edlog.lines(), 'logsize': edlog.size()})

        # !!! This puts a heavy load on the server when the log is large,
        # and it can appear on normal pages ==> so disable it for now.
        eventlogger = eventlog.EventLog()
        nonestr = _("NONE")
        row('Event log',
            "%s bytes" % eventlogger.size())
        row(_('Global extension macros'), 
            ', '.join(macro.extension_macros) or nonestr)
        row(_('Local extension macros'), 
            ', '.join(wikiutil.extensionPlugins('macro')) or nonestr)
        row(_('Global extension actions'), 
            ', '.join(action.extension_actions) or nonestr)
        row(_('Local extension actions'), 
            ', '.join(wikiaction.getPlugins()[1]) or nonestr)
        row(_('Installed processors'), 
            ', '.join(processor.processors) or nonestr)
        buf.write('</dl')

        return self.formatter.rawHTML(buf.getvalue())
	"""
	
	return self.formatter.rawHTML('<i>System Info macro is turned off.  It uses too much CPU to be actively used, so if you\'re an admin and want to use it for a minute, then edit wikimacro.py and turn it on.  Otherwise, leave it off! :)</i>')


    def _macro_pagecount(self, args, formatter=None):
        from Sycamore import wikidb
        if not formatter: formatter = self.formatter
        return formatter.text("%d" % (wikidb.getPageCount(self.request),))


    def _macro_icon(self, args, formatter=None):
        if not formatter: formatter = self.formatter
	self.request.formatter = formatter
        icon = args.lower()
        return self.request.theme.make_icon(icon, actionButton=True)

    def _macro_pagelist(self, args, formatter=None):
        import re
        if not formatter: formatter = self.formatter
        _ = self._
        try:
            needle_re = re.compile(args or '', re.IGNORECASE)
        except re.error, e:
            return "<strong>%s: %s</strong>" % (
                _("ERROR in regex '%s'") % (args,), e)

	all_pages = wikiutil.getPageList(self.request)
        hits = filter(needle_re.search, all_pages)
        hits.sort()
	hits = [Page(hit, request) for hit in hits]
        hits = filter(self.request.user.may.read, hits)

        result = []
        result.append(self.formatter.bullet_list(1))
        for page in hits:
            result.append(self.formatter.listitem(1))
            result.append(self.formatter.pagelink(page.page_name, generated=1))
            result.append(self.formatter.listitem(0))
        result.append(self.formatter.bullet_list(0))
        return ''.join(result)


    def __get_Date(self, args, format_date, formatter=None):
        if not formatter: formatter = self.formatter
        _ = self._
        if not args:
            tm = time.time() # always UTC
        elif len(args) >= 19 and args[4] == '-' and args[7] == '-' \
                and args[10] == 'T' and args[13] == ':' and args[16] == ':':
            # we ignore any time zone offsets here, assume UTC,
            # and accept (and ignore) any trailing stuff
            try:
                tm = (
                    int(args[0:4]),
                    int(args[5:7]),
                    int(args[8:10]),
                    int(args[11:13]),
                    int(args[14:16]),
                    int(args[17:19]),
                    0, 0, 0
                )
            except ValueError, e:
                return "<strong>%s: %s</strong>" % (
                    _("Bad timestamp '%s'") % (args,), e)
            # as mktime wants a localtime argument (but we only have UTC),
            # we adjust by our local timezone's offset
            tm = time.mktime(tm) - time.timezone
        else:
            # try raw seconds since epoch in UTC
            try:
                tm = float(args)
            except ValueError, e:
                return "<strong>%s: %s</strong>" % (
                    _("Bad timestamp '%s'") % (args,), e)
        return format_date(tm)

    def _macro_date(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        return self.__get_Date(args, self.request.user.getFormattedDate)

    def _macro_datetime(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        return self.__get_Date(args, self.request.user.getFormattedDateTime)


    def _macro_userpreferences(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        from Sycamore import userform
        return formatter.rawHTML(userform.getUserForm(self.request))

    def _macro_anchor(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        return formatter.anchordef(args or "anchor")

    def _macro_mailto(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        from Sycamore.util.mail import decodeSpamSafeEmail

        args = args or ''
        if args.find(',') == -1:
            email = args
            text = ''
        else:
            email, text = args.split(',', 1)

        email, text = email.strip(), text.strip()

        if self.request.user.valid:
            # decode address and generate mailto: link
            email = decodeSpamSafeEmail(email)
            text = util.web.getLinkIcon(self.request, formatter, "mailto") + \
                formatter.text(text or email)
            result = formatter.url('mailto:' + email, text, 'external', pretty_url=1, unescaped=1)
        else:
            # unknown user, maybe even a spambot, so
            # just return text as given in macro args
            email = formatter.code(1) + \
                formatter.text("<%s>" % email) + \
                formatter.code(0)
            if text:
                result = formatter.text(text) + " " + email
            else:
                result = email

        return result


    def _macro_getval(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        page,key = args.split(',')
        d = self.request.dicts.dict(page)
        result = d.get(key,'')
        return formatter.text(result)

def prepareCached(text):
  return 'request.write("' + text + '")'
