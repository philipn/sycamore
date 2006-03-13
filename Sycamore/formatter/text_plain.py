# -*- coding: iso-8859-1 -*-
"""
    Sycamore - "text/plain" Formatter

    @copyright: 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from Sycamore.formatter.base import FormatterBase

#############################################################################
### Plain Text Formatter
#############################################################################

class Formatter(FormatterBase):
    """
        Send text data.
    """

    hardspace = ' '

    def __init__(self, request, **kw):
        apply(FormatterBase.__init__, (self, request), kw)

    def startDocument(self, pagename):
        line = "*" * (len(pagename)+2) + '\n'
        return "<pre>%s %s \n%s" % (line, pagename, line)

    def endDocument(self):
        return '\n'

    def sysmsg(self, text, **kw):
        return '\n\n*** %s ***\n\n' % text

    def pagelink(self, pagename, text=None, **kw):
        apply(FormatterBase.pagelink, (self, pagename, text), kw)
        return ">>%s<<" % (pagename,)

    def url(self, url, text=None, css=None, **kw):
        if text is None:
            return url
        else:
            return '%s [%s]' % (text, url)

    def text(self, text):
        return text

    def rule(self, size=0):
        size = min(size, 10)
        ch = "---~=*+#####"[size]
        return (ch * 79) + '\n'

    def strong(self, on):
        return '*'

    def emphasis(self, on):
        return '/'

    def highlight(self, on):
        return ''

    def number_list(self, on, type=None, start=None):
        # !!! remember list state
        return ''

    def bullet_list(self, on):
        # !!! remember list state
        return ''

    def listitem(self, on, **kw):
        # !!! return number for ordered lists
        return ' * '

    def sup(self, on):
        return '^'

    def sub(self, on):
        return '_'

    def code(self, on):
        return ['`', '´'][not on]

    def preformatted(self, on):
        FormatterBase.preformatted(self, on)
        snip = '---%<'
        snip = snip + ('-' * (78 - len(snip)))
        if on:
            return '\n' + snip
        else:
            return snip + '\n'

    def paragraph(self, on):
        FormatterBase.paragraph(self, on)
        return ['\n', ''][not on]

    def linebreak(self, preformatted=1):
        return '\n'

    def heading(self, depth, title, **kw):
        return '\n%s\n%s\n%s\n\n' % ('=' * len(title), title, '=' * len(title))

    def table(self, on, attrs={}):
        return ''

    def table_row(self, on, attrs={}):
        return ''

    def table_cell(self, on, attrs={}):
        return ''

    def underline(self, on):
        return '_'

    def definition_list(self, on):
        return ''

    def definition_term(self, on, compact=0):
        result = ''
        if not compact: result = result + '\n'
        if not on: result = result + ':\n'
        return result

    def definition_desc(self, on):
        return ['    ', '\n'][not on]

    def image(self, **kw):
        if kw.has_key('alt'):
            return kw['alt']
        return ''

    def lang(self, lang_name, text):
        return text  
