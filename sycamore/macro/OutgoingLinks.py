# -*- coding: iso-8859-1 -*-

from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page

def execute(macro, args):

    body = ''
    numdict = {}
    for pagename in wikiutil.getPageList(config.text_dir):
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
    if config.relative_dir:
        add_on = '/'
    else:
        add_on = ''
    for k in dictkeys:
        body += "<h3>" + str(k) + "</h3>"
        if k is 0:
            for item in (numdict[k]):	
                if (Page(item).get_raw_body()[0:9] == "#redirect") or (item.endswith('/MoinEditorBackup')):
                    continue
                body += '<a style="padding: 2px;" href=/' + config.relative_dir + add_on + wikiutil.quoteWikiname(item) + ">" + item + "</a>" + " "
        else:
            for item in (numdict[k]):
                body += '<a style="padding: 2px;" href=/' + config.relative_dir + add_on + wikiutil.quoteWikiname(item) + ">" + item + "</a>" + " "


    return macro.formatter.rawHTML(body)
