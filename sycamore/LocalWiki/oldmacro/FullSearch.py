# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - FullSearch Macro

    [[FullSearch]]
        displays a search dialog, as it always did

    [[FullSearch()]]
        does the same as clicking on the page title, only that
        the result is embedded into the page (note the "()" after
        the macro name, which is an empty argument list)

    [[FullSearch('HelpContents')]]
        embeds a search result into a page, as if you entered
        "HelpContents" into the search dialog

    @copyright: 2000-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import re, urllib
from LocalWiki import wikiutil

_args_re_pattern = r'((?P<hquote>[\'"])(?P<htext>.+?)(?P=hquote))|'

Dependencies = ["pages"]

def execute(macro, text, args_re=re.compile(_args_re_pattern)):
    _ = macro.request.getText

    # if no args given, invoke "classic" behavior
    if text is None:
        return macro._m_search("fullsearch")

    # parse and check arguments
    args = args_re.match(text)
    if not args:
        return '<p><strong class="error">Invalid FullSearch arguments "%s"!</strong></p>' % (text,)

    needle = args.group('htext')
    literal = 0
    if not needle:
        # empty args means to duplicate the "title click" search (backlinks to page),
        # especially useful on "Category" type pages
        needle = macro.formatter.page.page_name
        literal = 1

    # do the search
    pagecount, hits = wikiutil.searchPages(needle, literal=literal, context=0)

    # generate the result
    result = []
    result.append(macro.formatter.number_list(1))
    for (count, pagename, dummy) in hits:
        if not macro.request.user.may.read(pagename):
            continue
        result.append(macro.formatter.listitem(1))
        result.append(wikiutil.link_tag(macro.request,
            '%s?action=highlight&value=%s' % (
                wikiutil.quoteWikiname(pagename),
                urllib.quote_plus(needle)),
            pagename))
        result.append(' . . . . ' + `count` + ' ' + [
            _('match'),
            _('matches')][count != 1])
        result.append(macro.formatter.listitem(0))
    result.append(macro.formatter.number_list(0))

    return ''.join(result)

