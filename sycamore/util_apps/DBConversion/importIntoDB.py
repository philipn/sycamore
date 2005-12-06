# This is a utility to take the old moin-style data and inject it into a super cool mysql database
# First you need to a) create the db in mysql. b) populate it with the basic table/view/etc
# Then, this will inject your old data into your new db!
# 1. Pages
# 2. Images
# 3. Users
# 4. Events

import sys, cStringIO
sys.path.extend(['/usr/local/lib/python2.3/site-packages','/var/www/installhtml/dwiki'])
from LocalWiki import wikiutil, config, wikidb, caching, request
from LocalWiki.Page import Page
from LocalWiki.logfile import editlog

import os, cPickle, time,shutil

data_path = 'data'
app_path = 'apps'


class aPage:
  # this is an object which holds all conceivable information about a page -- but just one version of the page.
  def __init__(self, pagename, version): 
    self.current = False
    self.pagename=pagename
    self.version=version
    self.text=self.getText()
    self.getEditInfo()

  def getEditInfo(self):
    in_editlog = False
    if os.path.exists(data_path + '/pages/' + wikiutil.quoteFilename(self.pagename) + '/editlog'):
      editlog = open(data_path + '/pages/' + wikiutil.quoteFilename(self.pagename) + '/editlog')
      editloglines = editlog.readlines()
      for line in editloglines:
        fields = line.split('\t')
        if fields[2] == self.version: 
	  in_editlog = True
          self.edit_user_ip = fields[1]    
  	  self.edit_user = fields[4]
	  self.edit_type = fields[len(fields)-1].strip()
	  if len(fields) > 5: 
	    self.edit_comment = fields[len(fields)-2]
	  else: self.edit_comment = ''
	  break

      editlog.close()
    if not in_editlog:
       self.edit_user_ip = ''
       self.edit_comment = ''
       self.edit_type = 'SAVE'
       self.edit_user = ''

        


  def getText(self):
    text = ''
    if os.path.exists(data_path + '/backup/' + wikiutil.quoteFilename(self.pagename) + '.' + self.version):
      file = open(data_path + '/backup/' + wikiutil.quoteFilename(self.pagename) + '.' + self.version)
      line = file.readline()
      text += line
      while line:
        line = file.readline()
	text += line
    else:
       # no backup version means this is the current version of the page
         file = open(data_path + '/text/' + wikiutil.quoteFilename(self.pagename))
         line = file.readline()
         text += line
         while line:
           line = file.readline()
  	   text += line
	 self.current = True

    return text

def dethumb(aPage):
    # converts old [[Thumbnail]], attachment: and borderless: syntax to new [[Image]] macro format.
    file = open('pagetext.in','w')
    file.write(aPage.text)
    file.close()
    os.spawnl(os.P_WAIT, 'dethumb.pl', 'dethumb.pl', 'pagetext.in', 'pagetext.out')
    file = open('pagetext.out','r')
    newtext  = ''
    for line in file.readlines():
      newtext += line
    file.close()
    aPage.text = newtext



def hasImages(pagename):
  if os.path.exists(data_path + '/pages/' + wikiutil.quoteFilename(pagename) + '/attachments'):
    if os.listdir(data_path + '/pages/' + wikiutil.quoteFilename(pagename) + '/attachments'):
      return True
  return False

def findAllVersions(pagelist):
  #returns a list of floats of the versions of the page that are on disk
  l = []

  # first, the backups!
  for backup in os.listdir(data_path + '/backup/'):
    if backup[0] == '.': continue
    pagename = wikiutil.unquoteFilename(backup.split('.')[0])
    version = backup.split('.')[1]
    l.append((pagename, version))

  # now, let's figure out the date of the current version of the page
  for pagename in pagelist:
     if os.path.exists(data_path + '/text/' + wikiutil.quoteFilename(pagename)):
      if os.path.exists(data_path + '/pages/' + wikiutil.quoteFilename(pagename) + '/editlog'):
       # we've got some history..
       	file = open(data_path + '/pages/' + wikiutil.quoteFilename(pagename) + '/last-edited')
	lines = file.readlines()
	lastline = lines[len(lines)-1]
	l.append((pagename, lastline.split()[2]))
      else:
         l.append((pagename, '0'))

  return l

def findUploadInfo(pagename, filename):
  # gets all that super secret special sexy information about an uploaded file.  HACKY.
  
  # sadly, we only logged to the master editlog.  so, we've gotta look in the master editlog :(
  editlog = open(data_path + '/editlog')
  editloglines = editlog.readlines()
  editloglines.reverse()
  for line in editloglines:
    sline = line.split('\t') 
    if sline[0] == wikiutil.quoteFilename(pagename):
      if len(sline) == 7:  
        if sline[5] == filename and sline[6].strip() == 'ATTNEW':
	  uploaded_by_ip = sline[1] 	  
	  uploaded_time = sline[2]
	  uploaded_by = sline[4]
	  return (uploaded_time, uploaded_by, uploaded_by_ip)
  #shit
  return ('','','') 

