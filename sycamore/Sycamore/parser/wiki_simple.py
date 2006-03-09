# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Sycamore Wiki Markup Parser

    @copyright: 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, re
import string
from Sycamore import config, wikimacro, wikiutil
from Sycamore.Page import Page
from Sycamore.util import web


#############################################################################
### Sycamore Wiki Markup Parser
#############################################################################

class Parser:
    """
        Object that turns Wiki markup into HTML.

        All formatting commands can be parsed one line at a time, though
        some state is carried over between lines.

        Methods named like _*_repl() are responsible to handle the named regex
        patterns defined in print_html().
    """

    # allow caching
    caching = 1

    # some common strings
    PARENT_PREFIX = wikiutil.PARENT_PREFIX
    attachment_schemas = ["attachment", "inline", "drawing", "borderless"]
    punct_pattern = re.escape('''"\'}]|:,.)?!''')
    url_pattern = ('http|https|ftp|nntp|news|mailto|telnet|wiki|file|' +
            '|'.join(attachment_schemas) + 
            (config.url_schemas and '|' + '|'.join(config.url_schemas) or ''))

    # some common rules
    word_rule = r'(?:(?<![%(l)s])|^)%(parent)s(?:%(subpages)s(?:[%(u)s][%(l)s]+){2,})+(?![%(u)s%(l)s]+)' % {
        'u': config.upperletters,
        'l': config.lowerletters,
        'subpages': config.allow_subpages and (wikiutil.CHILD_PREFIX + '?') or '',
        'parent': config.allow_subpages and (r'(?:%s)?' % re.escape(PARENT_PREFIX)) or '',
    }
    url_rule = r'%(url_guard)s(%(url)s)\:([^\s\<%(punct)s]|([%(punct)s][^\s\<%(punct)s]))+' % {
        'url_guard': '(^|(?<!\w))',
        'url': url_pattern,
        'punct': punct_pattern,
    }

    ol_rule = r"^\s+(?:[0-9]+|[aAiI])\.(?:#\d+)?\s"
    dl_rule = r"^\s+.*?::\s"

    # the big, fat, ugly one ;)
    formatting_rules = r"""(?:(?P<emph_ibb>'''''(?=[^']+'''))
(?P<emph_ibi>'''''(?=[^']+''))
(?P<emph_ib_or_bi>'{5}(?=[^']))
(?P<emph>'{2,3})
(?P<u>__)
(?P<center>(-{1,2}-\>)|(\<--{1,2}))
(?P<sup>\^.*?\^)
(?P<sub>,,[^,]{1,40},,)
(?P<tt>\{\{\{.*?\}\}\})
(?P<processor>(\{\{\{(#!.*|\s*$)))
(?P<pre>(\{\{\{ ?|\}\}\}))
(?P<rule>-{4,})
(?P<strike>(--X)|(X--))
(?P<mdash>--(-){0,1}))
(?P<li>^\s+\*)
(?P<ol>%(ol_rule)s)
(?P<dl>%(dl_rule)s)
(?P<url_bracket>\[((%(url)s)\:|#|\:)[^\s\]]+(\s[^\]]+)?\])
(?P<url>%(url_rule)s)
(?P<email>[-\w._+]+\@[\w-]+\.[\w.-]+)
(?P<alert>\/!\\)
(?P<smiley>(?<=\s)(%(smiley)s)(?=\s))
(?P<smileyA>^(%(smiley)s)(?=\s))
(?P<ent>[<>&])"""  % {
        'url': url_pattern,
        'punct': punct_pattern,
        'macronames': '|'.join(wikimacro.names),
        'ol_rule': ol_rule,
        'dl_rule': dl_rule,
        'url_rule': url_rule,
        'smiley': '|'.join(map(re.escape, config.smileys.keys()))}

    def __init__(self, raw, request, **kw):
        self.raw = raw
        self.request = request
        self.form = request.form
        self._ = request.getText

        self.macro = None

        self.is_em = 0
        self.is_b = 0
        self.is_u = 0
        self.is_center = 0
        self.is_strike = 0
        self.lineno = 0
        self.in_li = 0
        self.in_dd = 0
        self.in_pre = 0
        self.in_table = 0
        self.inhibit_p = 0 # if set, do not auto-create a <p>aragraph
        self.titles = {}

        # holds the nesting level (in chars) of open lists
        self.list_indents = []
        self.list_types = []
	

    def _close_item(self, result):
        #result.append("<!-- close item begin -->\n")
        if self.formatter.in_p:
            result.append(self.formatter.paragraph(0))
        if self.in_li:
            self.in_li = 0
            result.append(self.formatter.listitem(0))
        if self.in_dd:
            self.in_dd = 0
            result.append(self.formatter.definition_desc(0))
        #result.append("<!-- close item end -->\n")


    def interwiki(self, url_and_text, **kw):
        # TODO: maybe support [wiki:Page http://wherever/image.png] ?
        if len(url_and_text) == 1:
            url = url_and_text[0]
            text = None
        else:
            url, text = url_and_text

        url = url[5:] # remove "wiki:"
        if text is None:
            tag, tail = wikiutil.split_wiki(url)
            if tag:
                text = tail
            else:
                text = url
                url = ""
        #elif config.allow_subpages and url[0] == wikiutil.CHILD_PREFIX:
        #    # fancy link to subpage [wiki:/SubPage text]
        #    return self._word_repl(url, text)
        elif Page(url, self.request).exists():
            # fancy link to local page [wiki:LocalPage text]
            return self._word_repl(url, text)

        wikitag, wikiurl, wikitail, wikitag_bad = wikiutil.resolve_wiki(self.request, url)
        wikiurl = wikiutil.mapURL(wikiurl)
        href = wikiutil.join_wiki(wikiurl, wikitail)

        # check for image URL, and possibly return IMG tag
        if not kw.get('pretty_url', 0) and wikiutil.isPicture(wikitail):
            return self.formatter.image(src=href)

        # link to self?
        if wikitag is None:
            return self._word_repl(wikitail)
              
        # return InterWiki hyperlink
        if wikitag_bad:
            html_class = 'badinterwiki'
        else:
            html_class = 'interwiki'
        text = self.highlight_text(text) # also cgi.escapes if necessary

        icon = self.request.theme.make_icon('interwiki', {'wikitag': wikitag}) 
        return self.formatter.url(href, icon + text,
            title=wikitag, unescaped=1, pretty_url=kw.get('pretty_url', 0), css = html_class)


    def _u_repl(self, word):
        """Handle underline."""
        self.is_u = not self.is_u
        return self.formatter.underline(self.is_u)

    def _center_repl(self, word):
        """Handle center."""
        self.is_center = not self.is_center
        return self.formatter.center(self.is_center)

    def _strike_repl(self, word):
        """Handle strikethrough."""
        self.is_strike = not self.is_strike
        return self.formatter.strike(self.is_strike)


    def _emph_repl(self, word):
        """Handle emphasis, i.e. '' and '''."""
        ##print "#", self.is_b, self.is_em, "#"
        if len(word) == 3:
            self.is_b = not self.is_b
            if self.is_em and self.is_b: self.is_b = 2
            return self.formatter.strong(self.is_b)
        else:
            self.is_em = not self.is_em
            if self.is_em and self.is_b: self.is_em = 2
            return self.formatter.emphasis(self.is_em)

    def _emph_ibb_repl(self, word):
        """Handle mixed emphasis, i.e. ''''' followed by '''."""
        self.is_b = not self.is_b
        self.is_em = not self.is_em
        if self.is_em and self.is_b: self.is_b = 2
        return self.formatter.emphasis(self.is_em) + self.formatter.strong(self.is_b)

    def _emph_ibi_repl(self, word):
        """Handle mixed emphasis, i.e. ''''' followed by ''."""
        self.is_b = not self.is_b
        self.is_em = not self.is_em
        if self.is_em and self.is_b: self.is_em = 2
        return self.formatter.strong(self.is_b) + self.formatter.emphasis(self.is_em)

    def _emph_ib_or_bi_repl(self, word):
        """Handle mixed emphasis, exactly five '''''."""
        ##print "*", self.is_b, self.is_em, "*"
        b_before_em = self.is_b > self.is_em > 0
        self.is_b = not self.is_b
        self.is_em = not self.is_em
        if b_before_em:
            return self.formatter.strong(self.is_b) + self.formatter.emphasis(self.is_em)
        else:
            return self.formatter.emphasis(self.is_em) + self.formatter.strong(self.is_b)


    def _sup_repl(self, word):
        """Handle superscript."""
        return self.formatter.sup(1) + \
            self.highlight_text(word[1:-1]) + \
            self.formatter.sup(0)


    def _sub_repl(self, word):
        """Handle subscript."""
        return self.formatter.sub(1) + \
            self.highlight_text(word[2:-2]) + \
            self.formatter.sub(0)


    def _rule_repl(self, word):
        """Handle sequences of dashes."""
        self.inhibit_p = 1
        result = self._undent()
        if len(word) <= 4:
            result = result + self.formatter.rule()
        else:
            result = result + self.formatter.rule(min(len(word), 10) - 2)
        return result


    def _alert_repl(self, word):
        """show alert icon."""
        return self.request.theme.make_icon('attention.png')


    def _word_repl(self, word, text=None):
        """Handle WikiNames."""

        # check for parent links
        # !!! should use wikiutil.AbsPageName here, but setting `text`
        # correctly prevents us from doing this for now
        if config.allow_subpages and word.startswith(self.PARENT_PREFIX):
	    alt_text = True # for making error prettier
	    if not text:
	      text = word
	      alt_text = False
	    base_pagename = self.formatter.page.page_name
	    split_base_pagename = base_pagename.split('/')
	    split_pagename = word.split('/')
            for entry in split_pagename:
	      if entry == '..':
	        try:
	          split_base_pagename.pop()
		except IndexError:
		  # Their link makes no sense
		  if alt_text: return '["%s" %s]' % (word, text)
		  else: return '["%s"]' % word
	      else:
	        split_base_pagename.append(entry)
	    if split_base_pagename:
	      word = split_base_pagename[0]
	      if len(word) > 1:
                for entry in split_base_pagename[1:]:
                  word += '/' + entry

        if not text:
	    text = word
        # if a simple, self-referencing link, emit it as plain text
        if self.is_a_page:
	  if word == self.formatter.page.page_name:
            return text 
        if config.allow_subpages and word.startswith(wikiutil.CHILD_PREFIX):
            word = self.formatter.page.page_name + word
        text = self.highlight_text(text)
        if word == text:
            return self.formatter.pagelink(word)
        else:
            return self.formatter.pagelink(word, text)

    def _notword_repl(self, word):
        """Handle !NotWikiNames."""
        return self.highlight_text(word[1:])


    def _interwiki_repl(self, word):
        """Handle InterWiki links."""
        return self.interwiki(["wiki:" + word])


    def _url_repl(self, word):
        """Handle literal URLs including inline images."""
        #scheme = word.split(":", 1)[0]

        #if scheme == "wiki": return self.interwiki([word])
        #if scheme in self.attachment_schemas:
        #    return self.attachment([word])

        #return self.formatter.url(word, text=self.highlight_text(word))
        scheme = word.split(":", 1)[0]
	if not (scheme == "http"):
        	if scheme == "wiki": return self.interwiki([word])
        	if scheme in self.attachment_schemas:
            		return self.attachment([word])
        	return self.formatter.url(word, text=self.highlight_text(word))

	elif scheme == "http":
		words = word.split(':', 1)
        	if wikiutil.isPicture(word) and re.match(self.url_rule, word):
            		text = self.formatter.image(title=word, alt=word, src=word)
			return self.formatter.rawHTML(text)
        	else:
            		text = web.getLinkIcon(self.request, self.formatter, scheme)
            		text += self.highlight_text(word)
        	return self.formatter.url(word, text, 'external', pretty_url=1, unescaped=1)


    def _wikiname_bracket_repl(self, word):
        """Handle special-char wikinames."""
        wikiname = word[2:-2]
        if wikiname:
	    if string.find(wikiname, "http://") is not -1:
                return self.formatter.rawHTML('<b>!!&mdash;You wrote</b> %s<b>, you probably meant to write</b> [%s] <b>(or just </b>%s<b>) to make an outside the wiki link&mdash;!!</b>' % (word, wikiname, wikiname))
            return self._word_repl(wikiname)
        else:
            return word


    def _url_bracket_repl(self, word):
        """Handle bracketed URLs."""

        # Local extended link?
        if word[1] == ':':
            words = word[2:-1].split(':', 1)
            if len(words) == 1: words = words * 2
            return self._word_repl(words[0], words[1])

        # Traditional split on space
        words = word[1:-1].split(None, 1)
        if len(words) == 1: words = words * 2

        if words[0][0] == '#':
            # anchor link
            return self.formatter.url(words[0], self.highlight_text(words[1]))

        scheme = words[0].split(":", 1)[0]
        if scheme == "wiki": return self.interwiki(words, pretty_url=1)
        if scheme in self.attachment_schemas:
            return self.attachment(words, pretty_url=1)

        if wikiutil.isPicture(words[0]) and re.match(self.url_rule, words[0]) and (words[0] is words[1]):
            text = self.formatter.image(title=words[1], alt=words[1], src=words[0])
        else:
            text = web.getLinkIcon(self.request, self.formatter, scheme)
            text += self.highlight_text(words[1])
        return self.formatter.url(words[0], text, 'external', pretty_url=1, unescaped=1)

    def _bracket_link_repl(self, word):
        """Handle our standard format links. format:  ["Page name" text]"""
	words = word[1:-1].split("\" ",1)
	pagename = (words[0]).split("\"",1)[1]
	text = words[1]
	
	if string.find(words[0], "http://") is not -1:
		return self.formatter.rawHTML('<b>!!&mdash;You wrote</b> %s<b>, you probably meant to write</b> [%s %s] <b>to make an outside the wiki link&mdash;!!</b>' % (word, pagename, text))
        #return self.formatter.url("../index.cgi/" +pagename, text)
	return self._word_repl(pagename, text)


    def _email_repl(self, word):
        """Handle email addresses (without a leading mailto:)."""
        return self.formatter.url("mailto:" + word, self.highlight_text(word))


    def _ent_repl(self, word):
        """Handle SGML entities."""
        return self.formatter.text(word)
        #return {'&': '&amp;',
        #        '<': '&lt;',
        #        '>': '&gt;'}[word]


    def _ent_numeric_repl(self, word):
        """Handle numeric SGML entities."""
        return self.formatter.rawHTML(word)


    def _li_repl(self, match):
        """Handle bullet lists."""
        result = []
        self._close_item(result)
        self.inhibit_p = 1
        self.in_li = 1
        css_class = ''
        if self.line_was_empty and not self.first_list_item:
            css_class = 'gap'
        result.append(" "*4*self._indent_level())
        result.append(self.formatter.listitem(1, css_class=css_class))
        result.append(self.formatter.paragraph(1))
        return ''.join(result)


    def _ol_repl(self, match):
        """Handle numbered lists."""
        return self._li_repl(match)


    def _dl_repl(self, match):
        """Handle definition lists."""
        result = []
        self._close_item(result)
        self.inhibit_p = 1
        self.in_dd = 1
        result.extend([
            " "*4*self._indent_level(),
            self.formatter.definition_term(1),
            self.formatter.text(match[:-3]),
            self.formatter.definition_term(0),
            self.formatter.definition_desc(1),
            self.formatter.paragraph(1)
        ])
        return ''.join(result)


    def _indent_level(self):
        """Return current char-wise indent level."""
        return len(self.list_indents) and self.list_indents[-1]


    def _indent_to(self, new_level, list_type, numtype, numstart):
        """Close and open lists."""
        open = []   # don't make one out of these two statements!
        close = []

        # Close open paragraphs and list items
        if self._indent_level() != new_level:
            self._close_item(close)
        else:
            if not self.line_was_empty:                                                                                                       
                self.inhibit_p = 1                                                                                                            
    
        # Close lists while char-wise indent is greater than the current one
        while self._indent_level() > new_level:
            indentstr = " "*4*self._indent_level()
            if self.list_types[-1] == 'ol':
                tag = self.formatter.number_list(0)
            elif self.list_types[-1] == 'dl':
                tag = self.formatter.definition_list(0)
            else:
                tag = self.formatter.bullet_list(0)
            close.append("\n%s%s\n" % (indentstr, tag))

            del(self.list_indents[-1])
            del(self.list_types[-1])
            
            if new_level:
                self.inhibit_p = 1
            else:
                self.inhibit_p = 0
                
            # XXX This would give valid, but silly looking html.
            # the right way is that inner list has to be CONTAINED in outer li -
            # but in the one before, not a new one, like this code does:
            #if self.list_types: # we are still in a list, bracket with li /li
            #    if self.list_types[-1] in ['ol', 'ul']:
            #        open.append(" "*4*new_level)
            #        open.append(self.formatter.listitem(0))
            #    elif self.list_types[-1] == 'dl':
            #        open.append(" "*4*new_level)
            #        open.append(self.formatter.definition_desc(0))

        # Open new list, if necessary
        if self._indent_level() < new_level:
            # XXX see comment 10 lines above
            #if self.list_types: # we already are in a list, bracket with li /li
            #    if self.list_types[-1] in ['ol', 'ul']:
            #        open.append(" "*4*new_level)
            #        open.append(self.formatter.listitem(1))
            #    elif self.list_types[-1] == 'dl':
            #        open.append(" "*4*new_level)
            #        open.append(self.formatter.definition_desc(1))
                    
            self.list_indents.append(new_level)
            self.list_types.append(list_type)
            
            indentstr = " "*4*new_level
            if list_type == 'ol':
                tag = self.formatter.number_list(1, numtype, numstart)
            elif list_type == 'dl':
                tag = self.formatter.definition_list(1)
            else:
                tag = self.formatter.bullet_list(1)
            open.append("\n%s%s\n" % (indentstr, tag))
            
            self.first_list_item = 1
            self.inhibit_p = 1
            
        # If list level changes, close an open table
        if self.in_table and (open or close):
            close[0:0] = [self.formatter.table(0)]
            self.in_table = 0

        return ''.join(close) + ''.join(open)


    def _undent(self):
        """Close all open lists."""
        result = []
        #result.append("<!-- _undent start -->\n")
        self._close_item(result)
        for type in self.list_types:
            if type == 'ol':
                result.append(self.formatter.number_list(0))
            elif type == 'dl':
                result.append(self.formatter.definition_list(0))
            else:
                result.append(self.formatter.bullet_list(0))
        #result.append("<!-- _undent end -->\n")
        self.list_indents = []
        self.list_types = []
        return ''.join(result)


    def _tt_repl(self, word):
        """Handle inline code."""
        return self.formatter.code(1) + \
            self.highlight_text(word[3:-3]) + \
            self.formatter.code(0)


    def _tt_bt_repl(self, word):
        """Handle backticked inline code."""
        if len(word) == 2: return ""
        return self.formatter.code(1) + \
            self.highlight_text(word[1:-1]) + \
            self.formatter.code(0)


    def _getTableAttrs(self, attrdef):
        # skip "|" and initial "<"
        while attrdef and attrdef[0] == "|":
            attrdef = attrdef[1:]
        if not attrdef or attrdef[0] != "<":
            return {}, ''
        attrdef = attrdef[1:]

        # extension for special table markup
        def table_extension(key, parser, attrs, wiki_parser=self):
            _ = wiki_parser._
            msg = ''
            if key[0] in "0123456789":
                token = parser.get_token()
                if token != '%':
                    wanted = '%'
                    msg = _('Expected "%(wanted)s" after "%(key)s", got "%(token)s"') % {
                        'wanted': wanted, 'key': key, 'token': token}
                else:
                    try:
                        dummy = int(key)
                    except ValueError:
                        msg = _('Expected an integer "%(key)s" before "%(token)s"') % {
                            'key': key, 'token': token}
                    else:
                        attrs['width'] = '"%s%%"' % key
            elif key == '-':
                arg = parser.get_token()
                try:
                    dummy = int(arg)
                except ValueError:
                    msg = _('Expected an integer "%(arg)s" after "%(key)s"') % {
                        'arg': arg, 'key': key}
                else:
                    attrs['colspan'] = '"%s"' % arg
            elif key == '|':
                arg = parser.get_token()
                try:
                    dummy = int(arg)
                except ValueError:
                    msg = _('Expected an integer "%(arg)s" after "%(key)s"') % {
                        'arg': arg, 'key': key}
                else:
                    attrs['rowspan'] = '"%s"' % arg
            elif key == '(':
                attrs['align'] = '"left"'
            elif key == ':':
                attrs['align'] = '"center"'
            elif key == ')':
                attrs['align'] = '"right"'
            elif key == '^':
                attrs['valign'] = '"top"'
            elif key == 'v':
                attrs['valign'] = '"bottom"'
            elif key == '#':
                arg = parser.get_token()
                try:
                    if len(arg) != 6: raise ValueError
                    dummy = int(arg, 16)
                except ValueError:
                    msg = _('Expected a color value "%(arg)s" after "%(key)s"') % {
                        'arg': arg, 'key': key}
                else:
                    attrs['bgcolor'] = '"#%s"' % arg
            else:
                msg = None
            #print "key: %s\nattrs: %s" % (key, str(attrs))
            return msg

        # scan attributes
        attr, msg = wikiutil.parseAttributes(self.request, attrdef, '>', table_extension)
        if msg: msg = '<strong class="highlight">%s</strong>' % msg
        #print attr
        return attr, msg

    def _processor_repl(self, word):
        """Handle processed code displays."""
        if word[:3] == '{{{': word = word[3:]

        self.processor = None
        self.processor_name = None
        s_word = word.strip()
        if s_word == '#!':
            # empty bang paths lead to a normal code display
            # can be used to escape real, non-empty bang paths
            word = ''
            self.in_pre = 3
            return  self.formatter.preformatted(1)
        elif s_word[:2] == '#!':
            processor_name = s_word[2:].split()[0]
            self.processor = wikiutil.importPlugin("processor", processor_name, "process")
            if not self.processor and s_word.find('python') > 0:
                from Sycamore.processor.Colorize import process
                self.processor = process
                self.processor_name = "Colorize"

        if self.processor:
            self.processor_name = processor_name
            self.in_pre = 2
            self.colorize_lines = [word]
            return ''
        elif  s_word:
            self.in_pre = 3
            return self.formatter.preformatted(1) + \
                   self.formatter.text(s_word + ' (-)')
        else:
            self.in_pre = 1
            return ''

    def _pre_repl(self, word):
        """Handle code displays."""
        word = word.strip()
        if word == '{{{' and not self.in_pre:
            self.in_pre = 3
            return self.formatter.preformatted(self.in_pre)
        elif word == '}}}' and self.in_pre:
            self.in_pre = 0
            self.inhibit_p = 1
            return self.formatter.preformatted(self.in_pre)
        return word

    def _mdash_repl(self, word):
	"""Convert -- to &mdash;"""
	return "&mdash;"

    def _smiley_repl(self, word):
        """Handle smileys."""
        return wikiutil.getSmiley(word, self.formatter)

    _smileyA_repl = _smiley_repl


    def _comment_repl(self, word):
        return ''


    def _macro_repl(self, word):
        """Handle macros ([[macroname]])."""
        macro_name = word[2:-2]
        #self.inhibit_p = 1 # fixes UserPreferences, but makes new trouble!

        # check for arguments
        args = None
        if macro_name.count("("):
            macro_name, args = macro_name.split('(', 1)
            args = args[:-1]

        # create macro instance
        if self.macro is None:
            self.macro = wikimacro.Macro(self)

        # call the macro
        return self.formatter.macro(self.macro, macro_name, args)


    def highlight_text(self, text, **kw):
        if not self.hilite_re: return self.formatter.text(text)
        
        # work around for dom/xml formatter
        # if not self.hilite_re: return text
        # XXX bad idea: this allowed `<b>raw html</b>` to get through!
        
        result = []
        lastpos = 0
        match = self.hilite_re.search(text)
        while match and lastpos < len(text):
            # add the match we found
            result.append(self.formatter.text(text[lastpos:match.start()]))
            result.append(self.formatter.highlight(1))
            result.append(self.formatter.text(match.group(0)))
            result.append(self.formatter.highlight(0))

            # search for the next one
            lastpos = match.end() + (match.end() == lastpos)
            match = self.hilite_re.search(text, lastpos)

        result.append(self.formatter.text(text[lastpos:]))
        return ''.join(result)

    def scan(self, scan_re, line):
        """ scans the line for wiki syntax and replaces the
            found regular expressions
            calls highlight_text if self.hilite_re is set
        """
        result = []
        lastpos = 0
        match = scan_re.search(line)
        while match and lastpos < len(line):
            # add the match we found
            if self.hilite_re:
                result.append(self.highlight_text(line[lastpos:match.start()]))
            else:
                result.append(self.formatter.text(line[lastpos:match.start()]))
            result.append(self.replace(match))

            # search for the next one
            lastpos = match.end() + (match.end() == lastpos)
            match = scan_re.search(line, lastpos)

        if self.hilite_re:
            result.append(self.highlight_text(line[lastpos:]))
        else:
            result.append(self.formatter.text(line[lastpos:]))
        return ''.join(result)

    def replace(self, match):
        #hit = filter(lambda g: g[1], match.groupdict().items())
        for type, hit in match.groupdict().items():
            if hit is not None and type != "hmarker":
                ##print "###", cgi.escape(`type`), cgi.escape(`hit`), "###"
                if self.in_pre and type not in ['pre', 'ent']:
                    return self.highlight_text(hit)
                else:
                    return getattr(self, '_' + type + '_repl')(hit)
        else:
            import pprint
            raise Exception("Can't handle match " + `match`
                + "\n" + pprint.pformat(match.groupdict())
                + "\n" + pprint.pformat(match.groups()) )

        return ""


    def format(self, formatter):
        """ For each line, scan through looking for magic
            strings, outputting verbatim any intervening text.
        """
	if formatter.__dict__.has_key('page'):
	  self.is_a_page = True
	else: self.is_a_page = False

        self.formatter = formatter
	self.hilite_re = ''

        # prepare regex patterns
        rules = self.formatting_rules.replace('\n', '|')
        rules = rules + r'|(?P<wikiname_bracket>\["[^\[\]]+?"\])'
	rules = rules + r'|(?P<bracket_link>\["[^\[\]]+?" [^\[\]]+?\])'
        if config.bang_meta:
            rules = r'(?P<notword>!%(word_rule)s)|%(rules)s' % {
                'word_rule': self.word_rule,
                'rules': rules,
            }
        if config.backtick_meta:
            rules = rules + r'|(?P<tt_bt>`.*?`)'
        if config.allow_numeric_entities:
            rules = r'(?P<ent_numeric>&#\d{1,5};)|' + rules

        scan_re = re.compile(rules)
        number_re = re.compile(self.ol_rule)
        term_re = re.compile(self.dl_rule)
        indent_re = re.compile("^\s*")
        eol_re = re.compile(r'\r?\n')

        # get text and replace TABs
        rawtext = self.raw.expandtabs()

        # go through the lines
        self.lineno = 0
        self.lines = eol_re.split(rawtext)
        self.line_is_empty = 0

        for line in self.lines:
            self.lineno = self.lineno + 1
            self.table_rowstart = 1
            self.line_was_empty = self.line_is_empty
            self.line_is_empty = 0
            self.first_list_item = 0
            self.inhibit_p = 0

            if self.in_pre:
                # still looking for processing instructions
                if self.in_pre == 1:
                    self.processor = None
                    processor_name = ''
                    if (line.strip()[:2] == "#!"):
                        from Sycamore.processor import processors
                        processor_name = line.strip()[2:].split()[0]
                        self.processor = wikiutil.importPlugin("processor", processor_name, "process")
                        if not self.processor and (line.find('python') > 0):
                            from Sycamore.processor.Colorize import process
                            self.processor = process
                            processor_name = "Colorize"
                    if self.processor:
                        self.in_pre = 2
                        self.colorize_lines = [line]
                        self.processor_name = processor_name
                        continue
                    else:
                        self.request.write(self.formatter.preformatted(1))
                        self.in_pre = 3
                if self.in_pre == 2:
                    # processing mode
                    endpos = line.find("}}}")
                    if endpos == -1:
                        self.colorize_lines.append(line)
                        continue
                    if line[:endpos]:
                        self.colorize_lines.append(line[:endpos])
                    self.request.write(
                        self.formatter.processor(self.processor_name, self.colorize_lines))
                    del self.colorize_lines
                    self.in_pre = 0
                    self.processor = None

                    # send rest of line through regex machinery
                    line = line[endpos+3:]                    
            else:
                # paragraph break on empty lines
                if not line.strip():
                    #self.request.write("<!-- empty line start -->\n")
                    if self.formatter.in_p:
                        self.request.write(self.formatter.paragraph(0))
                    if self.in_table:
                        self.request.write(self.formatter.table(0))
                        self.in_table = 0
                    self.line_is_empty = 1
                    #self.request.write("<!-- empty line end -->\n")
                    continue

                # check indent level
                indent = indent_re.match(line)
                indlen = len(indent.group(0))
                indtype = "ul"
                numtype = None
                numstart = None
                if indlen:
                    match = number_re.match(line)
                    if match:
                        numtype, numstart = match.group(0).strip().split('.')
                        numtype = numtype[0]

                        if numstart and numstart[0] == "#":
                            numstart = int(numstart[1:])
                        else:
                            numstart = None

                        indtype = "ol"
                    else:
                        match = term_re.match(line)
                        if match:
                            indtype = "dl"

                # output proper indentation tags
                #self.request.write("<!-- inhibit_p==%d -->\n" % self.inhibit_p)
                #self.request.write("<!-- #%d calling _indent_to -->\n" % self.lineno)
                self.request.write(self._indent_to(indlen, indtype, numtype, numstart))
                #self.request.write("<!-- #%d after calling _indent_to -->\n" % self.lineno)
                #self.request.write("<!-- inhibit_p==%d -->\n" % self.inhibit_p)

                # start or end table mode
                if not self.in_table and line[indlen:indlen+2] == "||" and line[-2:] == "||":
                    attrs, attrerr = self._getTableAttrs(line[indlen+2:])
                    self.request.write(self.formatter.table(1, attrs) + attrerr)
                    self.in_table = self.lineno
                elif self.in_table and not(line[:2]=="##" or # intra-table comments should not break a table 
                    line[indlen:indlen+2] == "||" and line[-2:] == "||"):
                    self.request.write(self.formatter.table(0))
                    self.in_table = 0

            # convert line from wiki markup to HTML and print it
            if not self.in_pre:   # we don't want to have trailing blanks in pre
                line = line + " " # we don't have \n as whitespace any more

            formatted_line = self.scan(scan_re, line) # this also sets self.inhibit_p as side effect!
            
            #self.request.write("<!-- inhibit_p==%d -->\n" % self.inhibit_p)
            if not (self.inhibit_p or self.in_pre or self.in_table or self.formatter.in_p):
                self.request.write(self.formatter.paragraph(1))

            #self.request.write("<!-- %s\n     start -->\n" % line)
            self.request.write(formatted_line)
            #self.request.write("<!-- end -->\n")

            if self.in_pre:
                self.request.write(self.formatter.linebreak())
            #if self.in_li:
            #    self.in_li = 0
            #    self.request.write(self.formatter.listitem(0))

        # close code displays, paragraphs, tables and open lists
        if self.in_pre: self.request.write(self.formatter.preformatted(0))
        if self.formatter.in_p: self.request.write(self.formatter.paragraph(0))
        if self.in_table: self.request.write(self.formatter.table(0))
        self.request.write(self._undent())

