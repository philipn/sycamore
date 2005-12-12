# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - "links" action

    Generate a link database like MeatBall:LinkDatabase.

    @copyright: 2001 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

from LocalWiki import config, wikiutil
from LocalWiki.util import LocalWikiNoFooter


def execute(pagename, request):
    _ = request.getText
    form = request.form

    # get the MIME type
    if form.has_key('mimetype'):
        mimetype = form['mimetype'][0]
    else:
        mimetype = "text/html"

    request.http_headers(["Content-Type: " + mimetype])

    if mimetype == "text/html":
        wikiutil.send_title(request, _('Full Link List for "%s"') % config.sitename)
        request.write('<pre>')

    pages = wikiutil.getPageDict()

    pagelist = pages.keys()
    pagelist.sort()
    pagelist = filter(request.user.may.read, pagelist)

    for name in pagelist:
        if mimetype == "text/html":
            request.write(pages[name].link_to(request))
        else:
            _emit(request, name)
        for link in pages[name].getPageLinks(request):
            if mimetype == "text/html":
                if pages.has_key(link):
                    request.write(pages[link].link_to(request))
                else:
                    _emit(request, link)
            else:
                _emit(request, link)
        request.write('\n')

    if mimetype == "text/html":
        request.write('</pre>')
        wikiutil.send_footer(request, pagename, editable=0, showactions=0, form=form)
    else:
        raise LocalWikiNoFooter

def _emit(request, pagename):
    """ Send pagename, encode it if it contains spaces
    """
    if pagename.find(' ') >= 0:
        request.write(wikiutil.quoteWikiname(pagename))
    else:
        request.write(pagename)

