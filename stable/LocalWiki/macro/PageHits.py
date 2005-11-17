"""
    per page hit statistics

    @copyright: 2004 Thomas Waldmann
    @license: GNU GPL, see COPYING for details

"""

from LocalWiki import caching
from LocalWiki.Page import Page
from LocalWiki.logfile import eventlog

def execute(macro, args):
    key = 'pagehits'
    cache = caching.CacheEntry('charts', key)
    if cache.exists():
        try:
            cache_date, pagehits = eval(cache.content())
        except:
            cache_date, pagehits = 0, {}
    else:
        cache_date, pagehits = 0, {}

    event_log = eventlog.EventLog()
    event_log.set_filter(['VIEWPAGE'])
    new_date = event_log.date()
    
    for event in event_log.reverse():
        if event[0] <=  cache_date:
            break
        page = event[2].get('pagename','')
        if page:
            pagehits[page] = pagehits.get(page,0) + 1

    # save to cache
    cache.update("(%r, %r)" % (new_date, pagehits))
    
    # get hits and sort them
    hits = []
    for pagehit in pagehits.items():
        pagename = pagehit[0]
        if Page(pagename).exists() and macro.request.user.may.read(pagename):
            hits.append((pagehit[1],pagehit[0]))
    hits.sort()
    hits.reverse()

    # format list
    result = []
    result.append(macro.formatter.number_list(1))
    for hit, page in hits:
        result.extend([macro.formatter.listitem(1),
            macro.formatter.code(1),
            ("%6d" % hit).replace(" ", "&nbsp;"), " ",
            macro.formatter.code(0),
            macro.formatter.pagelink(page),
            macro.formatter.listitem(0),
        ])
    result.append(macro.formatter.number_list(0))

    return ''.join(result)

