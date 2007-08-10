# -*- coding: utf-8 -*-

# Imports
from Sycamore import wikiutil
from Sycamore import config
from Sycamore import farm

from Sycamore.Page import Page

KEEP_TIME = 60*60*2 # every two hours

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    request = macro.request

    if config.memcache:
        recent_wikis = request.mc.get('recentwikis', wiki_global=True)
        if recent_wikis is not None:
            return recent_wikis

    text = []


    # only show 100 wikis, determine where to start

    start = 0

    if request.form.has_key('next'):
      try:
        start = int(request.form['next'][0]) + 100
      except(ValueError, TypeError):
        return('')    # evil user manipulated the url

    if request.form.has_key('prev'):
      try:
        start = int(request.form['prev'][0]) - 100
      except(ValueError, TypeError):
        return('')    # evil user manipulated the url
            
      if start < 0:
        start = 0     # mysql wouldn't like LIMIT -100, 100

    if start > 0:
      text.append('<a href=?prev=%s>Previous Page</a><br>' % start)

    request.cursor.execute("""SELECT COUNT(name) as wikiCount FROM wikis""")
    totalNumRows = request.cursor.fetchone()


    if start + 100 < totalNumRows[0]:
      text.append('<a href=?next=%s>Next page</a>' % start)
    else:
      start = totalNumRows[0] - 100   # user messed with the url
                                      # show the last page
                                    
    
    text.append(formatter.bullet_list(1))
    request.cursor.execute("""SELECT wikis.name, min(editTime) as min
                              FROM allPages, wikis
                              WHERE editTime > 0 and
                                    allPages.wiki_id=wikis.id
                              GROUP BY wikis.name
                              ORDER BY min
                              DESC LIMIT %s, 100""" % start)

    limitedRows = request.cursor.fetchall()

    for item in limitedRows:
        wiki_name, editTime = item
        link = farm.link_to_wiki(wiki_name, formatter)
        text.append('%s%s%s' %
                    (formatter.listitem(1), link, formatter.listitem(0)))
        
    text.append(formatter.bullet_list(0))

    recent_wikis = formatter.rawHTML(''.join(text))

    if config.memcache:
        request.mc.add('recentwikis', recent_wikis, time=KEEP_TIME,
                       wiki_global=True)
    return recent_wikis
