# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - LikePages action

    This action generates a list of pages that either start or end
    with the same word as the current pagename. If only one matching
    page is found, that page is displayed directly.

    @copyright: (c) 2001 by Richard Jones <richard@bizarsoftware.com.au>
    @copyright: (c) 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

import re
from LocalWiki import config, wikiutil
from LocalWiki.Page import Page


def execute(pagename, request):
    _ = request.getText
    start, end, matches = findMatches(pagename, request)

    # error?
    if isinstance(matches, type('')):
        Page(pagename, request).send_page(msg=matches)
        return

    # no matches :(
    if not matches:
        Page(pagename, request).send_page(
            msg = _('No pages match "%s"!') % (pagename,))
        return

    # one match - display it
    if len(matches) == 1:
        Page(matches.keys()[0], request).send_page(
            msg =  _('Exactly one matching page for "%s" found!') % (pagename,))
        return

    # more than one match, list 'em
    request.http_headers()
    wikiutil.send_title(request, _('Multiple matches for "%s...%s"') % (start, end),
        pagename=pagename)
        
    request.write('<div id="content">\n') # start content div
    showMatches(pagename, request, start, end, matches)
    request.write('</div>\n') # end content div

    wikiutil.send_footer(request, pagename)


def findMatches(pagename, request,
        s_re=re.compile('([%s][%s]+)' % (config.upperletters, config.lowerletters)),
        e_re=re.compile('([%s][%s]+)$' % (config.upperletters, config.lowerletters))):
    import difflib
    _ = request.getText

    # get page lists
    pagelist = request.getPageList()
    lowerpages = [p.lower() for p in pagelist]
    similar = difflib.get_close_matches(pagename.lower(), lowerpages, 10) 

    # figure the start and end words
    s_match = s_re.match(pagename)
    e_match = e_re.search(pagename)
    if not (s_match and e_match or similar):
        return None, None, _('You cannot use LikePages on an extended pagename!')

    start = None
    end = None
    matches = {}
    if s_match and e_match:
        # extract the words
        start = s_match.group(1)
        end = e_match.group(1)
        subpage = pagename + '/'

        # find any matching pages
        for anypage in pagelist:
            # skip current page
            if anypage == pagename:
                continue
            if anypage.startswith(subpage):
                matches[anypage] = 4
            else:
                if anypage.startswith(start):
                    matches[anypage] = 1
                if anypage.endswith(end):
                    matches[anypage] = matches.get(anypage, 0) + 2

    if similar:
        pagemap = {}
        for anypage in pagelist:
            pagemap[anypage.lower()] = anypage

        for anypage in similar:
            if pagemap[anypage] == pagename:
                continue
            matches[pagemap[anypage]] = 8

    for pagename in matches.keys():
        page = Page(pagename, request)
        if not request.user.may.read(page):
            del matches[pagename]

    return start, end, matches


def showMatches(pagename, request, start, end, matches):
    keys = matches.keys()
    keys.sort()
    _showMatchGroup(request, matches, keys, 8, pagename)
    _showMatchGroup(request, matches, keys, 4, "%s/..." % pagename)
    _showMatchGroup(request, matches, keys, 3, "%s...%s" % (start, end))
    _showMatchGroup(request, matches, keys, 1, "%s..." % (start,))
    _showMatchGroup(request, matches, keys, 2, "...%s" % (end,))


def _showMatchGroup(request, matches, keys, match, title):
    _ = request.getText
    matchcount = matches.values().count(match)

    if matchcount:
        request.write('<p><strong>' + _('%(matchcount)d %(matches)s for "%(title)s"') % {
            'matchcount': matchcount,
            'matches': ' ' + (_('match'), _('matches'))[matchcount != 1],
            'title': wikiutil.escape(title)} + '</strong></p>')
        request.write("<ul>")
        for key in keys:
            if matches[key] == match:
                page = Page(key, request)
                request.write('<li><a href="%s/%s">%s</a>' % (
                    request.getScriptname(),
                    wikiutil.quoteWikiname(page.page_name),
                    page.page_name))
        request.write("</ul>")

