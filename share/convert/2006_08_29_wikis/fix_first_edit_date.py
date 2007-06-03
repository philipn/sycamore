import sys, cStringIO, os
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])

from Sycamore import wikiutil, config, request, caching, wikidb, maintenance, buildDB, wikiacl
from Sycamore.Page import Page
from Sycamore.buildDB import FlatPage

req = request.RequestDummy()

userlist = []
req.cursor.execute("SELECT id, name from users")
result = req.cursor.fetchall()
for entry in result:
  userlist.append(entry) 

for wikiname in wikiutil.getWikiList(req):
   req.switch_wiki(wikiname)
   print wikiname
   for thisuser_id, thisuser_name in userlist:
      print "  ", thisuser_name.encode(config.charset)
      req.cursor.execute("SELECT usersEdits.editTime from (SELECT allPages.editTime from allPages where userEdited=%(thisuser)s and wiki_id=%(thiswiki)s) as usersEdits order by usersEdits.editTime asc limit 1;", {'thisuser': thisuser_id, 'thiswiki': req.config.wiki_id})
      result = req.cursor.fetchone()
      if result:
         edit_time = result[0]
      else:
         edit_time = None
      
      if edit_time:
          req.cursor.execute("SELECT user_name from userWikiInfo where user_name=%(thisuser_name)s and wiki_id=%(thiswiki)s", {'thisuser_name':thisuser_name, 'thiswiki': req.config.wiki_id})
          has_user_info_on_wiki = req.cursor.fetchone()
          if has_user_info_on_wiki:
              req.cursor.execute("UPDATE userWikiInfo set first_edit_date=%(edit_time)s where user_name=%(thisuser_name)s and wiki_id=%(thiswiki)s", {'thisuser_name':thisuser_name, 'thiswiki': req.config.wiki_id, 'edit_time': edit_time}, isWrite=True)
          else:
              req.cursor.execute("INSERT into userWikiInfo (user_name, wiki_id, first_edit_date) values (%(thisuser_name)s, %(thiswiki)s, %(edit_time)s)", {'thisuser_name':thisuser_name, 'thiswiki': req.config.wiki_id, 'edit_time': edit_time}, isWrite=True)
       
req.db_disconnect()
