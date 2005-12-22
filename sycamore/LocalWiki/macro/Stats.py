# -*- coding: iso-8859-1 -*-
import time, re
from LocalWiki import wikiutil, wikiform, config, wikidb
from LocalWiki.Page import Page
from cStringIO import StringIO

import xml.dom.minidom


def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    request = macro.request
    if config.relative_dir:  add_on = '/'
    else:  add_on = ''

    if args:
       # personalized stats
       htmltext = []
       db = wikidb.connect()
       cursor = db.cursor()
       cursor.execute("SELECT join_date, created_count, edit_count, file_count, last_page_edited, last_edit_date from users where name=%s", (args))
       result = cursor.fetchone()
       cursor.close()
       db.close()
       if result: 
         join_date = result[0]
         if not join_date: join_date = "<em>unknown</em>"
         else: join_date = request.user.getFormattedDateTime(join_date)
         created_count = result[1]
         edit_count = result[2]
         file_count = result[3]
         last_page_edited = result[4]
         last_edit_date = result[5]
         if not last_edit_date: last_edit_date = "<em>unknown</em>"
         else: last_edit_date = request.user.getFormattedDateTime(last_edit_date)

         htmltext.append('<p><h2>%s\'s Statistics</h2></p><table width=100%% border=0><tr><td><b>Edits&nbsp;&nbsp;</b></td><td><b>Pages Created&nbsp;&nbsp;</b></td><td><b>Images Contributed&nbsp;&nbsp;</b></td><td><b>Date Joined&nbsp;&nbsp;</b></td><td><b>Last Edit&nbsp;&nbsp;</b></td><td><b>Last Page Edited&nbsp;&nbsp;</b></td></tr>' % args)
	 if result[4]:
           htmltext.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="/%s%s%s">%s</a></td></tr></table>' % (edit_count,created_count,file_count,join_date,last_edit_date,config.relative_dir,add_on,wikiutil.quoteWikiname(last_page_edited),last_page_edited))	     
	 else:
	   htmltext.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>&nbsp;</td></tr></table>' % (edit_count,created_count,file_count,join_date,last_edit_date))

       else: htmltext.append('<p>' + macro.formatter.highlight(1) + 'No such user "%s"' % args + macro.formatter.highlight(0) + '</p>')

    else:
       htmltext = []
       sort_by = 'edit_count'
       if macro.request.form.has_key('sort_by'):
	 sort_by = macro.request.form['sort_by'][0]
	 # this is to prevent SQL exploits
	 if sort_by not in ['edit_count', 'created_count', 'join_date', 'file_count', 'last_edit_date']: sort_by = 'edit_count'
       list = []
       db = wikidb.connect()
       cursor = db.cursor()
       cursor.execute("SELECT name, join_date, created_count, edit_count, file_count, last_page_edited, last_edit_date from users where name!='' order by %s desc" % sort_by, (args))
       user_stats = cursor.fetchall()
       cursor.close()
       db.close()

       htmltext.append('<p><h2>User Statistics</h2></p><table width=100%% border=0><tr><td><b>User</b></td><td><b><a href="/%s%sUser_Statistics?sort_by=edit_count">Edits</a>&nbsp;&nbsp;</b></td><td><b><a href="/%s%sUser_Statistics?sort_by=created_count">Pages Created</a>&nbsp;&nbsp;</b></td><td><b><a href="/%s%sUser_Statistics?sort_by=file_count">Images Contributed</a>&nbsp;&nbsp;</b></td><td><b><a href="/%s%sUser_Statistics?sort_by=join_date">Date Joined</a>&nbsp;&nbsp;</b></td><td><b><a href="/%s%sUser_Statistics?sort_by=last_edit_date">Last Edit</a>&nbsp;&nbsp;</b></td><td><b>Last Page Edited&nbsp;&nbsp;</b></td></tr>' %(config.relative_dir, add_on, config.relative_dir, add_on, config.relative_dir, add_on, config.relative_dir, add_on, config.relative_dir, add_on))
       toggle = -1
       for result in user_stats:
          toggle = toggle*(-1)
	  name = result[0]
	  join_date = result[1]
	  # older system sometimes didn't log this/hard to tell
	  if not join_date: join_date = '<em>unknown</em>' 
	  else: join_date = request.user.getFormattedDateTime(join_date)
	  created_count = result[2]
	  edit_count = result[3]
	  file_count = result[4]
	  last_page_edited = result[5]
	  last_edit_date = result[6]
	  if not last_edit_date: last_edit_date = '<em>unknown</em>' 
	  else: last_edit_date = request.user.getFormattedDateTime(last_edit_date)

	  if toggle < 0: 
	     if last_page_edited:
               htmltext.append('<tr bgcolor="#E5E5E5"><td><a href="/%s%s%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="/%s%s%s">%s</a></td></tr>' % (config.relative_dir,add_on,wikiutil.quoteWikiname(name),name,edit_count,created_count,file_count,join_date,last_edit_date,config.relative_dir,add_on,wikiutil.quoteWikiname(last_page_edited),last_page_edited))
	     else:
	       htmltext.append('<tr bgcolor="#E5E5E5"><td><a href="/%s%s%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>&nbsp;</td></tr>' % (config.relative_dir,add_on,wikiutil.quoteWikiname(name),name,edit_count,created_count,file_count,join_date,last_edit_date))
	  else:
	  	if last_page_edited:
             		htmltext.append('<tr bgcolor="#E0FFFF"><td><a href="/%s%s%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td><a href="/%s%s%s">%s</a></td></tr>' % (config.relative_dir,add_on,wikiutil.quoteWikiname(name),name,edit_count,created_count,file_count,join_date,last_edit_date,config.relative_dir,add_on,wikiutil.quoteWikiname(last_page_edited),last_page_edited))
	  	else:
	  		htmltext.append('<tr bgcolor="#E0FFFF"><td><a href="/%s%s%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>&nbsp;</td></tr>' % (config.relative_dir,add_on,wikiutil.quoteWikiname(name),name,edit_count,created_count,file_count,join_date,last_edit_date))

       htmltext.append('</table>') 

    return macro.formatter.rawHTML(''.join(htmltext))

def compare_edit(x,y):
    if int(x.getAttribute("edit_count")) == int(y.getAttribute("edit_count")):
       return 0
    elif int(x.getAttribute("edit_count")) < int(y.getAttribute("edit_count")):
       return 1
    else:
	return -1
