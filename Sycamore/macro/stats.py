import time, re
from Sycamore import wikiutil, config, wikidb, user
from Sycamore.Page import Page
from cStringIO import StringIO

def execute(macro, args, formatter=None):
    if not formatter: formatter = macro.formatter
    request = macro.request

    if args:
       # personalized stats
       htmltext = []
       theuser = user.User(macro.request, name=args.lower())
       wiki_info = theuser.getWikiInfo()
       if not wiki_info.first_edit_date:
           first_edit_date = "<em>unknown</em>"
       else:
           first_edit_date = request.user.getFormattedDateTime(wiki_info.first_edit_date)
       created_count = wiki_info.created_count
       edit_count = wiki_info.edit_count
       file_count = wiki_info.file_count
       last_page_edited = wiki_info.last_page_edited
       last_edit_date = wiki_info.last_edit_date
       if not last_edit_date:
           last_edit_date = "<em>unknown</em>"
       else:
           last_edit_date = request.user.getFormattedDateTime(last_edit_date)

       if last_page_edited:
            htmltext.append('<p><h2>%s\'s Statistics</h2></p><table width=100%% border=0><tr><td><b>Edits&nbsp;&nbsp;</b></td><td><b>Pages Created&nbsp;&nbsp;</b></td><td><b>Files Contributed&nbsp;&nbsp;</b></td><td><b>First Edit Date&nbsp;&nbsp;</b></td><td><b>Last Edit&nbsp;&nbsp;</b></td><td><b>Last Page Edited&nbsp;&nbsp;</b></td></tr>' % args)
            htmltext.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr></table>' % (edit_count,created_count,file_count,first_edit_date,last_edit_date,Page(last_page_edited, request).link_to()))
       elif edit_count or wiki_info.first_edit_date:
            htmltext.append('<p><h2>%s\'s Statistics</h2></p><table width=100%% border=0><tr><td><b>Edits&nbsp;&nbsp;</b></td><td><b>Pages Created&nbsp;&nbsp;</b></td><td><b>Files Contributed&nbsp;&nbsp;</b></td><td><b>First Edit Date&nbsp;&nbsp;</b></td><td><b>Last Edit&nbsp;&nbsp;</b></td><td><b>Last Page Edited&nbsp;&nbsp;</b></td></tr>' % args)
            htmltext.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>&nbsp;</td></tr></table>' % (edit_count,created_count,file_count,first_edit_date,last_edit_date))
       else:
            htmltext.append('<p>' + macro.formatter.highlight(1) + 'The user "%s" has not edited this wiki.' % args + macro.formatter.highlight(0) + '</p>')

    else:
       htmltext = []
       sort_by = 'edit_count'
       if macro.request.form.has_key('sort_by'):
         sort_by = macro.request.form['sort_by'][0]
         # this is to prevent SQL exploits
         if sort_by not in ['edit_count', 'created_count', 'first_edit_date', 'file_count', 'last_edit_date']: sort_by = 'edit_count'
       list = []
       cursor = macro.request.cursor
       if sort_by == 'first_edit_date':
         cursor.execute("SELECT users.propercased_name, userWikiInfo.first_edit_date, userWikiInfo.created_count, userWikiInfo.edit_count, userWikiInfo.file_count, userWikiInfo.last_page_edited, userWikiInfo.last_edit_date, userWikiInfo.first_edit_date IS NULL AS join_isnull from userWikiInfo, users where users.name !='' and userWikiInfo.edit_count > 0 and users.name=userWikiInfo.user_name and userWikiInfo.wiki_id=%%(wiki_id)s order by join_isnull ASC, %s desc" % sort_by, {'wiki_id':macro.request.config.wiki_id})
       elif sort_by == 'last_edit_date':
         cursor.execute("SELECT users.propercased_name, userWikiInfo.first_edit_date, userWikiInfo.created_count, userWikiInfo.edit_count, userWikiInfo.file_count, userWikiInfo.last_page_edited, userWikiInfo.last_edit_date, userWikiInfo.last_edit_date IS NULL AS edit_isnull from users, userWikiInfo where users.name !='' and userWikiInfo.edit_count > 0 and users.name=userWikiInfo.user_name and userWikiInfo.wiki_id=%%(wiki_id)s order by edit_isnull ASC, %s desc" % sort_by, {'wiki_id':macro.request.config.wiki_id})
       else:
         cursor.execute("SELECT users.propercased_name, userWikiInfo.first_edit_date, userWikiInfo.created_count, userWikiInfo.edit_count, userWikiInfo.file_count, userWikiInfo.last_page_edited, userWikiInfo.last_edit_date from users, userWikiInfo where users.name !='' and userWikiInfo.edit_count > 0 and users.name=userWikiInfo.user_name and userWikiInfo.wiki_id=%%(wiki_id)s order by %s desc" % sort_by, {'wiki_id':macro.request.config.wiki_id})

       user_stats = cursor.fetchall()
       page = Page("User Statistics", request)

       htmltext.append('<p><h2>User Statistics</h2></p><table width=100%% border=0><tr><td><b>User</b></td><td><b>%s&nbsp;&nbsp;</b></td><td><b>%s&nbsp;&nbsp;</b></td><td><b>%s&nbsp;&nbsp;</b></td><td><b>%s&nbsp;&nbsp;</b></td><td><b>%s&nbsp;&nbsp;</b></td><td><b>Last Page Edited&nbsp;&nbsp;</b></td></tr>' % (page.link_to(know_status=True, know_status_exists=True, querystr="sort_by=edit_count", text="Edits"), page.link_to(know_status=True, know_status_exists=True, querystr="sort_by=created_count", text="Pages Created"), page.link_to(know_status=True, know_status_exists=True, querystr="sort_by=file_count", text="Files Contributed"), page.link_to(know_status=True, know_status_exists=True, querystr="sort_by=first_edit_date", text="First Edit Date"), page.link_to(know_status=True, know_status_exists=True, querystr="sort_by=last_edit_date", text="Last Edit")))
       toggle = -1
       for result in user_stats:
          toggle = toggle*(-1)
          name = result[0]
          first_edit_date = result[1]
          # older system sometimes didn't log this/hard to tell
          if not first_edit_date: first_edit_date = '<em>unknown</em>' 
          else: first_edit_date = request.user.getFormattedDateTime(first_edit_date)
          created_count = result[2]
          edit_count = result[3]
          file_count = result[4]
          last_page_edited = result[5]
          last_edit_date = result[6]
          if not last_edit_date: last_edit_date = '<em>unknown</em>' 
          else: last_edit_date = request.user.getFormattedDateTime(last_edit_date)

      # we don't user User objects here because there's a hell of a lot of users, potentally
          if toggle < 0: 
             if last_page_edited:
               htmltext.append('<tr bgcolor="#E5E5E5"><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (Page(config.user_page_prefix + name, request).link_to(know_status=True, know_status_exists=True, text=name),edit_count,created_count,file_count,first_edit_date,last_edit_date,Page(last_page_edited, request).link_to()))
             else:
               htmltext.append('<tr bgcolor="#E5E5E5"><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>&nbsp;</td></tr>' % (Page(config.user_page_prefix + name, request).link_to(know_status=True, know_status_exists=True, text=name),edit_count,created_count,file_count,first_edit_date,last_edit_date))
          else:
                if last_page_edited:
                        htmltext.append('<tr bgcolor="#E0FFFF"><td>%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (Page(config.user_page_prefix + name, request).link_to(know_status=True, know_status_exists=True, text=name),edit_count,created_count,file_count,first_edit_date,last_edit_date,Page(last_page_edited, request).link_to()))
                else:
                        htmltext.append('<tr bgcolor="#E0FFFF"><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>&nbsp;</td></tr>' % (Page(config.user_page_prefix + name, request).link_to(know_status=True, know_status_exists=True, text=name),edit_count,created_count,file_count,first_edit_date,last_edit_date))

       htmltext.append('</table>') 

    
    return macro.formatter.rawHTML(u''.join(htmltext))

def compare_edit(x,y):
    if int(x.getAttribute("edit_count")) == int(y.getAttribute("edit_count")):
       return 0
    elif int(x.getAttribute("edit_count")) < int(y.getAttribute("edit_count")):
       return 1
    else:
        return -1
