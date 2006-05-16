# -*- coding: iso-8859-1 -*-
"""
    Sycamore - Include macro

    This macro includes the formatted content of the given page(s).

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @copyright: 2000-2001 by Richard Jones <richard@bizarsoftware.com.au>
    @license: GNU GPL, see COPYING for details.
"""

import re, cStringIO
from Sycamore import config, wikiutil, caching
from Sycamore.Page import Page

_sysmsg = '<p><strong class="%s">%s</strong></p>'
_arg_heading = r'((?P<heading>,)\s*(|(?P<hquote>[\'"])(?P<htext>.+?)(?P=hquote))){0,1}'
_arg_showtitle = r'(,\s*(?P<showtitle>title)){0,1}'
_arg_level = r',\s*(?P<level>\d+)'
_arg_from = r'(,\s*from=(?P<fquote>[\'"])(?P<from>.+?)(?P=fquote))?'
_arg_to = r'(,\s*to=(?P<tquote>[\'"])(?P<to>.+?)(?P=tquote))?'
_arg_sort = r'(,\s*sort=(?P<sort>(ascending|descending)))?'
_arg_items = r'(,\s*items=(?P<items>\d+))?'
_arg_skipitems = r'(,\s*skipitems=(?P<skipitems>\d+))?'
_arg_titlesonly = r'(,\s*(?P<titlesonly>titlesonly))?'
_args_re_pattern = r'^(?P<name>[^,]+)(%s%s(%s)?%s%s%s%s%s%s)?$' % (
    _arg_heading, _arg_showtitle, _arg_level, _arg_from, _arg_to, _arg_sort, _arg_items,
    _arg_skipitems, _arg_titlesonly)

TITLERE = re.compile("^(?P<heading>\s*(?P<hmarker>=+)\s.*\s(?P=hmarker))$",
                     re.M)

def extract_titles(body):
    titles = []
    for title, _ in TITLERE.findall(body):
        h = title.strip()
        level = 1
        while h[level:level+1] == '=': level = level+1
        depth = min(5,level)
        title_text = h[level:-level].strip()
        titles.append((title_text, level))
    return titles

Dependencies = []

def execute(macro, args, formatter=None):
    if not formatter:
      if hasattr(macro.parser, 'formatter'): formatter = macro.parser.formatter
      else: formatter = macro.formatter
    _ = macro.request.getText
    args_re=re.compile(_args_re_pattern)

    # return immediately if getting links for the current page
    #if macro.request.mode_getpagelinks:
    #    return ''

    request = macro.request

    # parse and check arguments
    args = args_re.match(args)
    if not args:
        return (_sysmsg % ('error', _('Invalid include arguments "%s"!')) % (args,))

    # prepare including page
    result = []
    this_page = formatter.page
    showtitle = args.group('showtitle')

    if not hasattr(this_page, '_macroInclude_pagelist'):
        this_page._macroInclude_pagelist = {}

    inc_name = wikiutil.AbsPageName(this_page.page_name, args.group('name'))
    inc_page = Page(inc_name, macro.request)
    if not macro.request.user.may.read(inc_page):
        return ''
    if this_page.page_name.lower() == inc_name.lower():
        result.append('<p><strong class="error">Recursive include of "%s" forbidden</strong></p>' % (inc_name,))
	return ''.join(result)

    # check for "from" and "to" arguments (allowing partial includes)
    body = inc_page.get_raw_body() + '\n'
    from_pos = 0
    to_pos = -1
    from_re = args.group('from')
    if from_re:
        try:
            from_match = re.compile(from_re, re.M).search(body)
        except re.error, e:
            ##result.append("*** fe=%s ***" % e)
            from_match = re.compile(re.escape(from_re), re.M).search(body)
        if from_match:
            from_pos = from_match.end()
        else:
            result.append(_sysmsg % ('warning', 'Include: ' + _('Nothing found for "%s"!')) % from_re)
    to_re = args.group('to')
    if to_re:
        try:
            to_match = re.compile(to_re, re.M).search(body, from_pos)
        except re.error:
            to_match = re.compile(re.escape(to_re), re.M).search(body, from_pos)
        if to_match:
            to_pos = to_match.start()
        else:
            result.append(_sysmsg % ('warning', 'Include: ' + _('Nothing found for "%s"!')) % to_re)

    if from_pos or to_pos != -1:
        inc_page.set_raw_body(body[from_pos:to_pos])

    edit_icon = ''
    
    # do headings
    level = None
    if config.relative_dir: add_on = '/'
    else: add_on = ''

    heading = args.group('htext') or inc_page.page_name
    level = 1
    if args.group('level'):
        level = int(args.group('level'))
    if args.group('htext') or showtitle: 
      result.append(formatter.heading(level, heading, action_link="edit", link_to_heading=True, pagename=inc_page.proper_name(), backto=this_page.page_name))

    if this_page._macroInclude_pagelist.has_key(inc_name):
      if this_page._macroInclude_pagelist[inc_name] > caching.MAX_DEPENDENCY_DEPTH:
	 return '<em>Maximum include depth exceeded.</em>'
         
    # set or increment include marker
    this_page._macroInclude_pagelist[inc_name] = \
        this_page._macroInclude_pagelist.get(inc_name, 0) + 1

    # format the included page
    pi_format = config.default_markup or "wiki" 
    Parser = wikiutil.importPlugin("parser", pi_format, "Parser")
    raw_text = inc_page.get_raw_body()
    formatter.setPage(inc_page)
    parser = Parser(raw_text, formatter.request)
    # note that our page now depends on the content of the included page
    if formatter.name == 'text_python':
      # this means we're in the caching formatter
      caching.dependency(this_page.page_name, inc_name.lower(), macro.request)
    # output formatted
    buffer = cStringIO.StringIO()
    formatter.request.redirect(buffer)
    parser.format(formatter)

    formatter.setPage(this_page)
    formatter.request.redirect()
    text = buffer.getvalue()
    buffer.close()
    result.append(text)
              
    # decrement or remove include marker
    if this_page._macroInclude_pagelist[inc_name] > 1:
        this_page._macroInclude_pagelist[inc_name] -= 1
    else:
        del this_page._macroInclude_pagelist[inc_name]

    # return include text
    return ''.join(result)
