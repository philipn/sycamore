# -*- coding: utf-8 -*-
"""
    Sycamore - Sycamore Wiki Markup Parser

    @copyright: 2000, 2001, 2002 by JÃ¼rgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, re
import string
from Sycamore import config, wikimacro, wikiutil, metadata
from Sycamore.Page import Page
from Sycamore.util import web
from Sycamore.parser.wiki_simple import Parser as SimpleParser

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
#(?P<definition>^(.*)%(def_op)s(.*)$)"""

    formatting_rules_dict = {
        'macronames': '|'.join(wikimacro.names),
        'def_op': DEFINITION_OPERATOR
        }
    formatting_rules_dict.update(SimpleParser.formatting_rules_dict)
    formatting_rules = ("(?:%s%s)%s%s" % (SimpleParser.formatting_a, formatting_a, SimpleParser.formatting_b, formatting_b)) % formatting_rules_dict

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
        rules = rules + r'|(?P<wikiname_bracket>\["[^\[\]"]+?"\])'
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


        for line in self.lines:
            self.lineno = self.lineno + 1
            self.table_rowstart = 1
            self.line_was_empty = self.line_is_empty
            self.line_is_empty = 0
            self.first_list_item = 0
            self.inhibit_p = 0
            if self.inhibit_br > 0: self.inhibit_br -= 1
            else: self.inhibit_br = 0

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
                elif self.print_br():
                    self.request.write('<br/>')
                    self.inhibit_br += 1 # to avoid printing two if they did [[br]]
                # start p on first line
                elif not self.inhibit_p and self.lineno == 1 and self.print_first_p:
                    self.request.write(self.formatter.paragraph(1))

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
            if not (self.inhibit_p or self.in_pre or self.in_table):
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
        if self.in_table: self.request.write(self.formatter.table(0))
        self.request.write(self._undent())

        # check for pending footnotes
        if getattr(self.request, 'footnotes', None):
          from Sycamore.macro.footnote import emit_footnotes
          emit_footnotes(self.request, self.formatter)


    def _tableZ_repl(self, word):
        """Handle table row end."""
        if self.in_table:
            return self.formatter.table_cell(0) + self.formatter.table_row(0)
        else:
            return word

    def _table_repl(self, word):
        """Handle table cell separator."""
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
            return word


    def _heading_repl(self, word):
        """Handle section headings."""
        import sha

        self.inhibit_p = 1
        self.inhibit_br += 2
        icons = ''

        h = word.strip()
        level = 1
        while h[level:level+1] == '=':
            level = level+1
        depth = min(5,level)

        title_text = h[level:-level].strip()
        self.titles.setdefault(title_text, 0)
        self.titles[title_text] += 1

        unique_id = ''
        if self.titles[title_text] > 1:
            unique_id = '-%d' % self.titles[title_text]

        return self.formatter.heading(depth, self.highlight_text(title_text), icons=icons, id=("head-"+sha.new(title_text.encode('utf-8')).hexdigest()+unique_id).decode('utf-8'))


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

    def _definition_repl(self, word):
        typeKey, value = word.split(':=', 1)
        if ' ' in typeKey:
            type, key = typeKey.split(' ', 1)
        else:
            type, key, value = typeKey, value, False

        if not self.formatter.isPreview():
            result = metadata.addKey(self.formatter.page.page_name, type, 
                                     key, value)

        return self.definition(type, key, value)

    def get_page_lines(self): 
        # get text and replace TABs
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
