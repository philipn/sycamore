# -*- coding: utf-8 -*-
"""
    Sycamore - Include macro

    This macro includes the formatted content of the given page(s).

    @copyright: 2007 by Philip Neustrom <philipn@gmail.com>
    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @copyright: 2000-2001 by Richard Jones <richard@bizarsoftware.com.au>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re
import cStringIO

from Sycamore import config
from Sycamore import wikiutil
from Sycamore import caching

from Sycamore.Page import Page

_sysmsg = '<p><strong class="%s">%s</strong></p>'

INCLUDE_MACRO = re.compile(r'^(\s*(\[\[include((\(.*\))|())\]\])\s*)+$')

def line_has_just_macro(macro, args, formatter):
    line = macro.parser.lines[macro.parser.lineno-1].lower().strip()
    if INCLUDE_MACRO.match(line):
        return True
    return False

def extract_titles(body):
    titles = []
    for title, _ in TITLERE.findall(body):
        h = title.strip()
        level = 1
        while h[level:level+1] == '=':
            level = level+1
        depth = min(5,level)
        title_text = h[level:-level].strip()
        titles.append((title_text, level))
    return titles

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter:
        if hasattr(macro.parser, 'formatter'):
            formatter = macro.parser.formatter
        else:
            formatter = macro.formatter
    _ = macro.request.getText

    inline_edit_state = formatter.inline_edit
    formatter.inline_edit = False

    # included page will already have paragraphs. no need to print another.
    macro.parser.inhibit_p = 1 

    if line_has_just_macro(macro, args, formatter):
        macro.parser.inhibit_br = 2

    request = macro.request

    # parse and check arguments
    if not args:
        return (_sysmsg % ('error',
                           _('You did not give a pagename of a page to '
                             'include!')))
    # prepare including page
    result = []
    this_page = formatter.page

    # if we're in a paragraph, let's close it.
    if macro.formatter.in_p:
       result.append(macro.formatter.paragraph(0))

    if not hasattr(this_page, '_macroInclude_pagelist'):
        this_page._macroInclude_pagelist = {}

    re_args = re.match('('
        '('
            '(?P<name1>.+?)(\s*,\s*)((".*")|(left|right)|([0-9]{1,2}%)))|'
        '(?P<name2>.+))', args)
    if not re_args:
        return (_sysmsg % ('error', _('Invalid arguments to Include.')))

    have_more_args = re_args.group('name1')
    page_name = re_args.group('name1') or re_args.group('name2')

    if have_more_args:
        args = args[re_args.end('name1'):]
    else:
        args = ''
    re_args = re.search('"(?P<heading>.*)"', args)
    if re_args:
        heading = re_args.group('heading')
    else:
        heading = None

    if heading:
        before_heading = args[:re_args.start('heading')-1].strip()
        after_heading = args[re_args.end('heading')+1:].strip()
        args = before_heading + after_heading[1:]

    args_elements = args.split(',')
    align = None
    was_given_width = False
    width = '50%'
    for arg in args_elements:
        arg = arg.strip()
        if arg == 'left' or arg == 'right':
            align = arg
        elif arg.endswith('%'):
            try:
                arg = str(int(arg[:-1])) + '%'
            except:
                continue
            width = arg
	    was_given_width = True

    inc_name = wikiutil.AbsPageName(this_page.page_name, page_name)
    inc_page = Page(inc_name, macro.request)
    if not macro.request.user.may.read(inc_page):
        return ''
    if this_page.page_name.lower() == inc_name.lower():
        result.append('<p><strong class="error">'
                      'Recursive include of "%s" forbidden</strong></p>' %
                      inc_name)
	return ''.join(result)

    # check for "from" and "to" arguments (allowing partial includes)
    body = inc_page.get_raw_body(fresh=True) + '\n'
    edit_icon = ''
    
    # do headings
    level = 1
    if heading:
        result.append(formatter.heading(level, heading, action_link="edit",
                                        link_to_heading=True,
                                        pagename=inc_page.proper_name(),
                                        backto=this_page.page_name))

    if this_page._macroInclude_pagelist.has_key(inc_name):
        if (this_page._macroInclude_pagelist[inc_name] >
            caching.MAX_DEPENDENCY_DEPTH):
            return '<em>Maximum include depth exceeded.</em>'
         
    # set or increment include marker
    this_page._macroInclude_pagelist[inc_name] = \
        this_page._macroInclude_pagelist.get(inc_name, 0) + 1

    # format the included page
    pi_format = config.default_markup or "wiki" 
    Parser = wikiutil.importPlugin("parser", pi_format, "Parser")
    raw_text = inc_page.get_raw_body(fresh=True)
    formatter.setPage(inc_page)
    parser = Parser(raw_text, formatter.request)

    parser.print_first_p = 0 # don't print two <p>'s

    # note that our page now depends on the content of the included page
    if formatter.name == 'text_python':
        # this means we're in the caching formatter
        caching.dependency(this_page.page_name, inc_name.lower(), macro.request)
    # output formatted
    buffer = cStringIO.StringIO()
    formatter.request.redirect(buffer)
    parser.format(formatter, inline_edit_default_state=False)

    formatter.setPage(this_page)
    formatter.request.redirect()
    text = buffer.getvalue().decode('utf-8')
    buffer.close()
    result.append(text)
              
    # decrement or remove include marker
    if this_page._macroInclude_pagelist[inc_name] > 1:
        this_page._macroInclude_pagelist[inc_name] -= 1
    else:
        del this_page._macroInclude_pagelist[inc_name]


    attrs = ''
    if align:
    	attrs += (' style="width: %s; float: %s; clear: %s;" ' %
                  (width, align, align))
    elif was_given_width:
        attrs += ' style="width: %s;' % width
    attrs += ' class="includedPage"'
    include_page = '<div%s>%s</div>' % (attrs, ''.join(result))

    ## turn back on inline editing ability
    parser.formatter.inline_edit = inline_edit_state
    formatter.inline_edit = inline_edit_state

    # return include text
    return include_page
