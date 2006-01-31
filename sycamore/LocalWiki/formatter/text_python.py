# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - "text/python" Formatter

    @copyright: 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import time
from LocalWiki.formatter.base import FormatterBase
from LocalWiki import wikiutil, config, i18n, wikimacro
from LocalWiki.Page import Page


#############################################################################
### Wiki to Pythoncode Formatter
#############################################################################

class Formatter:
    """
        Inserts '<<<>>>' into the page and adds python code to
        self.code_fragments for dynamic parts of the page
        (as macros, wikinames...).
        Static parts are formatted with an extrenal formatter.
        Page must be assembled after the parsing to get working python code.
    """

    def __init__(self, request, static = [], formatter = None, **kw):
        if formatter:
            self.formatter = formatter
        else:
            from LocalWiki.formatter.text_html import Formatter
            self.formatter = Formatter(request, store_pagelinks=1, preview=0)

	self._preview = kw.get('preview', 0)
        self.static = static
        self.code_fragments = []
        self.__formatter = "formatter"
        self.__parser = "parser"
        self.request = request
        # XXX never used???
        #self.__static_macros = ['BR', 'GoTo', 'TableOfContents', 'Anchor', 'Icon']
        #self.__static_macros.extend(i18n.languages.keys())
        self.__in_p = 0
        self.__in_pre = 0
        self.text_cmd_begin = '\nrequest.write("""'
        self.text_cmd_end = '""")\n'


    def isPreview(self):
        if self._preview: return True
	else: return False

    def assemble_code(self, text):
        """inserts the code into the generated text
        """
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        text = text.split('<<<>>>', len(self.code_fragments))
        source = self.text_cmd_begin + text[0]
        i = 0
        for t in text[1:]:
            source = (source + self.text_cmd_end +
                      self.code_fragments[i] +
                      self.text_cmd_begin + text[i+1])
            i = i + 1
        source = source + self.text_cmd_end
        self.code_fragments = [] # clear code fragments to make
                                 # this object reusable

        # Automatic invalidation due to moin code changes:
        # we are called from Page.py, so moincode_timestamp is
        # mtime of LocalWiki directory. If we detect, that the
        # saved rendering code is older than the LocalWiki directory
        # we invalidate it by raising an exception. This avoids
        # calling functions that have changed by a code update.
        # Hint: we don't check the mtime of the directories within
        # LocalWiki, so better do a touch if you only modified stuff
        # in a subdirectory.
        #waspcode_timestamp = int(time.time())
        #source = """localwikicode_timestamp = int(os.path.getmtime(os.path.dirname(__file__)))
        #if localwikicode_timestamp > %d: raise "CacheNeedsUpdate"
        #%s
        #""" % (waspcode_timestamp, source)
        return source

    def __getattr__(self, name):
        """ For every thing we have no method/attribute use the formatter
        """
        return getattr(self.formatter, name)

    def __insert_code(self, call):
        """ returns the python code
        """
        self.code_fragments.append(call)
        return '<<<>>>'

    def __is_static(self, dependencies):
        for dep in dependencies:
            if dep not in  self.static: return False
        return True

    def __adjust_formatter_state(self):
        result = ''
        if self.__in_p != self.formatter.in_p:
            result = "%s.in_p = %r\n" % (self.__formatter, self.formatter.in_p)
            self.__in_p = self.formatter.in_p
        if self.__in_pre != self.formatter.in_pre:
            result = "%s%s.in_pre = %r\n" % (result, self.__formatter,
                                           self.formatter.in_pre)
            self.__in_pre = self.formatter.in_pre
        return result
    
    def dynamic_content(self, parser, callback, arg_list = [], arg_dict = {},
                            returns_content = 1):
        adjust = self.__adjust_formatter_state()
        if returns_content:
            return self.__insert_code('%srequest.write(%s.%s(*%r,**%r))' %
                        (adjust, self.__parser, callback, arg_list, arg_dict))
        else:
            return self.__insert_code('%s%s.%s(*%r,**%r)' %
                        (adjust, self.__parser, callback, arg_list, arg_dict))

    def pagelink(self, pagename, text=None, **kw):
        return self.__insert_code('request.write(%s.pagelink(%r, %r, **%r))' %
                        (self.__formatter, pagename, text, kw))

    def add_code(self, code_text):
        return self.__insert_code(code_text)

    def heading(self, depth, title, **kw):        
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

        if self._show_section_numbers:
            return self.__insert_code('request.write(%s.heading(%r, %r, **%r))' %
                        (self.__formatter, depth, title, kw))
        else:
            return self.formatter.heading(depth, title, **kw)

    def macro(self, macro_obj, name, args):
        # call the macro
        if self.__is_static(macro_obj.get_dependencies(name)):
            return macro_obj.execute(name, args, formatter=self)
        else:
            return self.__insert_code(
                '%srequest.write(%s.macro(macro_obj, %r, %r))' %
                (self.__adjust_formatter_state(),
                 self.__formatter, name, args))
            
    def processor(self, processor_name, lines):
        """ processor_name MUST be valid!
        prints out the result insted of returning it!
        """
        Dependencies = wikiutil.importPlugin("processor",
                                            processor_name, "Dependencies")
        if Dependencies == None:
            Dependencies = ["time"]
        if self.__is_static(Dependencies):
            return self.formatter.processor(processor_name, lines)
        else:
            return self.__insert_code('%s%s.processor(%r, %r)' %
                                      (self.__adjust_formatter_state(),
                                       self.__formatter,
                                       processor_name, lines))

