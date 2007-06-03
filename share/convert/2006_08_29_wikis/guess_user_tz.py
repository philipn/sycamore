import sys, cStringIO, os, shutil, re
__directory__ = os.path.dirname(__file__)
sys.path.extend([os.path.abspath(os.path.join(__directory__, '..', '..', '..'))])

from Sycamore import wikiutil, config, request, caching, wikidb, maintenance, buildDB, wikiacl, maintenance, user
from Sycamore.Page import Page

#################################################
# This script will try and guess users' timezone
# values.  Sets the tz to the tz of the wiki they
# made the most edits on.
#################################################
tzs = {'davis':'US/Pacific', 'rochester':'US/Eastern', 'santacruz':'US/Pacific', 'chico':'US/Pacific', 'pittsburgh':'US/Eastern', 'anthill':'US/Eastern'}

req = request.RequestDummy()

for uid in user.getUserList(req.cursor):
  req.cursor.execute("""SELECT users.id, count(allPages.wiki_id) as editcount, wikis.name from users, allPages, wikis where users.id=%(uid)s and users.id=allPages.userEdited and wikis.id=allPages.wiki_id group by users.id, wikis.name order by editcount desc limit 1;""", {'uid': uid}) 
  result = req.cursor.fetchone()
  if result:
     wiki_of_most_edits = result[2]
     if tzs.has_key(wiki_of_most_edits):
        tz = tzs[wiki_of_most_edits]	
	theuser = user.User(req, uid)	
        theuser.tz = tz	
	theuser.save()
  else:
     req.cursor.execute("""SELECT wikis.name from userWikiInfo, users, wikis where user_name=users.name and users.id=%(uid)s and wikis.id=userWikiInfo.wiki_id""", {'uid':uid})
     result = req.cursor.fetchall()
     if len(result) == 1:
        wiki_of_creation = result[0][0]
	if tzs.has_key(wiki_of_creation):
           tz = tzs[wiki_of_creation]	
	   theuser = user.User(req, uid)	
           theuser.tz = tz	
	   theuser.save()

req.db_disconnect()

print "Done with user tz guessing!"
