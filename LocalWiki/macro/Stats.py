# -*- coding: iso-8859-1 -*-
import time, re
from LocalWiki import wikiutil, wikiform, config
from LocalWiki.Page import Page
import xml.dom.minidom
from cStringIO import StringIO


def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def execute(macro, args):
    if config.relative_dir:  add_on = '/'
    else:  add_on = ''

    if args:
       dom = xml.dom.minidom.parse(config.app_dir + "/userstats.xml")
       users = dom.getElementsByTagName("user")
       root = dom.documentElement
       htmltext = []
       for user in users:
          if user.getAttribute("name") == args:
	     htmltext.append('<p><h2>%s\'s Statistics</h2></p><table width=100%% border=0><tr><td><b>Pages Edited&nbsp;&nbsp;</b></td><td><b>Pages Created&nbsp;&nbsp;</b></td><td><b>Images Contributed&nbsp;&nbsp;</b></td><td><b>Date Joined&nbsp;&nbsp;</b></td><td><b>Last Edit&nbsp;&nbsp;</b></td><td><b>Last Page Edited&nbsp;&nbsp;</b></td></tr>' % args)
             htmltext.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="/%s%s%s">%s</a></td></tr></table>' % (user.getAttribute("edit_count"),user.getAttribute("created_count"),user.getAttribute("file_count"),user.getAttribute("join_date"),user.getAttribute("last_edit"),config.relative_dir,add_on,wikiutil.quoteWikiname(user.getAttribute("last_page_edited")),user.getAttribute("last_page_edited")))	     
    else:
       htmltext = []
       list = []
       dom = xml.dom.minidom.parse(config.app_dir + "/userstats.xml")
       users = dom.getElementsByTagName("user")
       htmltext.append('<p><h2>User Statistics</h2></p><table width=100%% border=0><tr><td><b>User</b></td><td><b>Pages Edited&nbsp;&nbsp;</b></td><td><b>Pages Created&nbsp;&nbsp;</b></td><td><b>Images Contributed&nbsp;&nbsp;</b></td><td><b>Date Joined&nbsp;&nbsp;</b></td><td><b>Last Edit&nbsp;&nbsp;</b></td><td><b>Last Page Edited&nbsp;&nbsp;</b></td></tr>')
       for user in users:
          list.append(user) 
       list.sort(compare_edit)
       toggle = -1
       for user in list:
          toggle = toggle*(-1)
	  if toggle < 0: 
             htmltext.append('<tr bgcolor="#E5E5E5"><td><a href="/%s%s%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="/%s%s%s">%s</a></td></tr>' % (config.relative_dir,add_on,wikiutil.quoteWikiname(user.getAttribute("name")),user.getAttribute("name"),user.getAttribute("edit_count"),user.getAttribute("created_count"),user.getAttribute("file_count"),user.getAttribute("join_date"),user.getAttribute("last_edit"),config.relative_dir,add_on,wikiutil.quoteWikiname(user.getAttribute("last_page_edited")),user.getAttribute("last_page_edited")))
	  else:
             htmltext.append('<tr bgcolor="#E0FFFF"><td><a href="/%s%s%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="/%s%s%s">%s</a></td></tr>' % (config.relative_dir,add_on,wikiutil.quoteWikiname(user.getAttribute("name")),user.getAttribute("name"),user.getAttribute("edit_count"),user.getAttribute("created_count"),user.getAttribute("file_count"),user.getAttribute("join_date"),user.getAttribute("last_edit"),config.relative_dir,add_on,wikiutil.quoteWikiname(user.getAttribute("last_page_edited")),user.getAttribute("last_page_edited")))
        
       htmltext.append('</table>') 

    return macro.formatter.rawHTML(''.join(htmltext))

def compare_edit(x,y):
    if int(x.getAttribute("edit_count")) == int(y.getAttribute("edit_count")):
       return 0
    elif int(x.getAttribute("edit_count")) < int(y.getAttribute("edit_count")):
       return 1
    else:
	return -1
