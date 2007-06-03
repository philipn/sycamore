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
      req.cursor.execute("SELECT count(name) from files where uploaded_by=%(thisuser)s and wiki_id=%(thiswiki)s", {'thisuser': thisuser_id, 'thiswiki': req.config.wiki_id})
      result = req.cursor.fetchone()
      if result:
         file_count = result[0]
      else:
         file_count = 0
      req.cursor.execute("SELECT count(name) from oldFiles where uploaded_by=%(thisuser)s and wiki_id=%(thiswiki)s", {'thisuser': thisuser_id, 'thiswiki': req.config.wiki_id})
      result = req.cursor.fetchone()
      if result:
         file_count += result[0]
      
      req.cursor.execute("SELECT user_name from userWikiInfo where user_name=%(thisuser_name)s and wiki_id=%(thiswiki)s", {'thisuser_name':thisuser_name, 'thiswiki': req.config.wiki_id})
      result = req.cursor.fetchone()
      if result:
          req.cursor.execute("UPDATE userWikiInfo set file_count=%(file_count)s where user_name=%(thisuser_name)s and wiki_id=%(thiswiki)s", {'thisuser_name':thisuser_name, 'thiswiki': req.config.wiki_id, 'file_count': file_count}, isWrite=True)
      else:
          req.cursor.execute("INSERT into userWikiInfo (user_name, wiki_id, file_count) values (%(thisuser_name)s, %(thiswiki)s, %(file_count)s)", {'thisuser_name':thisuser_name, 'thiswiki': req.config.wiki_id, 'file_count': file_count}, isWrite=True)
       
req.db_disconnect()
