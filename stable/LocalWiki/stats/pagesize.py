# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Pagesize Statistics

    This macro creates a bar graph of page size classes.

    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

_debug = 0

from LocalWiki import config, wikiutil
from LocalWiki.Page import Page
from LocalWiki.util import LocalWikiNoFooter


def linkto(pagename, request, params=''):
    _ = request.getText

    if not config.chart_options:
        return request.formatter.sysmsg(_('Charts are not available!'))

    if _debug:
        return draw(pagename, request)

    page = Page(pagename)
    result = []
    data = {
        'url': page.url(request, "action=chart&amp;type=pagesize"),
    }
    data.update(config.chart_options)
    result.append('<img src="%(url)s" border="0" width="%(width)d" height="%(height)d">' % data)

    return ''.join(result)


def _slice(data, lo, hi):
    data = data[:]
    if lo: data[:lo] = [None] * lo
    if hi < len(data): data[hi:] =  [None] * (len(data)-hi)
    return data


def draw(pagename, request):
    import bisect, shutil, cStringIO
    from LocalWiki import config
    from LocalWiki.stats.chart import Chart, ChartData, Color

    _ = request.getText
    style = Chart.GDC_3DBAR

    # get data
    pages = wikiutil.getPageDict(config.text_dir)
    sizes = [(p.size(), name) for name, p in pages.items()]
    sizes.sort()

    upper_bound = sizes[-1][0]
    bounds = [s*128 for s in range(1, 9)]
    if upper_bound >= 1024:
        bounds.extend([s*1024 for s in range(2, 9)])
    if upper_bound >= 8192:
        bounds.extend([s*8192 for s in range(2, 9)])
    if upper_bound >= 65536:
        bounds.extend([s*65536 for s in range(2, 9)])
        
    data = [None] * len(bounds)
    for size, name in sizes:
        idx = bisect.bisect(bounds, size)
        ##idx = int((size / upper_bound) * classes)
        data[idx] = (data[idx] or 0) + 1

    labels = ["%d" %b for b in bounds]

    # give us a chance to develop this
    if _debug:
        return "<p>data = %s</p>" % \
            '<br>'.join(map(wikiutil.escape, map(repr, [labels, data])))

    # create image
    image = cStringIO.StringIO()
    c = Chart()
    ##c.addData(ChartData(data, 'magenta'))
    c.addData(ChartData(_slice(data, 0, 7), 'blue'))
    if upper_bound >= 1024:
        c.addData(ChartData(_slice(data, 7, 14), 'green'))
    if upper_bound >= 8192:
        c.addData(ChartData(_slice(data, 14, 21), 'red'))
    if upper_bound >= 65536:
        c.addData(ChartData(_slice(data, 21, 28), 'magenta'))
    title = ''
    if config.sitename: title = "%s: " % config.sitename
    title = title + _('Page Size Distribution')
    c.option(
        annotation = (bisect.bisect(bounds, upper_bound), Color('black'), "%d %s" % sizes[-1]),
        title = title,
        xtitle = _('page size upper bound [bytes]'),
        ytitle = _('# of pages of this size'),
        title_font = c.GDC_GIANT,
        threed_depth = 2.0,
        requested_yinterval = 1.0,
        stack_type = c.GDC_STACK_LAYER
    )
    c.draw(style,
        (config.chart_options['width'], config.chart_options['height']),
        image, labels)

    # send HTTP headers
    headers = [
        "Content-Type: image/gif",
        "Content-Length: %d" % len(image.getvalue()),
    ]
    request.http_headers(headers)

    # copy the image
    image.reset()
    shutil.copyfileobj(image, request, 8192)
    raise LocalWikiNoFooter

