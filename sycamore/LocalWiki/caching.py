# -*- coding: iso-8859-1 -*-
"""
    LocalWiki caching module

    @copyright: 2005 by Philip Neustrom, 2001-2004 by Jürgen Hermann <jh@web.de>
    @license: GNU GPL, see COPYING for details.
"""

# Imports
import os, shutil, time
from LocalWiki import config, wikiutil, wikidb


class CacheEntry:
    def __init__(self, arena, key):
        self.arena = arena
        self.key = key

    def exists(self):
	db = wikidb.connect()
	cursor = db.cursor()
	cursor.execute("SELECT cachedTime from curPages where name=%s", (self.key))
	result = cursor.fetchall()
	cursor.close()
	db.close()
	return result

    def mtime(self):
	db = wikidb.connect()
	cursor = db.cursor()
	cursor.execute("SELECT cachedTime from curPages where name=%s", (self.key))
	result = cursor.fetchall()
	cursor.close()
	db.close()
	if result:
		return result[0][0]
	else: return 0

    def needsUpdate(self):
        needs_update = True
        db = wikidb.connect()
        cursor = db.cursor()
        cursor.execute("SELECT editTime, cachedTime from curPages where name=%s", (self.key))
        result = cursor.fetchall()
	
        if result:
            if result[0][0]:
		edit_time = result[0][0]
            else: return True 
            if result[0][1]:
		cached_time = result[0][1]
            else: return True

        needsupdate = edit_time > cached_time
        
        # if a page has attachments (images) we check if this needs changing, too
	# also check included pages
        if not needsupdate:
	    cursor.execute("SELECT max(uploaded_time) from images where attached_to_pagename=%s", (self.key))
	    result = cursor.fetchone()
	    if result:
	      ftime2 = result[0]
              needsupdate = ftime2 > cached_time
	    for page in dependencies(self.key):
	      if page.mtime() > cached_time:
	        return True

        cursor.close()
	db.close()        
        return needsupdate

    def update(self, content, links):
	db = wikidb.connect()
        cursor = db.cursor()
	cursor.execute("start transaction")
        cursor.execute("UPDATE curPages set cachedText=%s, cachedTime=%s where name=%s", (content, time.time(), self.key))
	cursor.execute("DELETE from links where source_pagename=%s", (self.key))
	for link in links:
	  cursor.execute("INSERT into links values (%s, %s)", (self.key, link))
	cursor.execute("commit")
	cursor.close()
	db.close()

    def content(self):
	db = wikidb.connect()
       	cursor = db.cursor()
        cursor.execute("SELECT cachedText from curPages where name=%s", self.key)
        result = cursor.fetchone()
	cursor.close()
	db.close()
	return result[0]

    def clear(self):
        #clears the content of the cache regardless of whether or not the page needs an update
	db = wikidb.connect()
        cursor = db.cursor()
	cursor.execute("start transaction")
	cursor.execute("UPDATE curPages set cachedText=NULL, cachedTime=NULL where name=%s", (self.key))
	cursor.execute("commit")
	cursor.close()
	db.close()

def dependency(depend_pagename, source_pagename):
  # note that depend_pagename depends on source_pagename
  # this means that if source_pagename is updated we should
  # clear the depend_pagename cache
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("start transaction")
  cursor.execute("REPLACE into pageDependencies set page_that_depends=%s, source_page=%s", (depend_pagename, source_pagename))
  cursor.execute("commit")
  cursor.close()
  db.close()

def clear_dependencies(pagename):
  # clears out dependencies.  do this before parsing on a page save
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("start transaction")
  cursor.execute("DELETE from pageDependencies where page_that_depends=%s", (pagename))
  cursor.execute("commit")
  cursor.close()
  db.close()

 
def dependencies(pagename):
  from LocalWiki.Page import Page
  # return a list of pages (page objects) that pagename depends on
  db = wikidb.connect()
  cursor = db.cursor()
  cursor.execute("SELECT source_page from pageDependencies where page_that_depends=%s", (pagename))
  results = cursor.fetchall()
  cursor.close()
  db.close()
  l = []
  for result in results:
   l.append(Page(result[0]))
  return l
