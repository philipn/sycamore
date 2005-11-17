# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

def execute(macro, args):

  title = ''
  master = ''
  for pagename in wikiutil.getPageList(config.text_dir):
        page = Page(pagename)
        links = page.getPageLinks(macro.request)
	title = ''
        for link in links[:len(links)-1]:
		link = link.replace(' ', '_')
                title+= link + " "
	if len(links) > 0:
        	title += (links[len(links)-1]).replace(' ','_') + "\n"
	pagename = pagename.replace(' ', '_')
	master += pagename + " " + title

  f = open('/var/www/html/vismap/sourcefile','w')
  f.write(master)
  f.close()
  return macro.formatter.rawHTML(title)
