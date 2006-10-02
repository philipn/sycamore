"""
    RSS Handling!!

    If you do changes, please check if it still validates after your changes:

    http://feedvalidator.org/

    @license: GNU GPL, see COPYING for details.
"""
from Sycamore import config, wikiutil, wikidb, user
from Sycamore.Page import Page
from Sycamore.widget.comments import Comment
from Sycamore.wikiaction import do_diff
import xml.dom.minidom
import urllib
#from Sycamore.wikixml.util import RssGenerator


def execute(pagename, request):
    """ Send recent changes as an RSS document
    """
    
    if pagename.lower() == 'recent changes':
      rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Recent Changes - %s</title><link>http://%s%s/Recent_Changes</link><description>Recent Changes on %s.</description><language>en-us</language>
</channel> 
</rss>
      """ % (config.sitename, config.domain, request.getScriptname(), config.sitename)
      # get normal recent changes 
      changes = wikidb.getRecentChanges(request, total_changes_limit=100)
    elif pagename.lower() == 'bookmarks':
      if request.form.has_key('user'):
        username = urllib.unquote_plus(request.form['user'][0])
        rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Bookmarks - %s @ %s</title><link>%s</link><description>Bookmarks for user %s on %s.</description><language>en-us</language>
</channel> 
</rss>""" %  (username, config.sitename, Page(username, request).link_to(know_status=True, know_status_exists=True), username, config.sitename)
        
	userid = user.User(request, name=username).id
        changes = wikidb.getRecentChanges(request, per_page_limit=1, userFavoritesFor=userid)
      else:
        return ''
      
    else:
      rss_init_text = """<?xml version="1.0" ?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Recent Changes for "%s" - %s</title><link>http://%s%s/%s</link><description>Recent Changes of the page "%s" on %s.</description><language>en-us</language>
</channel> 
</rss>
      """ % (pagename, config.sitename, config.domain, request.getScriptname(), wikiutil.quoteWikiname(pagename), pagename, config.sitename)
      # get page-specific recent changes 
      changes = wikidb.getRecentChanges(request, total_changes_limit=100, page=pagename.lower())

    rss_dom = xml.dom.minidom.parseString(rss_init_text)
    channel = rss_dom.getElementsByTagName("channel")[0]
    for line in changes:
      if line.ed_time == None: line.ed_time = 0
      line.comment = Comment(request, line.comment, line.action, line.pagename).render()
      item = rss_dom.createElement("item")
      item_guid = rss_dom.createElement("guid")
      item_guid.appendChild(rss_dom.createTextNode("%s, %s" % (line.ed_time, wikiutil.quoteWikiname(line.pagename))))
      item_description = rss_dom.createElement("description")
      if line.action in ['SAVE', 'SAVENEW', 'RENAME', 'COMMENT_MACRO', 'SAVE/REVERT', 'DELETE']:
        page = Page(line.pagename, request)
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
      item_link.appendChild(rss_dom.createTextNode("http://%s%s/%s" % (config.domain, request.getScriptname(), wikiutil.quoteWikiname(line.pagename))))
      item.appendChild(item_link)
      item_date = rss_dom.createElement("dc:date")
      item_date.appendChild(rss_dom.createTextNode(request.user.getFormattedDateTime(line.ed_time, global_time=True)))
      item.appendChild(item_date)
      creator = rss_dom.createElement("dc:creator")
      creator.appendChild(rss_dom.createTextNode(user.User(request, line.userid).propercased_name))
      item.appendChild(creator)
      item.appendChild(item_description)
      channel.appendChild(item)

    the_xml = rss_dom.toxml()
    request.http_headers()
    request.write(the_xml)
