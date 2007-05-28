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

names = [ "titleindex",
         "pagecount", "userpreferences", "generalsettings", "securitysettings", "usergroups",
         # Macros with arguments
         "icon", "anchor", "mailto", "getval", "search", "listtemplates",
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
        "goto"        : [],
        "wordindex"   : ["namespace"],
        "titleindex"  : ["namespace"],
        "pagecount"   : ["namespace"],
        "icon"        : ["user"], # users have different themes and user prefs
        "icon"        : [], # users have different themes and user prefs
        "date"        : ["time"],
        "datetime"    : ["time"],
        "userpreferences" :["time"],
        "anchor"      : [],
        "mailto"      : ["user"],
        "getval"      : ["pages"],
        "search"      : [],
        }

    # we need the lang macros to execute when html is generated,
    # to have correct dir and lang html attributes
    for lang in i18n.languages.keys():
        Dependencies[lang] = []
    

    def __init__(self, parser, formatter=None):
        self.parser = parser
        self.form = self.parser.form
        self.request = self.parser.request
        self.formatter = formatter or self.request.formatter
        self.name = ''
        self._ = self.request.getText

    def execute(self, macro_name, args, formatter=None):
        self.name = macro_name
        macro = wikiutil.importPlugin('macro', macro_name)
        if macro:
            return macro(self, args, formatter=formatter)

        builtins = vars(self.__class__)
        # builtin macro
        if builtins.has_key('_macro_' + macro_name):
            return builtins['_macro_' + macro_name](self, args, formatter=formatter)

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
                html.append('<a href="%s%s">%s</a>\n' % (self.request.getScriptname(), wikiutil.quoteWikiname(name), name))
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


    def _macro_pagecount(self, args, formatter=None):
        from Sycamore import wikidb
        if not formatter: formatter = self.formatter
        return formatter.text("%d" % (wikidb.getPageCount(self.request),))


    def _macro_icon(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        self.request.formatter = formatter
        icon = args.lower()
        return self.request.theme.make_icon(icon, actionButton=True)

    def _macro_listtemplates(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        self.request.formatter = formatter
        templates = wikiutil.getTemplatePages(self.request)
        if not templates: ''
        text = []
        text.append(formatter.bullet_list(1))
        for template in templates:
            template_name = template[len('Templates/'):]
            text.append('%s%s%s' % (formatter.listitem(1), formatter.pagelink(template, template_name), formatter.listitem(0)))
        text.append(formatter.bullet_list(0))
        return ''.join(text)
            

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

    def _macro_userpreferences(self, args, formatter=None):
        if not formatter: formatter = self.formatter
        from Sycamore import userform
        return formatter.rawHTML(userform.getUserForm(self.request))

    def _macro_generalsettings(self, arg, formatter=None):
        if not formatter: formatter = self.formatter
        from Sycamore import sitesettings
        return formatter.rawHTML(sitesettings.getGeneralForm(self.request))

    def _macro_securitysettings(self, arg, formatter=None):
        if not formatter: formatter = self.formatter
        from Sycamore import sitesettings
        return formatter.rawHTML(sitesettings.getSecurityForm(self.request))

    def _macro_usergroups(self, arg, formatter=None):
        if not formatter: formatter = self.formatter
        from Sycamore import sitesettings
        return formatter.rawHTML(sitesettings.getUserGroupForm(self.request))

    def _macro_search(self, arg, formatter=None):
        if not formatter: formatter = self.formatter
        alt, img_url, x, y = self.request.theme.get_icon('searchbutton')
        d = { 'img_url': img_url, 'alt': alt, 'q_pagename': wikiutil.quoteWikiname(formatter.page.page_name) }
        if arg and arg.lower() == 'global':
            d['search_action'] = 'global_search'
        else:
            d['search_action'] = 'search'
        search_html = """<span><form method="GET" action="%(q_pagename)s" style="display:inline !important;">
<input type="hidden" name="action" value="%(search_action)s">
<input class="formfields" type="text" name="inline_string" value="" size="25" maxlength="50">&nbsp;<input type="image" src="%(img_url)s" alt="%(alt)s">&nbsp;&nbsp;
</form></span>""" % d
        return formatter.rawHTML(search_html)

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


def prepareCached(text):
  return 'request.write("' + text + '")'
