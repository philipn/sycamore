# -*- coding: iso-8859-1 -*-
"""
    Sycamore - "text/html+css" Formatter

    This is a cleaned up version of text_html.py.

    @copyright: 2000 - 2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore.formatter.base import FormatterBase
from Sycamore import wikiutil, config, i18n
from Sycamore.Page import Page


#############################################################################
### HTML Formatter
#############################################################################

class Formatter(FormatterBase):
    """
        Send HTML data.
    """

    hardspace = '&nbsp;' # XXX was: '&#160;', but that breaks utf-8

    def __init__(self, request, **kw):
        apply(FormatterBase.__init__, (self, request), kw)
        self._in_li = 0
        self._in_code = 0
        self._base_depth = 0
        self._show_section_numbers = None
	self.name = 'text_html'
	self._preview = kw.get("preview", 0)

        if not hasattr(request, '_fmt_hd_counters'):
            request._fmt_hd_counters = []

    def isPreview(self):
        if self._preview: 
            return True
        return False

    def _langAttr(self):
        result = ''
        lang = self.request.current_lang
        if lang != config.default_lang:
            result = ' lang="%s" dir="%s"' % (lang, i18n.getDirection(lang))

        return result

    def lang(self, lang_name, text):
        """ Insert text with specific lang and direction.
        
            Enclose within span tag if lang_name is different from
            the current lang    
        """
        
        if lang_name != self.request.current_lang:
            dir = i18n.getDirection(lang_name)
            text = wikiutil.escape(text)
            return '<span lang="%(lang_name)s" dir="%(dir)s">%(text)s</span>' % {
                'lang_name': lang_name, 'dir': dir, 'text': text}
        
        return text            
                
    def sysmsg(self, text, **kw):
        return '\n<div class="message">%s</div>\n' % wikiutil.escape(text)

    
    # Links ##############################################################
    
    def pagelink(self, pagename, text=None, **kw):
        """ Link to a page.

            See wikiutil.link_tag() for possible keyword parameters.
        """
        apply(FormatterBase.pagelink, (self, pagename, text), kw)
        return Page(pagename, self.request).link_to(text, **kw)

    def url(self, url, text=None, css=None, show_image=True, **kw):
        """
            Keyword params:
                title - title attribute
                ... some more (!!! TODO) 
        """
        url = wikiutil.mapURL(url)
        pretty = kw.get('pretty_url', 0)
        title = kw.get('title', None)

        if show_image and not pretty and wikiutil.isPicture(url):
            return '<img src="%s" alt="%s">' % (url,url)

        if text is None: text = url

        # create link
        str = '<a'
        if css: str = '%s class="%s"' % (str, css)
        if title: str = '%s title="%s"' % (str, title)
        str = '%s href="%s">%s</a>' % (str, wikiutil.escape(url, 1), text)

        return str


    def interwikilink(self, url, text, **kw):
        wikitag, wikiurl, wikitail, wikitag_bad = wikiutil.resolve_wiki(self.request, url)
        wikiurl = wikiutil.mapURL(wikiurl)
        
        href = wikiutil.join_wiki(wikiurl, wikitail)

        # check for image URL, and possibly return IMG tag
        #if not kw.get('pretty_url', 0) and wikiutil.isPicture(wikitail):
        #    return self.formatter.image(src=href)
            
        # link to self?
        if wikitag is None:
            return self._word_repl(wikitail)
              
        # return InterWiki hyperlink
        if wikitag_bad:
            text = "No Interwiki Link for : " + wikitag
            html_class = 'badinterwiki'
        else:
            html_class = 'interwiki'
        
   #     text = self.highlight_text(text) # also cgi.escapes if necessary
            
        icon = self.request.theme.make_icon('interwiki', {'wikitag': wikitag})
        
        return self.url(href, icon + text,
            title=wikitag, unescaped=1, pretty_url=kw.get('pretty_url', 0), css = html_class, show_image=False)
  
 
    def anchordef(self, id):
        return '<a id="%s"></a>' % id

    def anchorlink(self, name, text, id = None):
        extra = ''
        if id:
            extra = ' id="%s"' % id
        return '<a href="#%s"%s>%s</a>' % (name, extra, wikiutil.escape(text))

    # Text and Text Attributes ###########################################
    
    def text(self, text):
        if self._in_code:
            return wikiutil.escape(text).replace(' ', self.hardspace)
        return wikiutil.escape(text)

    def strong(self, on):
        return ['<strong>', '</strong>'][not on]

    def emphasis(self, on):
        return ['<em>', '</em>'][not on]

    def center(self, on):
        return ['<center>', '</center>'][not on]
        
    def strike(self, on):
        return ['<s>', '</s>'][not on]

    def underline(self, on):
        return ['<u>', '</u>'][not on]

    def highlight(self, on):
        return ['<strong class="highlight">', '</strong>'][not on]

    def sup(self, on):
        return ['<sup>', '</sup>'][not on]

    def sub(self, on):
        return ['<sub>', '</sub>'][not on]

    def code(self, on):
        self._in_code = on
        return ['<tt>', '</tt>'][not on]

    def preformatted(self, on):
        FormatterBase.preformatted(self, on)
        return ['<pre>', '</pre>'][not on]

    # Paragraphs, Lines, Rules ###########################################
    
    def linebreak(self, preformatted=1):
        return ['\n', '<br>\n'][not preformatted]

    def paragraph(self, on):
        FormatterBase.paragraph(self, on)
        if self._in_li:
            self._in_li = self._in_li + 1
        result = ['<p%s>' % self._langAttr(), '\n</p>'][not on]
        return '%s\n' % result
    
    def rule(self, size=0):
        return '<hr noshade="noshade" size="1" />'

    # Lists ##############################################################

    def number_list(self, on, type=None, start=None):
        if on:
            attrs = ''
            if type: attrs += ' type="%s"' % (type,)
            if start is not None: attrs += ' start="%d"' % (start,)
            result = '<ol%s%s>' % (self._langAttr(), attrs)
        else:    
            result = '</ol>\n'
        return '%s\n' % result
    
    def bullet_list(self, on):
        result = ['<ul%s>' % self._langAttr(), '</ul>\n'][not on]
        return '%s\n' % result

    def listitem(self, on, **kw):
        """ List item inherit its lang from the list. """
        self._in_li = on != 0
        if on:
            css_class = kw.get('css_class', None)
            attrs = ''
            if css_class: attrs += ' class="%s"' % (css_class,)
            result = '<li%s>' % (attrs,)
        else:
            result = '</li>'
        return '%s\n' % result

    def definition_list(self, on):
        result = ['<dl>', '</dl>'][not on]
        return '%s\n' % result

    def definition_term(self, on):
        return ['<dt%s>' % (self._langAttr()), '</dt>'][not on]

    def definition_desc(self, on):
        return ['<dd%s>\n' % self._langAttr(), '</dd>\n'][not on]

    def heading(self, depth, title, id = None, **kw):
        # remember depth of first heading, and adapt counting depth accordingly
        if not self._base_depth:
            self._base_depth = depth
        count_depth = max(depth - (self._base_depth - 1), 1)

        # check numbering, possibly changing the default
        if self._show_section_numbers is None:
            self._show_section_numbers = config.show_section_numbers
            numbering = self.request.getPragma('section-numbers', '').lower()
            if numbering in ['0', 'off']:
                self._show_section_numbers = 0
            elif numbering in ['1', 'on']:
                self._show_section_numbers = 1
            elif numbering in ['2', '3', '4', '5', '6']:
                # explicit base level for section number display
                self._show_section_numbers = int(numbering)

        # create section number
        number = ''
        if self._show_section_numbers:
            # count headings on all levels
            self.request._fmt_hd_counters = self.request._fmt_hd_counters[:count_depth]
            while len(self.request._fmt_hd_counters) < count_depth:
                self.request._fmt_hd_counters.append(0)
            self.request._fmt_hd_counters[-1] = self.request._fmt_hd_counters[-1] + 1
            number = '.'.join(map(str, self.request._fmt_hd_counters[self._show_section_numbers-1:]))
            if number: number += ". "

        id_text = ''
        if id:
          id_text = ' id="%s"' % id

        heading_depth = depth + 1
        link_to_heading = False
        if kw.has_key('link_to_heading') and kw['link_to_heading']:
            link_to_heading = True
        if kw.has_key('on'):
            if kw['on']:
                result = '<h%d%s>' % (heading_depth, id_text)
            else:
                result = '</h%d>' % heading_depth
        else:
	    if link_to_heading:
	      title = Page(title, self.request).link_to(know_status=True, know_status_exists=True)
            result = '<h%d%s%s>%s%s%s</h%d>\n' % (
                heading_depth, self._langAttr(), id_text, kw.get('icons', ''), number, title, heading_depth)

	if kw.has_key('action_link'):
	  if kw['action_link'] == 'edit':
	    pagename = kw['pagename']
	    backto = kw['backto']
	    
	    if not (self.request.form.has_key('action') and self.request.form['action'][0] == 'print') and \
	       self.request.user.may.edit(Page(pagename, self.request)):
	         result = '<table class="sectionEdit" width="98%%"><tr><td align="left">%s</td><td align="right">[%s]</td></tr></table>' % \
		    (result, Page(pagename, self.request).link_to(text="edit", querystr="action=edit&backto=%s" % backto, know_status=True, know_status_exists=True))
	    else:
	         result = '<table class="sectionEdit" width="98%%"><tr><td align="left">%s</td></tr></table>' % result
        return result
    
    # Tables #############################################################

    # XXX TODO find better solution for bgcolor, align, valign (deprecated in html4)
    # do not remove current code before making working compliant code

    allowed_table_attrs = {
        'table': ['class', 'width', 'bgcolor', 'border', 'cellpadding'],
        'row': ['class', 'width', 'align', 'valign', 'bgcolor'],
        '': ['colspan', 'rowspan', 'class', 'width', 'align', 'valign', 'bgcolor'],
    }

    def _checkTableAttr(self, attrs, prefix):
        if not attrs: return ''

        result = ''
        for key, val in attrs.items():
            if prefix and key[:len(prefix)] != prefix: continue
            key = key[len(prefix):]
            if key not in self.allowed_table_attrs[prefix]: continue
            result = '%s %s=%s' % (result, key, val)
        return result

    def table(self, on, attrs={}):
        if on:
            # Enclose table inside a div to get correct alignment
            # when using language macros
            attrs = attrs and attrs.copy() or {}
            result = '\n<div%(lang)s %(tableinfo)s>\n<table%(tableAttr)s>' % {
                'lang': self._langAttr(),
                'tableAttr': self._checkTableAttr(attrs, 'table'),
		'tableinfo': 'class="wikitable"',
            }
        else:
            result = '</table>\n</div>'
        return '%s\n' % result
    
    def table_row(self, on, attrs={}):
        if on:
            result = '<tr%s>' % self._checkTableAttr(attrs, 'row')
        else:
            result = '</tr>'
        return '%s\n' % result

    def table_cell(self, on, attrs={}):
        if on:
            result = '<td%s>' % self._checkTableAttr(attrs, '')
        else:
            result = '</td>'
        return '%s\n' % result

