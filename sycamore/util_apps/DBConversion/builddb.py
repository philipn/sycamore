# This is a utility to take the old moin-style data and inject it into a super cool mysql database
# 1. Pages
# 2. Images
# 3. Users
# 4. Events

import sys
sys.path.extend(['/Library/Webserver','/Library/Webserver/Documents/installhtml/dwiki'])
from LocalWiki import wikiutil, config, wikidb
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
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("start transaction;")
  for pagename, pagelist in d.iteritems():
    for apage in pagelist: 
      cursor.execute("INSERT into allPages set name=%s, text=%s, editTime=FROM_UNIXTIME(%s), userEdited=%s, editType=%s, comment=%s, userIP=%s;", (apage.pagename, apage.text, apage.version, apage.edit_user, apage.edit_type, apage.edit_comment, apage.edit_user_ip))
      if apage.current:
        cursor.execute("INSERT into curPages set name=%s, text=%s, editTime=FROM_UNIXTIME(%s), userEdited=%s;", (apage.pagename, apage.text, apage.version, apage.edit_user))

  cursor.execute("commit;")

  db.close()

def insertImagesIntoDB(pagelist):
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
	   cursor.execute("start transaction;")
	   cursor.execute("INSERT into images set name=%s, image=%s, attached_to_pagename=%s, uploaded_time=FROM_UNIXTIME(%s), uploaded_by=%s, uploaded_by_ip=%s ;", (filename, filestring, pagename, uploaded_time, uploaded_by, uploaded_by_ip))
	   cursor.execute("commit;")

def insertUsersIntoDB():
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
      rc_bookmark = ''
      rc_showcomments = ''

      # first we grab all we can from the static file, next we'll grab from userstats.xml
      for line in lines:
        if line.startswith('#'): continue
	sline = line.split('=')
	attribute = sline[0] 
	value = sline[1].strip()
	if attribute == 'enc_password': value += value + '='
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


d = {}
filelist = os.listdir(data_path + '/pages/')
dirlist = [ x for x in filelist if os.path.isdir(data_path + '/pages/' + x) ]
pagelist = [ wikiutil.unquoteFilename(x) for x in dirlist ]
for pagename, version in findAllVersions(pagelist):
    if d.has_key(pagename): d[pagename].append(aPage(pagename, version))
    else: d[pagename] = [aPage(pagename, version)]

#insertPagesIntoDB(d)
#insertImagesIntoDB(pagelist)
insertUsersIntoDB()
