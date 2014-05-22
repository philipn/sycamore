# -*- coding: utf-8 -*-
"""
    Sycamore - Sycamore Wiki Markup Parser

    @copyright: 2004-2007 by Philip Neustrom <philipn@gmail.com
    @copyright: 2000, 2001, 2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os
import re
import string
import hashlib

from Sycamore import config
from Sycamore import wikimacro
from Sycamore import wikiutil

from Sycamore.Page import Page
from Sycamore.util import web
from Sycamore.parser.wiki_simple import Parser as SimpleParser

#############################################################################
### Utilities
#############################################################################
_heading_re = re.compile(
    '(?P<heading>^\s*(?P<hmarker>=+)(\s)*.*(\s)*(?P=hmarker)( )*$)')

def _is_heading(line):
    """
    Is the line a heading?
    """
    return _heading_re.match(line)

#############################################################################
### Sycamore Wiki Markup Parser
#############################################################################

class Parser(SimpleParser):
    """
    Object that turns Wiki markup into HTML.

    All formatting commands can be parsed one line at a time, though
    some state is carried over between lines.

    Methods named like _*_repl() are responsible to handle the named regex
    patterns defined in print_html().
    """

    DEFINITION_OPERATOR = ':='

    # the big, fat, ugly one ;)
    formatting_a = r"""
