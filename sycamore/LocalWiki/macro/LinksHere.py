# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

Dependencies = ["time"] # can't really be cached right now

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    page = macro.formatter.page
    links_here = page.getPageLinksTo(macro.request)
    text = ''
    if links_here:
      text += formatter.bullet_list(1)
      for link in links_here:
        text += formatter.listitem(1) + formatter.pagelink(link) + formatter.listitem(0)
      text += formatter.bullet_list(0)
    
    return text
