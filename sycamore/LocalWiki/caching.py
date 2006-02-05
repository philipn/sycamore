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
    def __init__(self, key, request):
        self.key = key
	self.request = request

    def exists(self):
	self.request.cursor.execute("SELECT cachedTime from curPages where name=%(key)s", {'key':self.key})
	result = self.request.cursor.fetchone()
	return result

    def mtime(self):
	self.request.cursor.execute("SELECT cachedTime from curPages where name=%(key)s", {'key':self.key})
	result = self.request.cursor.fetchone()
	if result:
	  return result[0]
	else: return 0

    def needsUpdate(self):
        needsupdate = True
        self.request.cursor.execute("SELECT editTime, cachedTime from curPages where name=%(key)s", {'key':self.key})
        result = self.request.cursor.fetchone()
        	
        if result:
            if result[0]:
		edit_time = result[0]
            else: return True 
            if result[1]:
		cached_time = result[1]
            else: return True

            needsupdate = edit_time > cached_time
        
        # if a page has attachments (images) we check if this needs changing, too
	# also check included pages
        if not needsupdate:
	    self.request.cursor.execute("SELECT max(uploaded_time) from images where attached_to_pagename=%(key)s", {'key':self.key})
	    result = self.request.cursor.fetchone()
	    if result:
	      ftime2 = result[0]
              needsupdate = ftime2 > cached_time
	    for page in dependencies(self.key, self.request):
	      if (page.mtime() > cached_time) or (page.ctime(self.request) > cached_time):
	        return True

        return needsupdate

    def update(self, content, links):
        self.request.cursor.execute("UPDATE curPages set cachedText=%(cached_content)s, cachedTime=%(cached_time)s where name=%(key)s", {'cached_content':wikidb.dbapi.Binary(content), 'cached_time':time.time(), 'key':self.key})
	self.request.cursor.execute("DELETE from links where source_pagename=%(key)s", {'key':self.key})
	for link in links:
	  self.request.cursor.execute("INSERT into links values (%(key)s, %(link)s)", {'key':self.key, 'link':link})

    def content(self):
        self.request.cursor.execute("SELECT cachedText from curPages where name=%(key)s", {'key':self.key})
        result = self.request.cursor.fetchone()
	return result[0]

    def clear(self):
        #clears the content of the cache regardless of whether or not the page needs an update
	self.request.cursor.execute("UPDATE curPages set cachedText=NULL, cachedTime=NULL where name=%(key)s", {'key':self.key})

def dependency(depend_pagename, source_pagename, request):
  # note that depend_pagename depends on source_pagename
  # this means that if source_pagename is updated we should
  # clear the depend_pagename cache
  request.cursor.execute("SELECT page_that_depends from pageDependencies where page_that_depends=%(depend_pagename)s and source_page=%(source_pagename)s", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename})
  result = request.cursor.fetchone()
  if result:
    request.cursor.execute("UPDATE pageDependencies set page_that_depends=%(depend_pagename)s, source_page=%(source_pagename)s", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename})
  else:
    request.cursor.execute("INSERT into pageDependencies (page_that_depends, source_page) values (%(depend_pagename)s, %(source_pagename)s)", {'depend_pagename':depend_pagename, 'source_pagename':source_pagename})

def clear_dependencies(pagename, request):
  # clears out dependencies.  do this before parsing on a page save
  request.cursor.execute("DELETE from pageDependencies where page_that_depends=%(page_name)s", {'page_name':pagename})

def dependencies(pagename, request):
  from LocalWiki.Page import Page
  # return a list of pages (page objects) that pagename depends on
  request.cursor.execute("SELECT source_page from pageDependencies where page_that_depends=%(page_name)s", {'page_name':pagename})
  results = request.cursor.fetchall()
  l = []
  for result in results:
   l.append(Page(result[0], request))
  return l
