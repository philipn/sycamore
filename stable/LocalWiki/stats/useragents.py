# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - User-Agent Statistics

    This macro creates a pie chart of the type of user agents
    accessing the wiki.

    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

_debug = 0

from LocalWiki import config, wikiutil, caching
from LocalWiki.logfile import eventlog
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
        'url': page.url(request, "action=chart&amp;type=useragents"),
    }
    data.update(config.chart_options)
    result.append('<img src="%(url)s" border="0" width="%(width)d" height="%(height)d">' % data)

    return ''.join(result)


def draw(pagename, request):
    import shutil, cStringIO, operator
    from LocalWiki import config
    from LocalWiki.stats.chart import Chart, ChartData, Color

    _ = request.getText

    style = Chart.GDC_3DPIE

    # get data
    colors = ['red', 'mediumblue', 'yellow', 'deeppink', 'aquamarine', 'purple', 'beige',
              'blue', 'forestgreen', 'orange', 'cyan', 'fuchsia', 'lime']
    colors = ([Color(c) for c in colors])

    # get results from cache
    cache = caching.CacheEntry('charts', 'useragents')
    if cache.exists():
        try:
            cache_date, data = eval(cache.content())
        except:
            data = {}
            cache_date = 0
    else:
        data = {}
        cache_date = 0

    logfile = eventlog.EventLog()
    logfile.set_filter(['VIEWPAGE', 'SAVEPAGE'])
    new_date = logfile.date()
    for event in logfile.reverse():
        if event[0] <= cache_date: break
        ua = event[2].get('HTTP_USER_AGENT')
        if ua:
            pos = ua.find(" (compatible; ")
            if pos >= 0: ua = ua[pos:].split(';')[1].strip()
            else: ua = ua.split()[0]
            #ua = ua.replace(';', '\n')
            data[ua] = data.get(ua, 0) + 1

    # write results to cache
    cache.update("(%r, %r)" % (new_date, data))
            
    data = [(cnt, ua) for ua, cnt in data.items()]
    data.sort()
    data.reverse()
    maxdata = len(colors) - 1
    if len(data) > maxdata:
        others = [x[0] for x in data[maxdata:]]
        data = data[:maxdata] + [(reduce(operator.add, others, 0), _('Others'))]

    # shift front to end if others is very small
    if data[-1][0] * 10 < data[0][0]:
        data = data[1:] + data[0:1]

    labels = [x[1] for x in data]
    data = [x[0] for x in data]

    # give us a chance to develop this
    if _debug:
        return "<p>data = %s</p>" % \
            '<br>'.join(map(wikiutil.escape, map(repr, [labels, data])))

    # create image
    image = cStringIO.StringIO()
    c = Chart()
    c.addData(data)

    title = ''
    if config.sitename: title = "%s: " % config.sitename
    title = title + _('Distribution of User-Agent Types')
    c.option(
        pie_color = colors,
        label_font = Chart.GDC_SMALL,
        label_line = 1,
        label_dist = 20,
        threed_depth = 20,
        threed_angle = 225,
        percent_labels = Chart.GDCPIE_PCT_RIGHT,
        title_font = c.GDC_GIANT,
        title = title)
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