(?P<comment>^(\#((\#)|(acl)|(redirect))).*$)
(?P<tableZ>\|\| $)
(?P<table>(?:\|\|)+(?:<[^>]*?>)?(?=.))
(?P<macro>\[\[(%(macronames)s)(?:\(.*?\))?\]\])"""
    formatting_b = r"""
(?P<heading>^\s*(?P<hmarker>=+)(\s)*.*(\s)*(?P=hmarker)( )*$)"""

    formatting_rules_dict = {'macronames': '|'.join(wikimacro.names),
                             'def_op': DEFINITION_OPERATOR}
    formatting_rules_dict.update(SimpleParser.formatting_rules_dict)
    formatting_rules = (
        "(?:%s%s)%s%s" % (SimpleParser.formatting_a, formatting_a,
                          SimpleParser.formatting_b, formatting_b)
                       ) % formatting_rules_dict

    def format(self, formatter, inline_edit_default_state=None):
        """
        For each line, scan through looking for magic
        strings, outputting verbatim any intervening text.
        """
        if hasattr(formatter, 'page'):
            self.is_a_page = True
        else:
            self.is_a_page = False

        self.formatter = formatter
        self.hilite_re = ''

        # prepare regex patterns
        rules = self.formatting_rules.replace('\n', '|')
        rules = rules + r'|(?P<wikiname_bracket>\["[^\[\]"]+?"\])'
        rules = rules + r'|(?P<bracket_link>\["[^\[\]]+?" [^\[\]]+?\])'
        if config.bang_meta:
            rules = r'(?P<notword>!%(word_rule)s)|%(rules)s' % {
                'word_rule': self.word_rule,
                'rules': rules,
            }
        if config.allow_numeric_entities:
            rules = r'(?P<ent_numeric>&#\d{1,5};)|' + rules

        scan_re = re.compile(rules,re.IGNORECASE)
        number_re = re.compile(self.ol_rule,re.IGNORECASE)
        term_re = re.compile(self.dl_rule,re.IGNORECASE)
        indent_re = re.compile("^\s*")
        eol_re = re.compile(r'\r?\n')

        # get text and replace TABs
        rawtext = self.raw.expandtabs()

        # go through the lines
        self.lineno = 0
        self.lines = eol_re.split(rawtext)
        self.line_is_empty = 0
        self.inhibit_br = 0
        self.force_print_p = False

        for line in self.lines:
            self.lineno = self.lineno + 1
            self.table_rowstart = 1
            self.line_was_empty = self.line_is_empty
            self.line_is_empty = 0
            self.first_list_item = 0
            self.formatter.printed_inline_edit_id = False
            self.inhibit_p = 0
            if self.inhibit_br > 0:
                self.inhibit_br -= 1
            else:
                self.inhibit_br = 0

            self.formatter.inline_edit_force_state = inline_edit_default_state

            if inline_edit_default_state is not None:
                self.formatter.inline_edit = inline_edit_default_state
            else:
                self.formatter.inline_edit = True

            if self.formatter.inline_edit:
                self.formatter.edit_id += 1

            if not self.in_pre:
                # paragraph break on empty lines
                if not line.strip():
                    #self.request.write("<!-- empty line start -->\n")
                    if self.formatter.in_p:
                        self.request.write(self.formatter.paragraph(0))
                    if self.in_table:
                        self.request.write(self.formatter.table(0))
                        self.in_table = 0
                    self.line_is_empty = 1
                    self.force_print_p = False
                    #self.request.write("<!-- empty line end -->\n")
                    continue
                elif self.print_br():
                    self.request.write('<br/>')
                    # to avoid printing two if they did [[br]]
                    self.inhibit_br += 1 
 
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
                #self.request.write("<!-- inhibit_p==%d -->\n" %
                #                   self.inhibit_p)
                #self.request.write("<!-- #%d calling _indent_to -->\n" %
                #                   self.lineno)
                self.request.write(self._indent_to(indlen, indtype, numtype,
                                                   numstart))
                #self.request.write("<!-- #%d after calling _indent_to -->\n" %
                #                   self.lineno)
                #self.request.write("<!-- inhibit_p==%d -->\n" %
                #                   self.inhibit_p)

                # start or end table mode
                if (not self.in_table and line[indlen:indlen+2] == "||" and
                    line[-2:] == "||"):
                    attrs, attrerr = self._getTableAttrs(line[indlen+2:])
                    self.request.write(self.formatter.table(1, attrs) +
                                       attrerr)
                    self.in_table = self.lineno
                # intra-table comments should not break a table 
                elif (self.in_table and not
                      (line[:2]=="##" or
                       (line[indlen:indlen+2] == "||" and line[-2:] == "||"))):
                    self.request.write(self.formatter.table(0))
                    self.in_table = 0
                    self.force_print_p = True

            # convert line from wiki markup to HTML and print it
            # we don't want to have trailing blanks in pre
            if not self.in_pre:
                line = line + " " # we don't have \n as whitespace any more

            if self.formatter.in_list > 0:
                self.force_print_p = False
            elif self.formatter.just_printed_heading:
                if _is_heading(line):
                    self.force_print_p = False
                else:
                    if not self.formatter.in_p and not self.in_table:
                        self.force_print_p = False
                        self.request.write(self.formatter.paragraph(1))
                        self.inhibit_br -= 1 
                        self.force_print_p = True
                    self.formatter.just_printed_heading = False
            elif (self.force_print_p and not self.formatter.in_p and not
                  self.in_table):
                self.force_print_p = False
                self.request.write(self.formatter.paragraph(1))
            elif self.formatter.in_p or self.in_table:
                self.force_print_p = False
            
            # this also sets self.inhibit_p as side effect!
            formatted_line = self.scan(scan_re, line) 
            #self.request.write("<!-- inhibit_p==%d -->\n" % self.inhibit_p)

            #self.request.write("<!-- inhibit_p==%d -->\n" % self.inhibit_p)
            # we check against force_print_p here to avoid printing out <p>
            # (above) and then immediately </p>
            if not (self.inhibit_p or self.in_pre or self.in_table or
                    self.force_print_p):
                 self.request.write(self.formatter.paragraph(1))
            elif (self.formatter.in_list > 0 and not
                  self.formatter.printed_inline_edit_id):
                 self.request.write(self.formatter.paragraph(1))

            #self.request.write("<!-- %s\n     start -->\n" % line)
            self.request.write(formatted_line)
            #self.request.write("<!-- end -->\n")

            if self.in_pre:
                self.request.write(self.formatter.linebreak())

        # close code displays, paragraphs, tables and open lists
        if self.in_pre:
            self.request.write(self.formatter.preformatted(0))
        if self.in_table:
            self.request.write(self.formatter.table(0))
        self.request.write(self._undent())

        # check for pending footnotes
        if getattr(self.request, 'footnotes', None):
            from Sycamore.macro.footnote import emit_footnotes
            emit_footnotes(self.request, self.formatter)

    def _tableZ_repl(self, word):
        """
        Handle table row end.
        """
        if self.in_table:
            return self.formatter.table_cell(0) + self.formatter.table_row(0)
        else:
            return word

    def _table_repl(self, word):
        """
        Handle table cell separator.
        """
        if self.in_table:
            # check for attributes
            attrs, attrerr = self._getTableAttrs(word)

            # start the table row?
            if self.table_rowstart:
                self.table_rowstart = 0
                leader = self.formatter.table_row(1, attrs)
            else:
                leader = self.formatter.table_cell(0)

            # check for adjacent cell markers
            if word.count("|") > 2:
                if not attrs.has_key('align'):
                    attrs['align'] = '"center"'
                if not attrs.has_key('colspan'):
                    attrs['colspan'] = '"%d"' % (word.count("|")/2)

            # return the complete cell markup           
            return leader + self.formatter.table_cell(1, attrs) + attrerr
        else:
            return wikiutil.escape(word)

    def _heading_repl(self, word):
        """
        Handle section headings.
        """
        self.inhibit_p = 1
        self.inhibit_br += 2
        icons = ''
        result = []
        if self.in_li or self.formatter.in_p:
            self._close_item(result)

        h = word.strip()
        level = 1
        while h[level:level+1] == '=':
            level = level+1
        depth = min(5,level)

        title_text = h[level:-level].strip()
        # we wikify the title so that things like links show up in the heading
        title_text = wikiutil.stripOuterParagraph(wikiutil.wikifyString(
                        title_text, self.request, self.formatter.page))

        self.titles.setdefault(title_text, 0)
        self.titles[title_text] += 1

        unique_id = ''
        if self.titles[title_text] > 1:
            unique_id = '-%d' % self.titles[title_text]

        self.force_print_p = True
        result.append(self.formatter.heading(
            depth, title_text, icons=icons,
            id=("head-" + hashlib.new('sha1', title_text.encode('utf-8')).hexdigest() +
                unique_id
               ).decode('utf-8')))

        return ''.join(result)

    def definition(self, type, key, value):
        d = []
        if value:
            typeKey = ' '.join((type, key))
        else:
            typeKey, value = type, key
        
        d.extend([self.formatter.definition_term(True), 
                  typeKey,
                  self.formatter.definition_term(False),
                  self.formatter.definition_desc(True),
                  value,
                  self.formatter.definition_desc(False)])

        return ''.join(d)

    def get_page_lines(self): 
        """
        get text and replace TABs
        """
        rawtext = self.raw.expandtabs()
        self.lines = self.EOL_RE.split(rawtext)
        return self.lines

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
        #result.append("<!-- close item end -->\n")o
