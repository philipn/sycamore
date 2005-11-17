# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Formatter Base Class

    @copyright: 2000 - 2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
from LocalWiki import wikiutil

#############################################################################
### Formatter Base
#############################################################################

class FormatterBase:
    """ This defines the output interface used all over the rest of the code.

        Note that no other means should be used to generate _content_ output,
        while navigational elements (HTML page header/footer) and the like
        can be printed directly without violating output abstraction.
    """

    hardspace = ' '

    def __init__(self, request, **kw):
        self.request = request
        self._ = request.getText

        self._store_pagelinks = kw.get('store_pagelinks', 0)
        self.pagelinks = []
        self.in_p = 0
        self.in_pre = 0

    def lang(self, lang_name, text):
        raise NotImplementedError

    def setPage(self, page):
        self.page = page

    def sysmsg(self, text, **kw):
        """ Emit a system message (embed it into the page).

            Normally used to indicate disabled options, or invalid markup.
        """
        return text

    # Document Level #####################################################
    
    def startDocument(self, pagename):
        return ""

    def endDocument(self):
        return ""

    # Links ##############################################################
    
    def pagelink(self, pagename, text=None, **kw):
        if kw.get('generated', 0): return
        if self._store_pagelinks and pagename not in self.pagelinks:
            self.pagelinks.append(pagename)

    def url(self, url, text=None, css=None, **kw):
        raise NotImplementedError

    def anchordef(self, name):
        return ""

    def anchorlink(self, name, text, id=None):
        return text

    def image(self, **kw):
        """ Take HTML <IMG> tag attributes in `attr`.

            Attribute names have to be lowercase!
        """
        result = '<img'
        for attr, value in kw.items():
            if attr=='html_class':
                attr='class'
            result = result + ' %s="%s"' % (attr, wikiutil.escape(str(value)))
        return result + '>'
 
    # Text and Text Attributes ########################################### 
    
    def text(self, text):
        raise NotImplementedError

    def strong(self, on):
        raise NotImplementedError

    def emphasis(self, on):
        raise NotImplementedError

    def underline(self, on):
        raise NotImplementedError

    def highlight(self, on):
        raise NotImplementedError

    def sup(self, on):
        raise NotImplementedError

    def sub(self, on):
        raise NotImplementedError

    def code(self, on):
        raise NotImplementedError

    def preformatted(self, on):
        self.in_pre = on != 0

    # Paragraphs, Lines, Rules ###########################################

    def linebreak(self, preformatted=1):
        raise NotImplementedError

    def paragraph(self, on):
        self.in_p = on != 0

    def rule(self, size=0):
        raise NotImplementedError

    # Lists ##############################################################

    def number_list(self, on, type=None, start=None):
        raise NotImplementedError

    def bullet_list(self, on):
        raise NotImplementedError

    def listitem(self, on, **kw):
        raise NotImplementedError

    def definition_list(self, on):
        raise NotImplementedError

    def definition_term(self, on, compact=0):
        raise NotImplementedError

    def definition_desc(self, on):
        raise NotImplementedError

    def heading(self, depth, title, **kw):
        raise NotImplementedError

    # Tables #############################################################
    
    def table(self, on, attrs={}):
        raise NotImplementedError

    def table_row(self, on, attrs={}):
        raise NotImplementedError

    def table_cell(self, on, attrs={}):
        raise NotImplementedError

    # Dynamic stuff / Plugins ############################################
    
    def macro(self, macro_obj, name, args):
        # call the macro
        return macro_obj.execute(name, args)    

    def processor(self, processor_name, lines):
        """ processor_name MUST be valid!
            writes out the result instead of returning it!
        """
        processor = wikiutil.importPlugin("processor",
                                          processor_name, "process")
        if not processor and processor_name=="python":
            from LocalWiki.processor.Colorize import process
            processor = process
        processor(self.request, self, lines)
        return ''

    def dynamic_content(self, parser, callback, arg_list = [], arg_dict = {},
                        returns_content = 1):
        content = parser[callback](*arg_list, **arg_dict)
        if returns_content:
            return content
        else:
            return ''

    # Other ##############################################################
    
    def rawHTML(self, markup):
        """ This allows emitting pre-formatted HTML markup, and should be
            used wisely (i.e. very seldom).

            Using this event while generating content results in unwanted
            effects, like loss of markup or insertion of CDATA sections
            when output goes to XML formats.
        """
        return markup

