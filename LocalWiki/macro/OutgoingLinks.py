# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

def execute(macro, args):

  title = ''
  numdict = {}
  for pagename in wikiutil.getPageList(config.text_dir):
    if not wikiutil.isSystemPage(macro.request, pagename):
        page = Page(pagename)
        links = page.getPageLinks(macro.request, False)
	numlinks = 0
        for link in links:
		numlinks += 1
	if numdict.has_key(numlinks):
		numdict[numlinks].append(pagename)
	else:
		numdict[numlinks] = [pagename]
  dictkeys = numdict.keys()
  dictkeys.sort()
  for k in dictkeys:
	print "<h3>" + str(k) + "</h3>"
	if k is 0:
		for item in (numdict[k]):	
			if Page(item).get_raw_body()[0:9] == "#redirect": continue
			else:
			    print "<a href=/" + config.relative_dir + "/" + wikiutil.quoteWikiname(item) + ">" + item + "</a>" + "&nbsp;&nbsp;"
	else:
		for item in (numdict[k]):
		  print "<a href=/" + config.relative_dir + "/" + wikiutil.quoteWikiname(item) + ">" + item + "</a>" + "&nbsp;&nbsp;"

  """
  for k, v in (numdict.iteritems()):
	print "<h3>" + str(k) + "</h3>"
	if k is 0:
		for item in v:	
			if Page(item).get_raw_body()[0:9] == "#redirect": continue
			else:
			    print "<a href=/" + config.relative_dir + "/" + wikiutil.quoteWikiname(item) + ">" + item + "</a>" + "&nbsp;&nbsp;"
	else:
		for item in v:
		  print "<a href=/" + config.relative_dir + "/" + wikiutil.quoteWikiname(item) + ">" + item + "</a>" + "&nbsp;&nbsp;"
  """

  return macro.formatter.rawHTML(title)
  #return macro.formatter.rawHTML('<b>This feature is temporarily disabled until we improve its performance.</b>')