def insertPagesIntoDB(d):
  print "Inserting pages into DB..."
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("start transaction;")
  for pagename, pagelist in d.iteritems():
    for apage in pagelist: 
      cursor.execute("INSERT into allPages set name=%s, text=%s, editTime=%s, userEdited=%s, editType=%s, comment=%s, userIP=%s;", (apage.pagename, apage.text, apage.version, apage.edit_user, apage.edit_type, apage.edit_comment, apage.edit_user_ip))
      if apage.current:
      	#we convert so it uses the new [[Image]]
	dethumb(apage)
        cursor.execute("INSERT into curPages set name=%s, text=%s, editTime=%s, userEdited=%s;", (apage.pagename, apage.text, apage.version, apage.edit_user))

  cursor.execute("commit;")

  db.close()

def insertImagesIntoDB(pagelist):
  import cStringIO
  from PIL import Image
  print "Inserting images into DB..."
  for pagename in pagelist:
   if hasImages(pagename):
     for filename in os.listdir(data_path + '/pages/' + wikiutil.quoteFilename(pagename) + '/attachments/'):
       # check if the file is sane and NOT a thumbnail
       sfile = filename.split('.')
       if len(sfile) >= 5:
         if sfile[len(sfile)-4] == 'thumbnail': continue
       if len(sfile) >= 2:
         end = sfile[len(sfile)-1].lower()
	 if end == 'jpeg' or end == 'jpg' or end == 'gif' or end =='png':
	   #we have a valid image
	   file = open(data_path + '/pages/' + wikiutil.quoteFilename(pagename) + '/attachments/' + filename)
	   filestring = ''
	   filelines = file.readlines()
	   for line in filelines:
	     filestring += line
	   uploaded_time, uploaded_by, uploaded_by_ip = findUploadInfo(pagename, filename)
	   db = wikidb.connect()
	   cursor = db.cursor()
	   imagefile = cStringIO.StringIO(filestring)
	   im = Image.open(imagefile)
	   x, y = im.size
	   cursor.execute("start transaction;")
	   if uploaded_time:
	     cursor.execute("INSERT into images set name=%s, image=%s, attached_to_pagename=%s, uploaded_time=%s, uploaded_by=%s, uploaded_by_ip=%s, xsize=%s, ysize=%s;", (filename, filestring, pagename, uploaded_time, uploaded_by, uploaded_by_ip, x, y))
	   else:
	     cursor.execute("INSERT into images set name=%s, image=%s, attached_to_pagename=%s, uploaded_by=%s, uploaded_by_ip=%s, xsize=%s, ysize=%s;", (filename, filestring, pagename, uploaded_by, uploaded_by_ip, x, y,))
	   cursor.execute("commit;")

def getFieldValue(dict, key, item):
 # utility function to grab the value of item from dict.  values associated with dict are lists, so we just look through the list and grab the item.  Should have used dict. in the first place for the value, but whatever
 l = dict[key]  
 for entry in l:
   if entry[0] == item:
     return entry[1]

