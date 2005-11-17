# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Formatter Base Class

    @copyright: 2000-2002 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import sys, cgi
from xml.dom import minidom
from LocalWiki.formatter.base import FormatterBase

#############################################################################
### Formatter Base
#############################################################################

#def print_dom(element, indent=''):
#    print indent + element.tagName
#    for child in element.get

class Formatter(FormatterBase):
    """ This defines the output interface used all over the rest of the code.

        Note that no other means should be used to generate _content_ output,
        while navigational elements (HTML page header/footer) and the like
        can be printed directly without violating output abstraction.
    """

    hardspace = ' '

    format_tags = ['b', 'em', 'highlight', 'sup', 'sub', 'code', 'u']

    unbreakables = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'p', 'ol', 'ul', 'li', 'pre', 'a']

    need_p = format_tags[:]
    need_p.extend(['ol', 'a'])

    no_p_after = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ol', 'ul', 'pre']

    close_on_open = {
        'h1' : ['p'],
        'li' : ['li'],
        'p' : ['p'],
        #'pre' : ['p'],
        }

    for i in xrange(2,7):
        close_on_open['h%i' % i] = close_on_open['h1']

    close_on_close = {
        'table' : ['td', 'tr'],
        'td' : ['tr'],
        'tr' : ['td'],
        'ol' : ['li'],
        'ul' : ['li'],
        }

    def __init__(self, request, **kw):
        self.request = request
        self._ = request.getText

        self._store_pagelinks = kw.get('store_pagelinks', 0)
        self.pagelinks = []
        self.in_p = 0
        self.in_pre = 0
        self.document = minidom.Document()
        self.document.documentElement = self.document.createElement('xml')
        self.position = self.document.documentElement
        self.tag_stack = [('xml', {})]
        
    def setPage(self, page):
        self.page = page

    def _open_tag(self, tag, **attrs):
        """ low level function: opens tag right now """
        self.tag_stack.append((tag, attrs))
        node = self.document.createElement(tag)
        for name, value in attrs.items():
            if value:
                node.setAttribute(name, str(value))
        self.position.appendChild(node)
        self.position = node
        return ''

    def _close_tag(self, tag):
        """ low level function: closes tag right now
            must be the last opend tag!!!
        """
        if self.tag_stack[-1][0] != tag:
            raise ValueError, "<%s> expected <%s> given" % (self.tag_stack[-1][0], tag)
        self.position = self.position.parentNode
        return self.tag_stack.pop()

    def _add_tag(self, tag, **attrs):
        """ low level function: insert self closing tag right now """
        node = self.document.createElement(tag)
        for name, value in attrs.items():
            if value:
                node.setAttribute(name, str(value))
        self.position.appendChild(node)                        
        return ''

    def text(self, text):
        self._check_p()
        if text.strip():
            self.position.appendChild(self.document.createTextNode(text))
        return ''

    def _set_tag(self, tag, on, **attrs):
        if on:
            close_on_open = self.close_on_open.get(tag, [])
            tags_to_reopen = []
            while 1:
                last_tag = self.tag_stack[-1][0]
                if last_tag in close_on_open:
                    self._close_tag(last_tag)
                elif last_tag in self.format_tags:
                    tags_to_reopen.append(self._close_tag(last_tag))
                else:
                    break
            # XXX check if enclosing tag is ok

            if tag in self.need_p:
                self._check_p()

            self._open_tag(tag, **attrs)
            tags_to_reopen.reverse()
            for tag_name, args in tags_to_reopen:
                self._open_tag(tag_name, **args)
        else:
            tags_to_reopen = []
            close_on_close = self.close_on_close.get(tag, [])
            # walk up
            while self.tag_stack:
                # collect format tags
                last_tag = self.tag_stack[-1][0]
                if last_tag == tag:
                    break
                elif last_tag in close_on_close:
                    self._close_tag(last_tag)
                elif last_tag in self.format_tags:
                    tags_to_reopen.append(self._close_tag(last_tag))
                else:
                    raise ValueError, "<%s> expected <%s> given" % (last_tag, tag)
            self._close_tag(tag)
            tags_to_reopen.reverse()
            for tag_name, args in tags_to_reopen:
                self._open_tag(tag_name, args)
        return ''

    def _check_p(self):
        for tag in self.tag_stack:
            if tag[0] in self.no_p_after: return
        self._open_tag('p')

    def sysmsg(self, text, **kw):
        """ Emit a system message (embed it into the page).

            Normally used to indicate disabled options, or invalid
            markup.
        """
        return text

    def startDocument(self, pagename):
        return ""

    def endDocument(self):
        #return self.document.documentElement.toxml()
        return self.document.documentElement.toprettyxml("  ")

    def rawHTML(self, markup):
        """ This allows emitting pre-formatted HTML markup, and should be
            used wisely (i.e. very seldom).

            Using this event while generating content results in unwanted
            effects, like loss of markup or insertion of CDATA sections
            when output goes to XML formats.
        """
        ## XXX
        self.text(markup)
        return ''

    def pagelink(self, pagename, text=None, **kw):
        apply(FormatterBase.pagelink, (self, pagename, text), kw)
        node = self.document.createElement('pagelink')
        node.setAttribute('pagename', pagename)
        
        if text:
            node.appendChild(self.document.createTextNode(text))
        self.position.appendChild(node)                                
        return ''
    
    def macro(self, macro_obj, name, args):
        # call the macro
        return self._add_tag('macro', name=name, args=(args or ''))

    def processor(self, processor_name, lines):
        """ processor_name MUST be valid!
            writes out the result insted of returning it!
        """
        node = self.document.createElement('processor')
        node.setAttribute('name', processor_name)
        node.appendChild(self.document.createTextNode('\n'.join(lines)))
        return (self._set_tag('processor', True, name=processor_name) +
                self.text('\n'.join(lines)) +
                self._set_tag('processor', False))

    def dynamic_content(self, parser, callback, arg_list = [], arg_dict = {},
                        returns_content = 1):
        content = parser[callback](*arg_list, **arg_dict)
        if returns_content:
            return content
        else:
            return ''

    def url(self, url, text=None, css=None, **kw):
        node = self.document.createElement('a')
        node.setAttribute('url', url)
        #XXX other parameters
        if text:
            node.appendChild(self.document.createTextNode(text))
        self.position.appendChild(node)
        return ''

    def rule(self, size=0):
        return self._add_tag('hr', {'size': str(size)})

    def strong(self, on):
        return self._set_tag('b', on)

    def emphasis(self, on):
        return self._set_tag('em', on)

    #def highlight(self, on):
    #    self._set_tag('highlight', on)
    #    return ''

    def number_list(self, on, type=None, start=None):
        return self._set_tag('ol', on, type=type, start=start)

    def bullet_list(self, on):
        return self._set_tag('ul', on)

    def listitem(self, on, **kw):
        return self._set_tag('li', on)

    def sup(self, on):
        return self._set_tag('sup', on)

    def sub(self, on):
        return self._set_tag('sub', on)

    def code(self, on):
        return self._set_tag('code', on)

    def preformatted(self, on):
        self.in_pre = on != 0
        return self._set_tag('pre', on)

    def paragraph(self, on):
        self.in_p = on != 0
        return self._set_tag('p', on)

    def linebreak(self, preformatted=1):
        if self.tag_stack[-1][0] == 'pre':
            return self.text('\n')
        else:
            return self._add_tag('br')
                                  
    def heading(self, depth, title, **kw):
        if title == None: title = ''
        if kw.has_key('on'):
            return self._set_tag('h%d' %depth, kw['on'])
        
        return (self._set_tag('h%d' % depth, True, **kw) +
                self.text(title) +
                self._set_tag('h%d' % depth, False))                                  

    def table(self, on, attrs={}):
        return self._set_tag('table', on, attrs)
        
    def table_row(self, on, attrs={}):
        return self._set_tag('tr', on, attrs)


    def table_cell(self, on, attrs={}):
        return self._set_tag('td', on, attrs)

    def anchordef(self, name):
        return self._add_tag('anchor', name=name)

    def anchorlink(self, name, text): # XXX TODO add missing id keyword parameter
        return self.url("#" + name, text)

    def underline(self, on):
        return self._set_tag('u', on)

    def definition_list(self, on):
        return self._set_tag('dl', on)

    def definition_term(self, on, compact=0):
        # XXXX may be not correct
        # self._langAttr() missing
        if compact and on:
            return self._set_tag('dt compact', on)
        else:
            return self._set_tag('dt', on)            

    def definition_desc(self, on):
        # self._langAttr() missing
        self._set_tag('dd', on)

    def image(self, **kw):
        """ Take HTML <IMG> tag attributes in `attr`.

            Attribute names have to be lowercase!
        """
        return self._add_tag('img', **kw)

