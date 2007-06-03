# -*- coding: iso-8859-1 -*-

from Sycamore import wikiutil, wikiform, config, farm
from Sycamore.Page import Page

KEEP_TIME = 60*60*2 # every two hours

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    request = macro.request

    if config.memcache:
       recent_wikis = request.mc.get('recentwikis', wiki_global=True)
       if recent_wikis is not None:
          return recent_wikis

    text = []
    
    text.append(formatter.bullet_list(1))
    request.cursor.execute("SELECT wikis.name, min(editTime) from allPages, wikis where editTime > 0 and allPages.wiki_id=wikis.id group by wikis.name order by min desc limit 100")
    for item in request.cursor.fetchall():
       wiki_name, editTime = item
       link = farm.link_to_wiki(wiki_name, formatter)
       text.append('%s%s%s' % (formatter.listitem(1), link, formatter.listitem(0)))
    text.append(formatter.bullet_list(0))

    recent_wikis = formatter.rawHTML(''.join(text))

    if config.memcache:
        request.mc.add('recentwikis', recent_wikis, time=KEEP_TIME, wiki_global=True)
    return recent_wikis
