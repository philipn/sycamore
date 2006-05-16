# -*- coding: iso-8859-1 -*-

from Sycamore import wikiutil, wikiform, config
from Sycamore.Page import Page

Dependencies = ["time"] # can't really be cached right now, maybe later (use memcache and might not matter)

def execute(macro, args, formatter=None):
    formatter = macro.formatter
    if not args:
      page = macro.formatter.page
    else:
      page = Page(args, macro.request)
    links_here = page.getPageLinksTo()
    pages_deco = [ (pagename.lower(), pagename) for pagename in links_here]
    pages_deco.sort()
    links_here = [ word for lower_word, word in pages_deco ]

    text = []
    if links_here:
      text.append(formatter.bullet_list(1))
      for link in links_here:
        text.append('%s%s%s' % (formatter.listitem(1), formatter.pagelink(link), formatter.listitem(0)))
      text.append(formatter.bullet_list(0))
    
    return ''.join(text)
