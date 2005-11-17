# -*- coding: iso-8859-1 -*-
"""
    LocalWiki - Hitcount Statistics

    This macro creates a hitcount chart from the data in "event.log".

    @copyright: 2002-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

_debug = 0

from LocalWiki import config, caching
from LocalWiki.Page import Page
from LocalWiki.util import LocalWikiNoFooter, datetime
from LocalWiki.logfile import eventlog
from LocalWiki.formatter.text_html import Formatter

def linkto(pagename, request, params=''):
    _ = request.getText

    if not config.chart_options:
        request.formatter = Formatter(request)
        return request.formatter.sysmsg(_('Charts are not available!'))

    if _debug:
        return draw(pagename, request)

    page = Page(pagename)
    result = []
    if params:
        params = '&amp;' + params
    data = {
        'url': page.url(request, "action=chart&amp;type=hitcounts" + params),
    }
    data.update(config.chart_options)
    result.append('<img src="%(url)s" border="0" width="%(width)d" height="%(height)d">' % data)

    return ''.join(result)


def draw(pagename, request):
    import shutil, cStringIO
    from LocalWiki import config, wikiutil
    from LocalWiki.stats.chart import Chart, ChartData, Color

    _ = request.getText

    # check params
    filterpage = None
    if request and request.form and request.form.has_key('page'):
        filterpage = request.form['page'][0]


    # get results from cache
    if filterpage:
        key = 'hitcounts-' + wikiutil.quoteFilename(filterpage)
    else:
        key = 'hitcounts'
    
    cache = caching.CacheEntry('charts', key)
    if cache.exists():
        try:
            cache_date, cache_days, cache_views, cache_edits = eval(cache.content())
        except:
            cache_days, cache_views, cache_edits = [], [], []
            cache_date = 0
    else:
        cache_days, cache_views, cache_edits = [], [], []
        cache_date = 0

    logfile = eventlog.EventLog()
    logfile.set_filter(['VIEWPAGE', 'SAVEPAGE'])
    new_date = logfile.date()

    # prepare data
    days = []
    views = []
    edits = []
    ratchet_day = None
    ratchet_time = None
    for event in logfile.reverse():
        #print ">>>", wikiutil.escape(repr(event)), "<br>"

        if event[0] <=  cache_date:
            break
        
        if filterpage and event[2].get('pagename','') != filterpage:
            continue
        time_tuple = request.user.getTime(event[0])
        day = tuple(time_tuple[0:3])
        if day != ratchet_day:
            # new day
            while ratchet_time:
                ratchet_time -= 86400
                rday = tuple(request.user.getTime(ratchet_time)[0:3])
                if rday <= day: break
                days.append(request.user.getFormattedDate(ratchet_time))
                views.append(0)
                edits.append(0)
            days.append(request.user.getFormattedDate(event[0]))
            views.append(0)
            edits.append(0)
            ratchet_day = day
            ratchet_time = event[0]
        if event[1] == 'VIEWPAGE':
            views[-1] = views[-1] + 1
        elif event[1] == 'SAVEPAGE':
            edits[-1] = edits[-1] + 1

    # give us a chance to develop this
    if _debug:
        return "labels = %s<br>views = %s<br>edits = %s<br>" % \
            tuple(map(wikiutil.escape, map(repr, [days, views, edits])))

    days.reverse()
    views.reverse()
    edits.reverse()

    # merge the day on the end of the cache
    if cache_days and days and days[0] == cache_days[-1]:
        cache_edits[-1] += edits[0]
        cache_views[-1] += views[0]
        days, views, edits = days[1:], views[1:], edits[1:]

    cache_days.extend(days)
    cache_views.extend(views)
    cache_edits.extend(edits)

    days, views, edits = cache_days, cache_views, cache_edits

    # save to cache
    cache.update("(%r, %r, %r, %r)" % (new_date, days, views, edits))

    import math
    
    try:
        scalefactor = float(max(views))/max(edits)
    except ZeroDivisionError:
        scalefactor = 1.0
    else:
        scalefactor = int(10 ** math.floor(math.log10(scalefactor)))

    #scale edits up
    edits = map(lambda x: x*scalefactor, edits)

    # create image
    image = cStringIO.StringIO()
    c = Chart()
    c.addData(ChartData(views, color='green'))
    c.addData(ChartData(edits, color='red'))
    chart_title = ''
    if config.sitename: chart_title = "%s: " % config.sitename
    chart_title = chart_title + _('Page hits and edits')
    if filterpage: chart_title = _("%(chart_title)s for %(filterpage)s") % {
        'chart_title': chart_title, 'filterpage': filterpage}
    chart_title = "%s\n%sx%d" % (chart_title, _("green=view\nred=edit"), scalefactor)
    c.option(
        title = chart_title,
        xtitle = _('date') + ' (Server)',
        ytitle = _('# of hits'),
        title_font = c.GDC_GIANT,
        #thumblabel = 'THUMB', thumbnail = 1, thumbval = 10,
        #ytitle_color = Color('green'),
        #yaxis2 = 1,
        #ytitle2 = '# of edits',
        #ytitle2_color = Color('red'),
        #ylabel2_color = Color('black'),
        #interpolations = 0,
        threed_depth = 1.0,
        requested_yinterval = 1.0,
        stack_type = c.GDC_STACK_BESIDE
    )
    c.draw(c.GDC_LINE,
        (config.chart_options['width'], config.chart_options['height']),
        image, days)

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

