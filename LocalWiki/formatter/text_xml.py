# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - "text/xml" Formatter

    @copyright: 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from xml.sax import saxutils
from LocalWiki.formatter.base import FormatterBase
from LocalWiki import wikiutil, config
from LocalWiki.Page import Page


#############################################################################
### XML Formatter
#############################################################################

class Formatter(FormatterBase):
    """
        Send XML data.
    """

    hardspace = '&nbsp;' # was: '&#160;' but that breaks utf-8 XXX

    def __init__(self, request, **kw):
        apply(FormatterBase.__init__, (self, request), kw)
        self._current_depth = 1
        self._base_depth = 0
        self.in_pre = 0

    def _escape(self, text, extra_mapping={"'": "&apos;", '"': "&quot;"}):
        return saxutils.escape(text, extra_mapping)

    def startDocument(self, pagename):
        encoding = config.charset
        return '<?xml version="1.0" encoding="%s"?>\n<s1 title="%s">' % (
            encoding, self._escape(pagename))

    def endDocument(self):
        result = ""
        while self._current_depth > 1:
            result = result + "</s%d>" % self._current_depth
            self._current_depth = self._current_depth - 1
        return result + '</s1>'

    def sysmsg(self, text, **kw):
        return '<!-- %s -->' % self._escape(text).replace('--', '==')

    def rawHTML(self, markup):
        return '<![CDATA[' + markup.replace(']]>', ']]>]]&gt;<![CDATA[') + ']]>'

    def pagelink(self, pagename, text=None, **kw):
        apply(FormatterBase.pagelink, (self, pagename, text), kw)
        return Page(pagename, formatter=self).link_to(self.request, text)

    def url(self, url, text=None, css=None, **kw):
        if text is None: text = url

        if wikiutil.isPicture(url):
            return '<img src="%s"/>' % (url,)
        else:
            unescaped = kw.get('unescaped', 0)
            str = '<jump'
            ##if css: str = '%s class="%s"' % (str, css)
            if not unescaped: text = self._escape(text)
            str = '%s href="%s">%s</jump>' % (str, self._escape(url), text)
            return str

    def text(self, text):
        if self.in_pre:
            return text.replace(']]>', ']]>]]&gt;<![CDATA[')
        return self._escape(text)

    def rule(self, size=0):
        return "\n<br/>%s<br/>\n" % ("-"*78,) # <hr/> not supported in stylebook
        if size:
            return '<hr size="%d"/>\n' % (size,)
        else:
            return '<hr/>\n'

    def strong(self, on):
        return ['<strong>', '</strong>'][not on]

    def emphasis(self, on):
        return ['<em>', '</em>'][not on]

    def highlight(self, on):
        return ['<strong>', '</strong>'][not on]

    def number_list(self, on, type=None, start=None):
        result = ''
        if self.in_p: result = self.paragraph(0)
        return result + ['<ol>', '</ol>'][not on]

    def bullet_list(self, on):
        result = ''
        if self.in_p: result = self.paragraph(0)
        return result + ['<ul>', '</ul>'][not on]

    def listitem(self, on, **kw):
        return ['<li>', '</li>'][not on]

    def code(self, on):
        return ['<code>', '</code>'][not on]

    def sup(self, on):
        return ['<sup>', '</sup>'][not on]

    def sub(self, on):
        return ['<sub>', '</sub>'][not on]

    def preformatted(self, on):
        FormatterBase.preformatted(self, on)
        result = ''
        if self.in_p: result = self.paragraph(0)
        return result + ['<source><![CDATA[', ']]></source>'][not on]

    def paragraph(self, on):
        FormatterBase.paragraph(self, on)
        return ['<p>', '</p>'][not on]

    def linebreak(self, preformatted=1):
        return ['\n', '<br/>'][not preformatted]

    def heading(self, depth, title, id = None, **kw):
        # remember depth of first heading, and adapt current depth accordingly
        if not self._base_depth:
            self._base_depth = depth
        depth = max(depth + (2 - self._base_depth), 2)

        # close open sections
        result = ""
        while self._current_depth >= depth:
            result = result + "</s%d>" % self._current_depth
            self._current_depth = self._current_depth - 1
        self._current_depth = depth

        id_text = ''
        if id:
          id_text = ' id="%s"' % id

        return result + '<s%d title="%s"%s>\n' % (depth, self._escape(title), id_text)

    def table(self, on, attrs={}):
        return ['<table>', '</table>'][not on]

    def table_row(self, on, attrs={}):
        return ['<tr>', '</tr>'][not on]

    def table_cell(self, on, attrs={}):
        return ['<td>', '</td>'][not on]

    def anchordef(self, id):
        return '<anchor id="%s"/>' % id

    def anchorlink(self, name, text, id=None):
        extra = ''
        if id:
            extra = ' id="%s"' % id
        return '<link anchor="%s"%s>%s</link>' % (name, extra, self._escape(text, {}))

    def underline(self, on):
        return self.strong(on) # no underline in StyleBook

    def definition_list(self, on):
        result = ''
        if self.in_p: result = self.paragraph(0)
        return result + ['<gloss>', '</gloss>'][not on]

    def definition_term(self, on, compact=0):
        return ['<label>', '</label>'][not on]

    def definition_desc(self, on):
        return ['<item>', '</item>'][not on]

    def image(self, **kw):
        valid_attrs = ['src', 'width', 'height', 'alt']
        attrs = {}
        for key, value in kw.items():
            if key in valid_attrs:
                attrs[key] = value
        return apply(FormatterBase.image, (self,), attrs) + '</img>'

