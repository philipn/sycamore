# -*- coding: utf-8 -*-

# Imports
from Sycamore import wikiutil
from Sycamore import config
from Sycamore import farm

from Sycamore.Page import Page

KEEP_TIME = 60*60*2 # every two hours

def get_recent_wikis(request):
    if config.memcache:
        recent_wikis = request.mc.get('recentwikis', wiki_global=True)
        if recent_wikis is not None:
            return recent_wikis
    
    request.cursor.execute("""SELECT wikis.name, min(editTime)
                              FROM allPages, wikis
                              WHERE editTime > 0 and
                                    allPages.wiki_id=wikis.id
                              GROUP BY wikis.name
                              ORDER BY min
                              DESC LIMIT 100""")
    return request.cursor.fetchall()

def set_recent_wikis_cache(request, recent_wikis):
    if config.memcache:
        request.mc.add('recentwikis', recent_wikis, time=KEEP_TIME,
                       wiki_global=True)

def get_recently_edited(request):
    if config.memcache:
        recently_edited = request.mc.get('recentlyeditedwikis',
                                         wiki_global=True)
        if recently_edited is not None:
            return recently_edited
    
    request.cursor.execute("""SELECT wikis.name FROM
                                wikis,
                                (SELECT wiki_id,
                                        max(curPages.editTime) as latest FROM
                                 wikis, curPages
                                 GROUP BY wiki_id
                                 ORDER BY latest DESC
                                 LIMIT 100)
                                as wikisLatest
                              WHERE wikis.id=WikisLatest.wiki_id
                              ORDER BY wikisLatest.latest DESC""")
    return [x[0] for x in request.cursor.fetchall()]

def set_recently_edited_cache(request, recently_edited):
    if config.memcache:
        request.mc.add('recentlyeditedwikis', recently_edited, time=KEEP_TIME,
                       wiki_global=True)

def execute(macro, args, formatter=None):
    if not formatter:
        formatter = macro.formatter
    request = macro.request

    text = []
    text.append('<div style="float: left; width: 40%;">')
    text.append(formatter.heading(2, "Recently created wikis"))
    text.append(formatter.bullet_list(1))

    recent_wikis = get_recent_wikis(request)
    
    for wiki_name, editTime in recent_wikis:
        link = farm.link_to_wiki(wiki_name, formatter)
        text.append('%s%s%s' %
                    (formatter.listitem(1), link, formatter.listitem(0)))
    text.append(formatter.bullet_list(0))
    text.append('</div>')

    set_recent_wikis_cache(request, recent_wikis)

    text.append('<div style="float: right; width: 40%;">')
    text.append(formatter.heading(2, "Recently edited wikis"))
    text.append(formatter.bullet_list(1))

    recently_edited = get_recently_edited(request)
    
    for wiki_name in recently_edited:
        link = farm.link_to_wiki(wiki_name, formatter)
        text.append('%s%s%s' %
                    (formatter.listitem(1), link, formatter.listitem(0)))
    text.append(formatter.bullet_list(0))
    text.append('</div>')

    set_recently_edited_cache(request, recently_edited)

    output_html = formatter.rawHTML(''.join(text))
    return output_html