def insertUsersIntoDB():
  print "Inserting users into DB..."
  import xml.dom.minidom

  userdict = {}
  for filename in os.listdir(data_path + '/user'):
   sfilename = filename.split('.')
   # check if it's a valid user file..who knows what kind of garbage they might have lying around
   if len(sfilename) == 3:
    valid_filename = True
    for character in sfilename[0]:
     if not character in ['0','1','2','3','4','5','6','7','8','9']:
       valid_filename = False
       break
        
    if valid_filename:
      file = open(data_path + '/user/' + filename)  
      lines = file.readlines()
      file.close()
      id = filename
      name = ''
      email = ''
      enc_password = ''
      language = ''
      remember_me = ''
      css_url = ''
      disabled = ''
      edit_cols = ''
      edit_rows = ''
      edit_on_doubleclick = ''
      theme_name = ''
      last_saved = ''
      join_date = ''
      created_count = ''
      edit_count = ''
      file_count = ''
      last_page_edited = ''
      last_edit_date = ''
      # rc bookmark comes from a different file..but, it doesn't matter, dont even grab it
      rc_bookmark = ''
      rc_showcomments = ''

      # first we grab all we can from the static file, next we'll grab from userstats.xml
      for line in lines:
        if line.startswith('#'): continue
	sline = line.split('=')
	attribute = sline[0] 
	value = sline[1].strip()
	if attribute == 'enc_password':
           value = value + '='
	   if value.startswith("{SHA}"):
             value = value[5:]
	if not userdict.has_key(id): userdict[id] = [(attribute, value)]
	else: userdict[id].append((attribute, value))

  dom = xml.dom.minidom.parse(app_path + '/userstats.xml')
  users = dom.getElementsByTagName("user")
  root = dom.documentElement
  # let's find the user's record, if they have one
  # if they have no userstats record, let's put in some sane values
  userstats_ids = []
  for user in users:
    found = False
    name = user.getAttribute("name")
    for id, values in userdict.iteritems():
     if not found:
      for value in values:
       if value[0] == 'name' and value[1] == name:
        # we have our user
        userstats_user_id = id
	userstats_ids.append(userstats_user_id)
        found = True
        break
    if found:
      edit_count = str(user.getAttribute("edit_count"))
      created_count = str(user.getAttribute("created_count"))
      file_count = str(user.getAttribute("file_count"))
      join_date = str(user.getAttribute("join_date"))
      last_edit_date = str(user.getAttribute("last_edit"))
      last_page_edited = str(user.getAttribute("last_page_edited"))
      userdict[userstats_user_id].append(("edit_count", edit_count))
      userdict[userstats_user_id].append(("created_count", created_count))
      userdict[userstats_user_id].append(("file_count", file_count))
      userdict[userstats_user_id].append(("join_date", join_date))
      userdict[userstats_user_id].append(("last_edit_date", last_edit_date))
      userdict[userstats_user_id].append(("last_page_edited", last_page_edited))

  #now let's find out which users don't have any user stats info, for whatever reason 
  ids_with_no_userstats_info = []
  for id, values in userdict.iteritems():
    if id not in userstats_ids:
      ids_with_no_userstats_info.append(id)
  for id in ids_with_no_userstats_info:
    userdict[id].append(("edit_count","0"))
    userdict[id].append(("created_count","0"))
    userdict[id].append(("file_count","0"))
    userdict[id].append(("join_date",""))
    userdict[id].append(("last_edit_date",""))
    userdict[id].append(("last_page_edited",""))

  # start filling the db with the user data
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("start transaction;")
  for user, fields in userdict.iteritems():
    id = user
    name = getFieldValue(userdict, user, "name") 
    email = getFieldValue(userdict, user, "email") 
    enc_password = getFieldValue(userdict, user, "enc_password") 
    language = getFieldValue(userdict, user, "language") 
    remember_me = getFieldValue(userdict, user, "remember_me") 
    css_url = getFieldValue(userdict, user, "css_url") 
    disabled = getFieldValue(userdict, user, "disabled") 
    edit_cols = getFieldValue(userdict, user, "edit_cols") 
    edit_rows = getFieldValue(userdict, user, "edit_rows") 
    edit_on_doubleclick = getFieldValue(userdict, user, "edit_on_doubleclick") 
    theme_name = getFieldValue(userdict, user, "theme_name") 
    last_saved = getFieldValue(userdict, user, "last_saved") 
    created_count = getFieldValue(userdict, user, "created_count") 
    edit_count = getFieldValue(userdict, user, "edit_count") 
    file_count = getFieldValue(userdict, user, "file_count") 
    last_page_edited = getFieldValue(userdict, user, "last_page_edited") 

    last_edit_date = getFieldValue(userdict, user, "last_edit_date") 
    join_date = getFieldValue(userdict, user, "join_date") 
    rc_bookmark = ''
    rc_showcomments = getFieldValue(userdict, user, "rc_showcomments") 
    cursor.execute("INSERT into users set id=%s, name=%s, email=%s, enc_password=%s, language=%s, remember_me=%s, css_url=%s, disabled=%s, edit_cols=%s, edit_rows=%s, edit_on_doubleclick=%s, theme_name=%s, last_saved=%s, created_count=%s, edit_count=%s, file_count=%s, last_page_edited=%s, last_edit_date=UNIX_TIMESTAMP(%s), rc_bookmark=%s, rc_showcomments=%s, join_date=UNIX_TIMESTAMP(%s)", ( id, name, email, enc_password, language, remember_me, css_url, disabled, edit_cols, edit_rows, edit_on_doubleclick, theme_name, last_saved, created_count, edit_count, file_count, last_page_edited, last_edit_date, rc_bookmark, rc_showcomments, join_date))
  cursor.execute("commit;") 

  

def clearCaches():
  print "Clearing page caches..."
  plist = wikiutil.getPageList() 
  arena = 'Page.py'
  for pname in plist:
    key = pname
    cache = caching.CacheEntry(arena, key)
    cache.clear()

def buildCaches():
  print "Building page caches...It is _normal_ for this to produce errors!"
  # this is hackish, but it will work
  # the idea is to view every page to build the cache
  # we should actually refactor send_page()
  req = request.RequestCGI()
  req.redirect(cStringIO.StringIO())
  for pname in wikiutil.getPageList():
   Page(pname).getPageLinks(req, docache=True)
  req.redirect()


  
    
  
d = {}
filelist = os.listdir(data_path + '/text/')
better_filelist = [ x for x in filelist if x[0] != '.']
pagelist = [ wikiutil.unquoteFilename(x) for x in better_filelist]
for pagename, version in findAllVersions(pagelist):
    if d.has_key(pagename): d[pagename].append(aPage(pagename, version))
    else: d[pagename] = [aPage(pagename, version)]

insertPagesIntoDB(d)
insertImagesIntoDB(pagelist)
insertUsersIntoDB()
clearCaches()
buildCaches()
print "It went as planned!  The DB should be populated and usable now."
