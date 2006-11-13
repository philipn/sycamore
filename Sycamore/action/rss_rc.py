"""
    RSS Handling!!

    If you do changes, please check if it still validates after your changes:

    http://feedvalidator.org/

    @license: GNU GPL, see COPYING for details.
"""
from Sycamore import config, wikiutil, wikidb, user, farm
from Sycamore.Page import Page
from Sycamore.widget.comments import Comment
from Sycamore.wikiaction import do_diff
import xml.dom.minidom
import urllib
#from Sycamore.wikixml.util import RssGenerator

rc_pagename = 'Recent Changes'
interwiki_rc_pagename = 'Interwiki Recent Changes'

def execute(pagename, request):
    """ Send recent changes as an RSS document
    """
    from Sycamore.formatter.text_html import Formatter
    formatter = Formatter(request)
    page = Page(pagename, request) 
    wiki_global = False
    bookmarks = False
    theuser = None
    if request.form.has_key('user'):
        # bookmarks
        username = urllib.unquote_plus(request.form['user'][0])
        if request.form.has_key('global') and request.form['global']:
            wiki_global = True
        theuser = user.User(request, name=username)
    if request.form.has_key('bookmarks') and request.form['bookmarks']:
        bookmarks = True

    if bookmarks and theuser:
        if not wiki_global:
            rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Bookmarks - %s @ %s</title><link>%s</link><description>Bookmarks for user %s on %s.</description><language>en-us</language>
</channel> 
</rss>""" %  (username, request.config.sitename, user.getUserLink(request, theuser), username, request.config.sitename)
        else:
            rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Interwiki Bookmarks - %s</title><link>%s</link><description>Interwiki bookmarks for user %s</description><language>en-us</language>
</channel> 
</rss>""" %  (username, user.getUserLink(request, theuser), username)

        userid = theuser.id
        changes = wikidb.getRecentChanges(request, per_page_limit=1, userFavoritesFor=userid, wiki_global=wiki_global)
    elif pagename.lower() == rc_pagename.lower():
      rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Recent Changes - %s</title><link>%s</link><description>Recent Changes on %s.</description><language>en-us</language>
</channel> 
</rss>
      """ % (request.config.sitename, page.link_to(), request.config.sitename)
      # get normal recent changes 
      changes = wikidb.getRecentChanges(request, total_changes_limit=100)
    elif pagename.lower() == interwiki_rc_pagename.lower() and theuser:
      wiki_global = True
      rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Interwiki Recent Changes for %s</title><link>%s</link><description>Interwiki Recent Changes for %s.</description><language>en-us</language>
</channel> 
</rss>
      """ % (theuser.propercased_name, page.link_to(), theuser.propercased_name)
      # get interwiki normal recent changes 
      changes = wikidb.getRecentChanges(request, total_changes_limit=100, wiki_global=True, on_wikis=theuser.getWatchedWikis())

    else:
      rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Recent Changes for "%s" - %s</title><link>%s</link><description>Recent Changes of the page "%s" on %s.</description><language>en-us</language>
</channel> 
</rss>
      """ % (pagename, request.config.sitename, page.link_to(), pagename, request.config.sitename)
      # get page-specific recent changes 
      changes = wikidb.getRecentChanges(request, page=pagename.lower())

    rss_dom = xml.dom.minidom.parseString(rss_init_text)
    channel = rss_dom.getElementsByTagName("channel")[0]
    original_wiki = request.config.wiki_name
    for line in changes:
      if wiki_global:
        request.switch_wiki(line.wiki_name)
      if line.ed_time == None: line.ed_time = 0
      page = Page(line.pagename, request)
      line.comment = Comment(request, line.comment, line.action, page=page).render()
      item = rss_dom.createElement("item")
      item_guid = rss_dom.createElement("guid")
      item_guid.appendChild(rss_dom.createTextNode("%s, %s" % (line.ed_time, wikiutil.quoteWikiname(line.pagename))))
      item_description = rss_dom.createElement("description")
      if line.action in ['SAVE', 'SAVENEW', 'RENAME', 'COMMENT_MACRO', 'SAVE/REVERT', 'DELETE']:
        if not request.user.may.read(page):
            continue
        version2 = Page(line.pagename, request, prev_date=line.ed_time).get_version()
        version1 = version2 - 1
        description = "%s %s" % (line.comment, do_diff(line.pagename, request, in_wiki_interface=False, text_mode=True, version1=version1, version2=version2))
      else:
        description = line.comment

      item_description.appendChild(rss_dom.createTextNode(description))
      item_title = rss_dom.createElement("title")
      item_title.appendChild(rss_dom.createTextNode(line.pagename))
      item.appendChild(item_title)
      item_link = rss_dom.createElement("link")
      if wiki_global:
        item_link.appendChild(rss_dom.createTextNode(farm.link_to_page(line.wiki_name, line.pagename, formatter)))
      else:
        item_link.appendChild(rss_dom.createTextNode("http://%s%s/%s" % (request.config.domain, request.getScriptname(), wikiutil.quoteWikiname(line.pagename))))
      item.appendChild(item_link)
      item_date = rss_dom.createElement("dc:date")
      item_date.appendChild(rss_dom.createTextNode(request.user.getFormattedDateTime(line.ed_time, global_time=True)))
      item.appendChild(item_date)
      creator = rss_dom.createElement("dc:creator")
      creator.appendChild(rss_dom.createTextNode(user.User(request, line.userid).propercased_name))
      item.appendChild(creator)
      item.appendChild(item_description)
      channel.appendChild(item)

    if wiki_global:
        request.switch_wiki(original_wiki)
    the_xml = rss_dom.toxml()
    request.http_headers()
    request.write(the_xml)
